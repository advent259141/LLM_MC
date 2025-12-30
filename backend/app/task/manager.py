"""
Task Manager for LLM-MC
Manages background skill/script execution without blocking LLM decisions
"""
import asyncio
import time
import traceback
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 执行完成
    FAILED = "failed"         # 执行失败
    CANCELLED = "cancelled"   # 被取消


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    progress: str = ""           # 当前进度描述
    result: Any = None           # 执行结果
    error: Optional[str] = None  # 错误信息
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    logs: List[str] = field(default_factory=list)
    
    # asyncio 任务引用
    _async_task: Optional[asyncio.Task] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result if not callable(self.result) else str(self.result),
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self._get_duration(),
            "logs": self.logs[-10:]  # 只返回最近10条日志
        }
    
    def _get_duration(self) -> Optional[float]:
        """获取执行时长"""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return round(end_time - self.started_at, 2)


class TaskManager:
    """
    任务管理器
    
    功能：
    - 管理后台任务的生命周期
    - 支持任务状态查询
    - 支持任务取消
    - 提供任务进度更新接口
    """
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._tasks: Dict[str, Task] = {}
        self._task_history: List[Task] = []  # 已完成的任务历史
        self._max_history = 20  # 最多保留20条历史
    
    @property
    def current_task(self) -> Optional[Task]:
        """获取当前正在运行的主要任务（最新创建的运行中任务）"""
        running_tasks = [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
        if running_tasks:
            return max(running_tasks, key=lambda t: t.created_at)
        return None
    
    @property
    def running_tasks(self) -> List[Task]:
        """获取所有正在运行的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
    
    @property
    def pending_tasks(self) -> List[Task]:
        """获取所有等待中的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
    
    def create_task(
        self,
        name: str,
        description: str,
        coroutine_func: Callable,
        *args,
        **kwargs
    ) -> Task:
        """
        创建并启动一个后台任务
        
        Args:
            name: 任务名称
            description: 任务描述
            coroutine_func: 异步函数
            *args, **kwargs: 传递给异步函数的参数
            
        Returns:
            创建的任务对象
        """
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            name=name,
            description=description
        )
        
        self._tasks[task_id] = task
        
        # 创建包装后的协程
        async def wrapped_coroutine():
            try:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                task.progress = "开始执行..."
                
                # 执行实际任务
                result = await coroutine_func(*args, **kwargs)
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = "执行完成"
                task.completed_at = time.time()
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.progress = "已取消"
                task.completed_at = time.time()
                raise
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.progress = f"执行失败: {str(e)[:50]}"
                task.completed_at = time.time()
                task.logs.append(f"错误详情: {traceback.format_exc()}")
                
            finally:
                # 移动到历史
                self._move_to_history(task_id)
        
        # 启动异步任务
        task._async_task = asyncio.create_task(wrapped_coroutine())
        
        return task
    
    def _move_to_history(self, task_id: str):
        """将任务移动到历史记录"""
        if task_id in self._tasks:
            task = self._tasks.pop(task_id)
            self._task_history.append(task)
            
            # 限制历史数量
            if len(self._task_history) > self._max_history:
                self._task_history = self._task_history[-self._max_history:]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        if task_id in self._tasks:
            return self._tasks[task_id]
        # 在历史中查找
        for task in self._task_history:
            if task.id == task_id:
                return task
        return None
    
    def update_progress(self, task_id: str, progress: str):
        """更新任务进度"""
        if task_id in self._tasks:
            self._tasks[task_id].progress = progress
            self._tasks[task_id].logs.append(progress)
    
    def add_log(self, task_id: str, log: str):
        """添加任务日志"""
        if task_id in self._tasks:
            self._tasks[task_id].logs.append(log)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Returns:
            是否成功取消
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        if task.status != TaskStatus.RUNNING:
            return False
        
        if task._async_task:
            task._async_task.cancel()
            try:
                await task._async_task
            except asyncio.CancelledError:
                pass
        
        return True
    
    async def cancel_all_tasks(self):
        """取消所有正在运行的任务"""
        for task_id in list(self._tasks.keys()):
            await self.cancel_task(task_id)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取任务状态摘要（用于 LLM 提示词）
        
        Returns:
            包含当前任务状态的摘要信息
        """
        running = self.running_tasks
        pending = self.pending_tasks
        
        if not running and not pending:
            return {
                "has_active_tasks": False,
                "summary": "当前没有正在执行的任务"
            }
        
        summaries = []
        
        for task in running:
            duration = task._get_duration()
            summaries.append(
                f"[运行中] {task.name}: {task.progress} (已执行 {duration}秒)"
            )
        
        for task in pending:
            summaries.append(f"[等待中] {task.name}")
        
        return {
            "has_active_tasks": True,
            "running_count": len(running),
            "pending_count": len(pending),
            "summary": "\n".join(summaries),
            "tasks": [t.to_dict() for t in running + pending]
        }
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的任务历史"""
        recent = self._task_history[-limit:]
        return [t.to_dict() for t in reversed(recent)]


# 全局任务管理器实例
task_manager = TaskManager()