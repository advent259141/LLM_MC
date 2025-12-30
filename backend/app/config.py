from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


# 获取项目根目录的.env路径
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Configuration
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4"
    llm_max_tokens: int = 1024  # LLM响应最大token数
    llm_temperature: float = 0.7  # 创造性参数 (0-1)
    
    # Context/Memory Configuration
    max_history_length: int = 20  # 保留的对话历史条数
    max_chat_messages: int = 10  # 保留的游戏聊天消息数
    max_events: int = 10  # 保留的游戏事件数
    use_conversation_history: bool = False  # 是否在决策时使用对话历史
    
    # Bot Service Configuration (Node.js mineflayer service)
    bot_service_url: str = "http://localhost:3001"
    bot_ws_url: str = "ws://localhost:3001/ws"
    
    # Agent Configuration
    agent_tick_rate: float = 2.0  # 空闲时的决策间隔（秒）
    agent_task_tick_rate: float = 15.0  # 有后台任务时的决策间隔（秒），0 表示完全事件驱动
    auto_start_agent: bool = True  # 是否自动启动 Agent
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # 忽略.env中的额外字段（给Bot服务用的配置）
    mc_host: Optional[str] = None
    mc_port: Optional[int] = None
    mc_username: Optional[str] = None
    mc_version: Optional[str] = None
    bot_service_port: Optional[int] = None
    backend_port: Optional[int] = None
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的额外字段


settings = Settings()