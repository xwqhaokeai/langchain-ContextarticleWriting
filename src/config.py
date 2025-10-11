from typing import List, Optional, Literal
import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class AppSettings(BaseSettings):
    """应用全局配置"""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="日志级别"
    )
    output_dir: str = Field(default="output", description="输出文件保存目录")
    host: str = Field(default="0.0.0.0", description="API监听地址")
    port: int = Field(default=8000, description="API监听端口")
    reload: bool = Field(default=True, description="是否开启热重载")
    workers: int = Field(default=1, description="工作进程数")

class ApiSettings(BaseSettings):
    """API 相关配置"""
    supported_styles: List[str] = Field(
        default=["popular science article", "review", "blog post"],
        description="支持的文章风格"
    )
    supported_languages: List[str] = Field(
        default=[
            "en", "zh-CN", "zh-TW", "ja", "fr"
        ],
        description="支持的语言 (代码)"
    )
    default_style: str = Field(default="popular science article", description="默认文章风格")
    default_language: str = Field(default="English", description="默认语言")
    max_keywords: int = Field(default=10, description="最大关键词数量")
    max_focus_areas: int = Field(default=5, description="最大焦点领域数量")
    default_max_sources: int = Field(default=5, description="默认最大数据源数量")
    max_sources_limit: int = Field(default=20, description="最大数据源限制")
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS 允许的源"
    )

class Settings(BaseSettings):
    """所有配置的容器"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    # LLM 配置
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"), description="OpenAI API 密钥")
    openai_api_base: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_BASE"), description="OpenAI API Base URL")
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"), description="OpenAI 模型名称")
    temperature: float = Field(default=0.7, description="LLM 温度参数")

    # 插件配置
    JIMENG_AK: Optional[str] = Field(default=None, description="即梦图像生成服务的Access Key")
    JIMENG_SK: Optional[str] = Field(default=None, description="即梦图像生成服务的Secret Key")

@lru_cache
def get_settings() -> Settings:
    """获取配置实例 (带缓存)"""
    return Settings()
