from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.agent.agent import agent
from app.bot.client import bot_client
from app.script.executor import script_executor
from app.skills.manager import skill_manager
from app.task.manager import task_manager


router = APIRouter()


class ActionRequest(BaseModel):
    """Request model for executing an action"""
    action: str
    parameters: Optional[Dict[str, Any]] = None


class ActionResponse(BaseModel):
    """Response model for action execution"""
    success: bool
    message: str


# ========== Agent Endpoints ==========

@router.get("/agent/status")
async def get_agent_status():
    """Get current agent status"""
    return agent.get_status()


@router.post("/agent/start")
async def start_agent():
    """Start the agent decision loop"""
    await agent.start()
    return {"status": "started"}


@router.post("/agent/stop")
async def stop_agent():
    """Stop the agent decision loop"""
    await agent.stop()
    return {"status": "stopped"}


@router.post("/agent/tick")
async def force_tick():
    """Force an immediate agent decision cycle"""
    await agent.force_tick()
    return {"status": "tick completed"}


# ========== Bot Endpoints (Proxy to Node.js service) ==========

@router.get("/bot/status")
async def get_bot_status():
    """Get bot connection status"""
    try:
        return await bot_client.get_status()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot service error: {str(e)}")


@router.get("/bot/observation")
async def get_bot_observation():
    """Get current game observation"""
    try:
        return await bot_client.get_observation()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot service error: {str(e)}")


@router.post("/bot/connect")
async def connect_bot():
    """Connect bot to Minecraft server"""
    try:
        return await bot_client.connect()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot service error: {str(e)}")


@router.post("/bot/disconnect")
async def disconnect_bot():
    """Disconnect bot from Minecraft server"""
    try:
        return await bot_client.disconnect()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot service error: {str(e)}")


@router.post("/bot/action", response_model=ActionResponse)
async def execute_bot_action(request: ActionRequest):
    """Execute an action on the bot"""
    try:
        result = await bot_client.execute_action(
            request.action,
            request.parameters
        )
        return ActionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot service error: {str(e)}")


# ========== Script Execution Endpoints ==========

class ScriptRequest(BaseModel):
    """Request model for script execution"""
    code: str
    timeout: Optional[float] = 120.0


class ScriptResponse(BaseModel):
    """Response model for script execution"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    output: Optional[str] = None
    logs: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    action_count: Optional[int] = None


@router.post("/script/execute")
async def execute_script(request: ScriptRequest):
    """
    Execute a Python script to perform complex bot actions.
    
    The script should define an async function 'main(bot)' that will be executed.
    
    Example script:
    ```python
    async def main(bot):
        # 寻找钻石矿
        result = await bot.findBlock('diamond_ore', 32)
        if result.get('found'):
            block = result['block']
            bot.log(f"找到钻石矿在 ({block['x']}, {block['y']}, {block['z']})")
            # 移动过去
            await bot.goTo(block['x'], block['y'], block['z'])
            # 装备镐子
            await bot.equipItem('diamond_pickaxe')
            # 挖掘
            await bot.collectBlock('diamond_ore')
            return "成功挖到钻石！"
        else:
            return "附近没有钻石矿"
    ```
    
    Available bot methods:
    - bot.chat(message)
    - bot.goTo(x, y, z)
    - bot.followPlayer(playerName)
    - bot.listPlayers() - 获取服务器上所有在线玩家列表
    - bot.stopMoving()
    - bot.jump()
    - bot.lookAt(x, y, z)
    - bot.attack(entityType)
    - bot.collectBlock(blockType)
    - bot.wait(seconds)
    - bot.viewInventory()
    - bot.equipItem(itemName)
    - bot.placeBlock(blockName, x, y, z)
    - bot.scanBlocks(blockTypes, range)
    - bot.findBlock(blockType, maxDistance)
    - bot.getBlockAt(x, y, z)
    - bot.scanEntities(range, entityType)
    - bot.getObservation()
    - bot.getStatus()
    - bot.getPosition()
    - bot.getHealth()
    - bot.log(message)
    """
    try:
        result = await script_executor.execute(
            script=request.code,
            timeout=request.timeout
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script execution error: {str(e)}")


# ========== Skills Library Endpoints ==========

class SkillCreateRequest(BaseModel):
    """Request model for creating a skill"""
    name: str
    description: str
    code: str
    params: Optional[List[str]] = None


class SkillResponse(BaseModel):
    """Response model for skill operations"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    skill: Optional[Dict[str, Any]] = None


@router.get("/skills")
async def list_skills():
    """
    列出所有已保存的技能
    
    Returns:
        技能列表，每个技能包含 name, description, params
    """
    skills = skill_manager.list_skills()
    return {
        "success": True,
        "count": len(skills),
        "skills": skills
    }


@router.get("/skills/{name}")
async def get_skill(name: str):
    """
    获取指定技能的详细信息（包含代码）
    
    Args:
        name: 技能名称
        
    Returns:
        技能详情，包含 name, description, params, full_code
    """
    skill = skill_manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    return {
        "success": True,
        "skill": skill
    }


@router.post("/skills", response_model=SkillResponse)
async def create_skill(request: SkillCreateRequest):
    """
    创建新技能
    
    技能代码应该是函数体（不含 async def 声明），例如：
    ```
    wood = await bot.findBlock("oak_log", 32)
    if wood.get("found"):
        await bot.goTo(wood["x"], wood["y"], wood["z"])
        await bot.collectBlock("oak_log")
        return "采集成功"
    return "没找到木头"
    ```
    """
    result = skill_manager.save_skill(
        name=request.name,
        description=request.description,
        code=request.code,
        params=request.params or []
    )
    
    if result.get("success"):
        return SkillResponse(
            success=True,
            message=result.get("message"),
            skill=result.get("skill")
        )
    else:
        return SkillResponse(
            success=False,
            error=result.get("error")
        )


@router.delete("/skills/{name}")
async def delete_skill(name: str):
    """
    删除指定技能
    
    Args:
        name: 技能名称
    """
    result = skill_manager.delete_skill(name)
    
    if result.get("success"):
        return {"success": True, "message": result.get("message")}
    else:
        raise HTTPException(status_code=404, detail=result.get("error"))


@router.get("/skills/{name}/code")
async def get_skill_code(name: str):
    """
    获取技能的可执行代码
    
    Args:
        name: 技能名称
        
    Returns:
        完整的技能函数代码
    """
    code = skill_manager.get_skill_code(name)
    if not code:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    return {
        "success": True,
        "name": name,
        "code": code
    }


@router.get("/skills-description")
async def get_skills_description():
    """
    获取所有技能的描述文本（用于 LLM 提示词）
    
    Returns:
        格式化的技能描述文本
    """
    description = skill_manager.get_skills_description()
    return {
        "success": True,
        "description": description
    }


# ========== Task Management Endpoints ==========

@router.get("/tasks")
async def list_tasks():
    """
    获取当前所有任务状态
    
    Returns:
        包含运行中和等待中任务的列表
    """
    status = task_manager.get_status_summary()
    history = task_manager.get_recent_history(10)
    
    return {
        "success": True,
        "status": status,
        "history": history
    }


@router.get("/tasks/current")
async def get_current_task():
    """
    获取当前正在运行的主要任务
    
    Returns:
        当前任务详情，或 null
    """
    current = task_manager.current_task
    
    if current:
        return {
            "success": True,
            "task": current.to_dict()
        }
    else:
        return {
            "success": True,
            "task": None,
            "message": "没有正在运行的任务"
        }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    获取指定任务的详情
    
    Args:
        task_id: 任务ID
    """
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    
    return {
        "success": True,
        "task": task.to_dict()
    }


class StartSkillRequest(BaseModel):
    """启动技能请求"""
    skillName: str
    kwargs: Optional[Dict[str, Any]] = None


@router.post("/tasks/start-skill")
async def start_skill_task(request: StartSkillRequest):
    """
    启动一个后台技能任务
    
    Args:
        skillName: 技能名称
        kwargs: 技能参数（可选）
    """
    from app.script.executor import BotAPI
    
    skill = skill_manager.get_skill(request.skillName)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{request.skillName}' not found")
    
    # 创建后台任务
    async def run_skill():
        bot_api = BotAPI()
        return await bot_api.useSkill(request.skillName, **(request.kwargs or {}))
    
    task = task_manager.create_task(
        name=request.skillName,
        description=skill.get("description", ""),
        coroutine_func=run_skill
    )
    
    return {
        "success": True,
        "message": f"已启动技能 '{request.skillName}'",
        "task": task.to_dict()
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    取消指定任务
    
    Args:
        task_id: 任务ID
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    
    success = await task_manager.cancel_task(task_id)
    
    # 停止机器人移动
    try:
        await bot_client.execute_action("stopMoving", {})
    except:
        pass
    
    if success:
        return {"success": True, "message": f"已取消任务 {task_id}"}
    else:
        return {"success": False, "message": f"无法取消任务 {task_id}（可能已完成）"}


@router.post("/tasks/cancel-all")
async def cancel_all_tasks():
    """
    取消所有正在运行的任务
    """
    await task_manager.cancel_all_tasks()
    
    # 停止机器人移动
    try:
        await bot_client.execute_action("stopMoving", {})
    except:
        pass
    
    return {"success": True, "message": "已取消所有任务"}