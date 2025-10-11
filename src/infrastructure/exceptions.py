"""
自定义异常体系

定义系统中所有的自定义异常类，确保错误信息的结构化
和可追踪性。每个模块都有其专属的异常基类。
"""

from typing import Any, Dict, Optional
from uuid import UUID


class BaseError(Exception):
    """
    系统基础异常类

    所有自定义异常都应该继承自此类
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.trace_id = trace_id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录和API响应"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "trace_id": self.trace_id
        }


# ============= 上下文供应层异常 =============

class ContextProviderError(BaseError):
    """上下文供应模块基础异常"""
    pass


class DataSourceError(ContextProviderError):
    """数据源相关异常"""
    pass


class DataSourceConnectionError(DataSourceError):
    """数据源连接失败"""
    def __init__(self, source_name: str, original_error: Exception, **kwargs):
        super().__init__(
            message=f"Failed to connect to data source '{source_name}': {str(original_error)}",
            details={"source_name": source_name, "original_error": str(original_error)},
            **kwargs
        )
        self.__cause__ = original_error


class DataSourceTimeoutError(DataSourceError):
    """数据源请求超时"""
    def __init__(self, source_name: str, timeout_seconds: float, **kwargs):
        super().__init__(
            message=f"Data source '{source_name}' request timed out after {timeout_seconds}s",
            details={"source_name": source_name, "timeout_seconds": timeout_seconds},
            **kwargs
        )


class ProcessingError(ContextProviderError):
    """数据处理相关异常"""
    pass


class DataValidationError(ProcessingError):
    """数据验证失败"""
    def __init__(self, processor_name: str, validation_errors: list, **kwargs):
        super().__init__(
            message=f"Data validation failed in processor '{processor_name}'",
            details={"processor_name": processor_name, "validation_errors": validation_errors},
            **kwargs
        )


class FormattingError(ContextProviderError):
    """格式化相关异常"""
    pass


# ============= 代理执行层异常 =============

class AgentError(BaseError):
    """代理执行层基础异常"""
    def __init__(
        self,
        message: str,
        agent_id: Optional[UUID] = None,
        agent_state: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.agent_id = agent_id
        self.agent_state = agent_state
        if agent_id:
            self.details["agent_id"] = str(agent_id)
        if agent_state:
            self.details["agent_state"] = agent_state


class AgentConfigurationError(AgentError):
    """代理配置错误"""
    def __init__(self, config_path: str, error_details: str, **kwargs):
        super().__init__(
            message=f"Invalid agent configuration at '{config_path}': {error_details}",
            details={"config_path": config_path, "error_details": error_details},
            **kwargs
        )


class AgentExecutionError(AgentError):
    """代理执行错误"""
    pass


class LLMResponseError(AgentExecutionError):
    """LLM响应解析失败"""
    def __init__(self, raw_response: str, parse_error: str, **kwargs):
        super().__init__(
            message=f"Failed to parse LLM response: {parse_error}",
            details={"raw_response": raw_response[:500], "parse_error": parse_error},
            **kwargs
        )


class ToolNotFoundError(AgentExecutionError):
    """请求的工具不存在"""
    def __init__(self, tool_name: str, available_tools: list, **kwargs):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            details={"tool_name": tool_name, "available_tools": available_tools},
            **kwargs
        )


class ToolExecutionError(AgentExecutionError):
    """工具执行失败"""
    def __init__(self, tool_name: str, error: Exception, **kwargs):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {str(error)}",
            details={"tool_name": tool_name, "error": str(error)},
            **kwargs
        )
        self.__cause__ = error


class GuardrailViolationError(AgentExecutionError):
    """违反护栏规则"""
    def __init__(self, violation: str, **kwargs):
        super().__init__(
            message=f"Guardrail violation: {violation}",
            details={"violation": violation},
            **kwargs
        )


# ============= LLM相关异常 =============

class LLMError(BaseError):
    """LLM调用基础异常"""
    pass


class LLMConnectionError(LLMError):
    """LLM服务连接失败"""
    def __init__(self, provider: str, error: Exception, **kwargs):
        super().__init__(
            message=f"Failed to connect to LLM provider '{provider}': {str(error)}",
            details={"provider": provider, "error": str(error)},
            **kwargs
        )
        self.__cause__ = error


class LLMRateLimitError(LLMError):
    """LLM调用达到速率限制"""
    def __init__(self, provider: str, retry_after: Optional[float] = None, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded for LLM provider '{provider}'",
            details={"provider": provider, "retry_after": retry_after},
            **kwargs
        )


class LLMTokenLimitError(LLMError):
    """超过Token限制"""
    def __init__(self, max_tokens: int, actual_tokens: int, **kwargs):
        super().__init__(
            message=f"Token limit exceeded: {actual_tokens} > {max_tokens}",
            details={"max_tokens": max_tokens, "actual_tokens": actual_tokens},
            **kwargs
        )