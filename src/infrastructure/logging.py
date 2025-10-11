"""
结构化日志系统配置

基于structlog实现的结构化日志系统，支持：
- JSON格式输出
- 自动trace_id传递
- 上下文信息绑定
"""

import sys
from typing import Any, Dict, Optional

import structlog
from structlog.contextvars import merge_contextvars
from structlog.processors import (
    CallsiteParameter,
    CallsiteParameterAdder,
    TimeStamper,
    add_log_level,
    dict_tracebacks,
    format_exc_info,
)
from structlog.stdlib import (
    BoundLogger,
)
from structlog.types import Processor


def configure_logging(
    log_level: str = "INFO",
    json_output: bool = False,
    add_caller_info: bool = True
) -> None:
    """
    配置结构化日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: 是否输出JSON格式
        add_caller_info: 是否添加调用者信息
    """
    timestamper = TimeStamper(fmt="iso")

    processors: list[Processor] = [
        # 添加日志级别
        add_log_level,
        # 合并上下文变量
        merge_contextvars,
        # 添加时间戳
        timestamper,
        # 处理异常信息
        format_exc_info,
    ]

    # 可选添加调用者信息
    if add_caller_info:
        processors.append(
            CallsiteParameterAdder(
                parameters=[
                    CallsiteParameter.FILENAME,
                    CallsiteParameter.LINENO,
                    CallsiteParameter.FUNC_NAME,
                ]
            )
        )

    # 配置输出格式
    if json_output:
        # JSON格式输出
        processors.extend([
            dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        # 开发环境友好的控制台输出
        processors.append(
            structlog.dev.ConsoleRenderer()
        )

    # 配置structlog
    structlog.configure(
        processors=processors,
        wrapper_class=BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


class LoggerMixin:
    """
    日志混入类

    为任何类提供结构化日志能力
    """

    @property
    def logger(self) -> BoundLogger:
        """获取绑定了类名的logger实例"""
        if not hasattr(self, "_logger"):
            self._logger = structlog.get_logger(
                self.__class__.__module__ + "." + self.__class__.__name__
            )
        return self._logger

    def log_with_context(
        self,
        level: str,
        event: str,
        **kwargs: Any
    ) -> None:
        """
        带上下文的日志记录

        Args:
            level: 日志级别
            event: 事件名称
            **kwargs: 额外的上下文信息
        """
        log_method = getattr(self.logger, level.lower())
        log_method(event, **kwargs)


def bind_context(**kwargs: Any) -> None:
    """
    绑定全局上下文

    这些上下文会自动添加到所有后续的日志中

    Args:
        **kwargs: 要绑定的上下文键值对
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    解绑全局上下文

    Args:
        *keys: 要解绑的上下文键
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """清空所有全局上下文"""
    structlog.contextvars.clear_contextvars()


def get_logger(name: Optional[str] = None, **initial_context: Any) -> BoundLogger:
    """
    获取logger实例

    Args:
        name: logger名称
        **initial_context: 初始上下文

    Returns:
        绑定了初始上下文的logger
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


# 常用的日志事件名称常量
class LogEvent:
    """标准化的日志事件名称"""
    # 系统事件
    SYSTEM_STARTED = "system_started"
    SYSTEM_SHUTDOWN = "system_shutdown"

    # 请求生命周期
    REQUEST_RECEIVED = "request_received"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_FAILED = "request_failed"

    # 代理执行
    AGENT_STARTED = "agent_started"
    AGENT_STEP = "agent_step"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # 工具执行
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"

    # 数据源
    DATA_FETCH_STARTED = "data_fetch_started"
    DATA_FETCH_COMPLETED = "data_fetch_completed"
    DATA_FETCH_FAILED = "data_fetch_failed"

    # LLM调用
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_ERROR = "llm_error"

    # 性能指标
    PERFORMANCE_METRIC = "performance_metric"

    # 错误与警告
    ERROR_OCCURRED = "error_occurred"
    WARNING_RAISED = "warning_raised"
    EXCEPTION_CAUGHT = "exception_caught"


def log_performance(
    event: str,
    duration_ms: float,
    **extra_metrics: Any
) -> None:
    """
    记录性能指标

    Args:
        event: 事件名称
        duration_ms: 持续时间(毫秒)
        **extra_metrics: 额外的性能指标
    """
    logger = get_logger()
    logger.info(
        LogEvent.PERFORMANCE_METRIC,
        event=event,
        duration_ms=duration_ms,
        **extra_metrics
    )
