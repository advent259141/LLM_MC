import asyncio
import re
from typing import Optional, Dict, Any

from app.bot.client import bot_client
from app.llm.client import llm_client
from app.llm.prompts import get_agent_system_prompt, format_observation
from app.script.executor import script_executor, BotAPI
from app.skills.manager import skill_manager
from app.task.manager import task_manager, TaskStatus
from app.config import settings


class Agent:
    """
    Main Agent class
    Coordinates perception, decision-making, and action execution
    
    支持后台任务执行，LLM 决策循环不被阻塞
    """
    
    def __init__(self):
        self.is_running = False
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_action_result: Optional[Dict[str, Any]] = None
        self._tick_task: Optional[asyncio.Task] = None
        self._pending_chat: list = []
        
        # 任务管理器引用
        self.task_manager = task_manager
        
        # 任务运行时的轮询计时
        self._task_tick_counter: int = 0
    
    async def start(self):
        """Start the agent's decision loop"""
        if self.is_running:
            print("[Agent] Already running")
            return
        
        print("[Agent] Starting agent loop...")
        self.is_running = True
        
        # Register event handler for chat messages
        bot_client.add_event_handler(self._handle_bot_event)
        
        # Start tick loop
        self._tick_task = asyncio.create_task(self._tick_loop())
    
    async def stop(self):
        """Stop the agent's decision loop"""
        if not self.is_running:
            return
        
        print("[Agent] Stopping agent loop...")
        self.is_running = False
        
        # 取消所有后台任务
        await self.task_manager.cancel_all_tasks()
        
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        
        bot_client.remove_event_handler(self._handle_bot_event)
    
    async def _tick_loop(self):
        """Main decision loop"""
        error_count = 0
        while self.is_running:
            try:
                await self.tick()
                error_count = 0  # 重置错误计数
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # 只打印前3次错误
                    print(f"[Agent] 错误: {e}")
                elif error_count == 4:
                    print("[Agent] 后续相同错误将不再显示...")
            
            await asyncio.sleep(settings.agent_tick_rate)
    
    async def tick(self):
        """Single decision-action cycle - 事件驱动模式"""
        if not self.is_running:
            return
        
        # 先检查Bot是否已连接
        try:
            status = await bot_client.get_status()
            if not status.get("connected"):
                return  # Bot未连接，静默跳过
        except Exception:
            return  # 无法获取状态，静默跳过
        
        try:
            # 1. Get observation from bot
            observation = await bot_client.get_observation()
            
            # Add any pending chat messages
            if self._pending_chat:
                if "chatMessages" not in observation:
                    observation["chatMessages"] = []
                observation["chatMessages"].extend(self._pending_chat)
                self._pending_chat = []
            
            # 2. 添加当前任务状态到观察
            task_status = self.task_manager.get_status_summary()
            observation["currentTasks"] = task_status
            
            # 3. 检查触发条件
            has_chat = bool(observation.get("chatMessages"))
            has_events = bool(observation.get("events"))
            has_active_tasks = task_status.get("has_active_tasks", False)
            
            # 检查是否有紧急情况需要处理
            health_info = observation.get("health", {})
            is_health_critical = health_info.get("health", 20) < 6  # 生命值低于 6
            is_food_critical = health_info.get("food", 20) < 4      # 饥饿值低于 4
            has_urgent_situation = is_health_critical or is_food_critical
            
            # LLM 触发策略：
            # - 空闲状态（无后台任务）：每 agent_tick_rate 秒调用一次，让 bot 可以主动行动
            # - 有后台任务运行时：
            #   - 有事件/聊天/紧急情况时立即调用
            #   - 否则每 agent_task_tick_rate 秒调用一次（如果配置 > 0）
            
            if has_active_tasks:
                # 有后台任务运行时
                should_call_llm = (
                    has_chat or               # 有聊天消息
                    has_events or             # 有游戏事件
                    has_urgent_situation      # 紧急情况
                )
                
                if not should_call_llm:
                    # 检查是否到了定时轮询时间
                    task_tick_rate = settings.agent_task_tick_rate
                    if task_tick_rate > 0:
                        # 计算需要多少个 tick 才等于 task_tick_rate
                        ticks_needed = int(task_tick_rate / settings.agent_tick_rate)
                        self._task_tick_counter += 1
                        
                        if self._task_tick_counter >= ticks_needed:
                            # 到达定时轮询时间，触发 LLM
                            self._task_tick_counter = 0
                            should_call_llm = True
                    
                    if not should_call_llm:
                        # 任务运行中且未到轮询时间，跳过本次 tick
                        return
                else:
                    # 有事件触发，重置计数器
                    self._task_tick_counter = 0
            else:
                # 空闲状态：重置任务计数器
                self._task_tick_counter = 0
                
                # 保持每 tick_rate 秒调用一次
                # 但如果上次是 wait 且没有新事件，可以跳过
                if (not has_chat and not has_events and
                    self.last_action and self.last_action.get("action") == "wait"):
                    return
            
            # 3. Format observation for LLM
            user_message = format_observation(observation)
            
            # 添加任务状态信息
            if has_active_tasks:
                user_message += f"\n\n=== 当前后台任务 ===\n{task_status['summary']}"
            
            if self.last_action_result:
                user_message += f"\n\nLast action result: {self.last_action_result}"
            
            # 4. Get decision from LLM
            print("[Agent] Thinking...")
            
            system_prompt = get_agent_system_prompt({
                "position": observation.get("position"),
                "health": observation.get("health"),
                "time": observation.get("time"),
                "has_active_tasks": has_active_tasks
            })
            
            response = await llm_client.chat_json(system_prompt, user_message)
            
            if settings.debug:
                print(f"[Agent] LLM Response: {response}")
            
            # 5. Execute action
            if response and response.get("action"):
                print(f"[Agent] Thought: {response.get('thought', 'N/A')}")
                print(f"[Agent] Action: {response['action']} {response.get('parameters', {})}")
                
                self.last_action = response
                
                # 特殊处理：启动后台技能任务
                if response["action"] == "startSkill":
                    self.last_action_result = await self._start_skill_task(
                        response.get("parameters", {})
                    )
                # 特殊处理：取消任务
                elif response["action"] == "cancelTask":
                    self.last_action_result = await self._cancel_task(
                        response.get("parameters", {})
                    )
                # 特殊处理：查询任务状态
                elif response["action"] == "getTaskStatus":
                    self.last_action_result = self._get_task_status()
                # 特殊处理脚本执行动作（同步阻塞，用于简单脚本）
                elif response["action"] == "executeScript":
                    self.last_action_result = await self._execute_script(
                        response.get("parameters", {})
                    )
                else:
                    self.last_action_result = await bot_client.execute_action(
                        response["action"],
                        response.get("parameters", {})
                    )
                
                print(f"[Agent] Result: {self.last_action_result.get('message', 'N/A')}")
            else:
                print("[Agent] No valid action in response")
                
        except Exception as e:
            print(f"[Agent] Error: {e}")
            self.last_action_result = {"success": False, "message": str(e)}
    
    async def force_tick(self):
        """Force an immediate decision cycle"""
        await self.tick()
    
    async def _start_skill_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        启动后台技能任务（非阻塞）
        
        Args:
            params: 包含 skillName 和可选的 kwargs
        """
        skill_name = params.get("skillName", "")
        skill_kwargs = params.get("kwargs", {})
        
        if not skill_name:
            return {"success": False, "message": "未指定技能名称"}
        
        # 检查技能是否存在
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            skills = skill_manager.list_skills()
            skill_names = [s['name'] for s in skills]
            return {
                "success": False,
                "message": f"技能 '{skill_name}' 不存在，可用技能: {', '.join(skill_names)}"
            }
        
        # 创建后台任务
        async def run_skill():
            bot_api = BotAPI()
            return await bot_api.useSkill(skill_name, **skill_kwargs)
        
        task = self.task_manager.create_task(
            name=skill_name,
            description=skill.get("description", ""),
            coroutine_func=run_skill
        )
        
        return {
            "success": True,
            "message": f"已启动技能 '{skill_name}'，任务ID: {task.id}",
            "task_id": task.id
        }
    
    async def _cancel_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取消指定任务或所有任务"""
        task_id = params.get("taskId", "")
        cancel_all = params.get("all", False)
        
        if cancel_all:
            await self.task_manager.cancel_all_tasks()
            # 同时停止bot移动
            try:
                await bot_client.execute_action("stopMoving", {})
            except:
                pass
            return {"success": True, "message": "已取消所有任务"}
        
        if not task_id:
            # 取消当前任务
            current = self.task_manager.current_task
            if current:
                task_id = current.id
            else:
                return {"success": False, "message": "没有正在运行的任务"}
        
        success = await self.task_manager.cancel_task(task_id)
        if success:
            # 停止移动
            try:
                await bot_client.execute_action("stopMoving", {})
            except:
                pass
            return {"success": True, "message": f"已取消任务 {task_id}"}
        else:
            return {"success": False, "message": f"无法取消任务 {task_id}"}
    
    def _get_task_status(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        status = self.task_manager.get_status_summary()
        history = self.task_manager.get_recent_history(5)
        
        return {
            "success": True,
            "message": status.get("summary", "无任务"),
            "current_tasks": status,
            "recent_history": history
        }
    
    async def _execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Python script for complex actions"""
        script = params.get("script", "")
        description = params.get("description", "Unnamed script")
        timeout = params.get("timeout", 300)  # 默认5分钟
        
        if not script:
            return {"success": False, "message": "No script provided"}
        
        print(f"[Agent] Executing script: {description}")
        
        try:
            result = await script_executor.execute(
                script=script,
                timeout=timeout
            )
            
            if result["success"]:
                # 构建有意义的结果摘要
                actions = result.get("actions", [])
                action_count = len(actions)
                script_result = result.get('result')
                
                # 构建动作摘要
                if actions:
                    # 获取每个动作的结果摘要
                    action_summaries = []
                    for action_info in actions[-5:]:  # 最多显示最后5个动作
                        action_name = action_info.get("action", "unknown")
                        action_result = action_info.get("result", {})
                        success = action_result.get("success", False)
                        msg = action_result.get("message", "")
                        status = "✓" if success else "✗"
                        action_summaries.append(f"{status}{action_name}: {msg[:50]}")
                    
                    actions_text = "; ".join(action_summaries)
                    if action_count > 5:
                        actions_text = f"...and {action_count - 5} more; " + actions_text
                else:
                    actions_text = "No actions executed"
                
                # 如果脚本有返回值，使用返回值；否则使用动作摘要
                if script_result is not None:
                    message = f"Script result: {script_result}"
                else:
                    message = f"Executed {action_count} actions: {actions_text}"
                
                return {
                    "success": True,
                    "message": message,
                    "logs": result.get("logs", []),
                    "actions": actions,
                    "action_count": action_count,
                    "execution_time": result.get("execution_time", 0)
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                # 如果有traceback，打印到控制台方便调试
                if result.get('traceback'):
                    print(f"[Agent] Script traceback:\n{result['traceback']}")
                return {
                    "success": False,
                    "message": f"Script failed: {error_msg}",
                    "logs": result.get("logs", []),
                    "actions": result.get("actions", [])
                }
        except Exception as e:
            import traceback
            print(f"[Agent] Script execution error:\n{traceback.format_exc()}")
            return {"success": False, "message": f"Script execution error: {str(e)}"}
    
    async def _handle_bot_event(self, event: Dict[str, Any]):
        """Handle events from the bot WebSocket"""
        event_type = event.get("type")
        
        if event_type == "chat":
            message = event.get("message", "")
            username = event.get("username", "")
            
            # 检查是否是测试指令（使用后台任务管理器）
            if message.startswith("%test "):
                asyncio.create_task(self._handle_test_command(message, username))
                return
            
            # 检查是否是停止指令
            if message.strip() == "%stop":
                asyncio.create_task(self._handle_stop_command(username))
                return
            
            # 检查是否是任务状态指令
            if message.strip() == "%status":
                asyncio.create_task(self._handle_status_command(username))
                return
            
            # 检查是否是列出技能指令
            if message.strip() == "%skills":
                asyncio.create_task(self._handle_skills_command(username))
                return
            
            # 检查是否是帮助指令
            if message.strip() == "%help":
                asyncio.create_task(self._handle_help_command(username))
                return
            
            # Store chat message for next tick
            self._pending_chat.append({
                "username": username,
                "message": message
            })
    
    async def _handle_test_command(self, message: str, username: str):
        """
        处理 %test 指令，使用后台任务管理器启动技能
        
        格式: %test 技能名
        或者: %test 技能名(参数1=值1, 参数2=值2)
        """
        try:
            # 解析指令
            command = message[6:].strip()  # 去掉 "%test "
            
            # 解析技能名和参数
            match = re.match(r'^([^(]+)(?:\(([^)]*)\))?$', command)
            if not match:
                await bot_client.execute_action("chat", {
                    "message": f"@{username} 格式错误喵~ 用法: %test 技能名 或 %test 技能名(参数=值)"
                })
                return
            
            skill_name = match.group(1).strip()
            params_str = match.group(2)
            
            # 解析参数
            kwargs = {}
            if params_str:
                param_pairs = params_str.split(',')
                for pair in param_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            if '.' in value:
                                kwargs[key] = float(value)
                            else:
                                kwargs[key] = int(value)
                        except ValueError:
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            kwargs[key] = value
            
            # 检查技能是否存在
            skill = skill_manager.get_skill(skill_name)
            if not skill:
                skills = skill_manager.list_skills()
                skill_names = [s['name'] for s in skills]
                await bot_client.execute_action("chat", {
                    "message": f"@{username} 技能'{skill_name}'不存在喵~ 可用技能: {', '.join(skill_names) or '无'}"
                })
                return
            
            # 使用后台任务管理器启动技能
            async def run_skill_with_notification():
                try:
                    bot_api = BotAPI()
                    result = await asyncio.wait_for(
                        bot_api.useSkill(skill_name, **kwargs),
                        timeout=300.0
                    )
                    
                    # 报告结果
                    if isinstance(result, dict):
                        success = result.get("success", True)
                        msg = result.get("message", str(result))
                        status_text = "成功" if success else "失败"
                    else:
                        status_text = "完成"
                        msg = str(result) if result else "无返回值"
                    
                    await bot_client.execute_action("chat", {
                        "message": f"@{username} 技能'{skill_name}'{status_text}: {msg[:80]}"
                    })
                    
                    return result
                    
                except asyncio.TimeoutError:
                    await bot_client.execute_action("chat", {
                        "message": f"@{username} 技能'{skill_name}'超时(5分钟)喵~"
                    })
                    await bot_client.execute_action("stopMoving", {})
                    raise
                except asyncio.CancelledError:
                    await bot_client.execute_action("chat", {
                        "message": f"@{username} 技能'{skill_name}'已停止喵~"
                    })
                    await bot_client.execute_action("stopMoving", {})
                    raise
            
            task = self.task_manager.create_task(
                name=skill_name,
                description=f"测试技能 (由 {username} 触发)",
                coroutine_func=run_skill_with_notification
            )
            
            await bot_client.execute_action("chat", {
                "message": f"@{username} 已启动技能'{skill_name}' (ID:{task.id})，LLM保持运行喵~"
            })
            
            print(f"[Agent] 后台启动技能: {skill_name}, 任务ID: {task.id}, 参数: {kwargs}")
            
        except Exception as e:
            import traceback
            print(f"[Agent] 技能测试错误: {traceback.format_exc()}")
            await bot_client.execute_action("chat", {
                "message": f"@{username} 测试出错喵: {str(e)[:50]}"
            })
    
    async def _handle_stop_command(self, username: str):
        """处理 %stop 指令，停止当前任务"""
        current_task = self.task_manager.current_task
        
        if not current_task:
            await bot_client.execute_action("chat", {
                "message": f"@{username} 没有正在运行的任务喵~"
            })
            return
        
        task_name = current_task.name
        task_id = current_task.id
        
        success = await self.task_manager.cancel_task(task_id)
        
        # 停止移动
        try:
            await bot_client.execute_action("stopMoving", {})
        except:
            pass
        
        if success:
            print(f"[Agent] 停止任务: {task_name} (ID: {task_id})")
            await bot_client.execute_action("chat", {
                "message": f"@{username} 已停止任务'{task_name}'喵~"
            })
        else:
            await bot_client.execute_action("chat", {
                "message": f"@{username} 停止任务失败喵~"
            })
    
    async def _handle_status_command(self, username: str):
        """处理 %status 指令，显示当前任务状态"""
        status = self.task_manager.get_status_summary()
        
        if not status.get("has_active_tasks"):
            await bot_client.execute_action("chat", {
                "message": f"@{username} 当前没有运行中的任务喵~"
            })
        else:
            running = status.get("running_count", 0)
            pending = status.get("pending_count", 0)
            
            # 获取当前任务详情
            current = self.task_manager.current_task
            if current:
                duration = current._get_duration() or 0
                await bot_client.execute_action("chat", {
                    "message": f"@{username} 运行:{running} 等待:{pending} | {current.name}: {current.progress} ({duration:.1f}s)"
                })
            else:
                await bot_client.execute_action("chat", {
                    "message": f"@{username} 运行中:{running} 等待中:{pending}"
                })
    
    async def _handle_help_command(self, username: str):
        """处理 %help 指令，显示帮助信息"""
        help_text = (
            "指令: %skills-列出技能 | %test 技能名-测试 | "
            "%test 技能(参数=值)-带参测试 | %stop-停止 | %status-状态"
        )
        await bot_client.execute_action("chat", {
            "message": f"@{username} {help_text}"
        })
    
    async def _handle_skills_command(self, username: str):
        """处理 %skills 指令，列出所有技能"""
        try:
            skills = skill_manager.list_skills()
            
            if not skills:
                await bot_client.execute_action("chat", {
                    "message": f"@{username} 还没有保存任何技能喵~"
                })
                return
            
            # 格式化技能列表
            skill_list = []
            for s in skills:
                params = s.get('params', [])
                param_str = f"({', '.join(params)})" if params else ""
                skill_list.append(f"{s['name']}{param_str}")
            
            await bot_client.execute_action("chat", {
                "message": f"@{username} 可用技能: {', '.join(skill_list)}"
            })
            
        except Exception as e:
            await bot_client.execute_action("chat", {
                "message": f"@{username} 获取技能列表失败喵: {str(e)[:30]}"
            })
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        task_status = self.task_manager.get_status_summary()
        
        return {
            "is_running": self.is_running,
            "last_action": self.last_action,
            "last_action_result": self.last_action_result,
            "pending_chat_count": len(self._pending_chat),
            "active_tasks": task_status
        }


# Singleton instance
agent = Agent()