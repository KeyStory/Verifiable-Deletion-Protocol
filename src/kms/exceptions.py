"""
KMS (Key Management Service) 自定义异常类

这个模块定义了KMS操作中可能出现的所有异常类型。
"""


class KMSError(Exception):
    """KMS基础异常类，所有KMS异常的父类"""

    def __init__(self, message: str, details: dict | None = None):
        """
        Args:
            message: 错误描述
            details: 额外的错误详情（不应包含敏感信息）
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ===== 密钥操作相关异常 =====


class KeyNotFoundError(KMSError):
    """密钥不存在异常"""

    def __init__(self, key_id: str):
        super().__init__(message=f"Key not found", details={"key_id": key_id})


class KeyAlreadyExistsError(KMSError):
    """密钥已存在异常（用于防止重复创建）"""

    def __init__(self, key_id: str):
        super().__init__(message=f"Key already exists", details={"key_id": key_id})


class KeyInvalidStateError(KMSError):
    """密钥状态不正确异常"""

    def __init__(self, key_id: str, current_state: str, required_state: str):
        super().__init__(
            message=f"Key is in invalid state for this operation",
            details={
                "key_id": key_id,
                "current_state": current_state,
                "required_state": required_state,
            },
        )


class KeyDestroyedError(KMSError):
    """访问已销毁的密钥异常"""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"Cannot access destroyed key", details={"key_id": key_id}
        )


# ===== 权限和访问控制异常 =====


class PermissionDeniedError(KMSError):
    """权限不足异常"""

    def __init__(self, key_id: str, owner_id: str, requester_id: str):
        super().__init__(
            message=f"Permission denied",
            details={"key_id": key_id, "owner": owner_id, "requester": requester_id},
        )


# ===== 密钥销毁相关异常 =====


class DestructionFailedError(KMSError):
    """密钥销毁失败异常"""

    def __init__(self, key_id: str, method: str, reason: str):
        super().__init__(
            message=f"Key destruction failed",
            details={"key_id": key_id, "method": method, "reason": reason},
        )


class UnsupportedDestructionMethodError(KMSError):
    """不支持的销毁方法异常"""

    def __init__(self, method: str, supported_methods: list):
        super().__init__(
            message=f"Unsupported destruction method",
            details={"method": method, "supported_methods": supported_methods},
        )


# ===== 配置和初始化异常 =====


class KMSConfigurationError(KMSError):
    """KMS配置错误异常"""

    def __init__(self, parameter: str, reason: str):
        super().__init__(
            message=f"KMS configuration error",
            details={"parameter": parameter, "reason": reason},
        )


class InvalidKeyParameterError(KMSError):
    """无效的密钥参数异常"""

    def __init__(self, parameter: str, value, reason: str):
        super().__init__(
            message=f"Invalid key parameter",
            details={
                "parameter": parameter,
                "value": str(value),  # 转为字符串避免泄露
                "reason": reason,
            },
        )
