"""
KMS (Key Management Service) Package

这是密钥管理服务的Python包入口文件。

包结构：
    kms/
    ├── __init__.py          # 包初始化（本文件）
    ├── exceptions.py        # 异常类定义
    ├── utils.py            # 工具函数
    └── key_manager.py      # 核心KMS类（待实现）

使用示例：
    >>> from src.kms import KeyManagementService, DestructionMethod
    >>> kms = KeyManagementService()
    >>> key_id = kms.generate_key(key_size=32, algorithm="AES-256-GCM")
    >>> kms.destroy_key(key_id, method=DestructionMethod.DOD_OVERWRITE)

版本历史：
    v0.1.0 - 基础架构（异常、工具）
    v0.2.0 - 核心KMS实现
"""

# 包元数据
__version__ = "0.2.0"
__author__ = "Liang"
__description__ = "Key Management Service with Verifiable Deletion"

# ===== 导出异常类 =====
from .exceptions import (
    # 基础异常
    KMSError,
    # 密钥操作异常
    KeyNotFoundError,
    KeyAlreadyExistsError,
    KeyInvalidStateError,
    KeyDestroyedError,
    # 权限异常
    PermissionDeniedError,
    # 销毁异常
    DestructionFailedError,
    UnsupportedDestructionMethodError,
    # 配置异常
    KMSConfigurationError,
    InvalidKeyParameterError,
)

# ===== 导出工具函数 =====
from .utils import (
    # 随机数生成
    generate_random_bytes,
    generate_key_id,
    # 内存安全操作
    secure_zero_memory,
    secure_overwrite_memory,
    dod_overwrite_memory,
    # 时间戳工具
    get_utc_timestamp,
    timestamp_to_iso,
    # 数据验证
    validate_key_size,
    compute_key_fingerprint,
)

# ===== 核心类 =====
from .key_manager import (
    KeyManagementService,
    KeyStatus,
    DestructionMethod,
    KeyMetadata,
    SecureKey,
)

# ===== __all__ 定义（控制 from kms import * 的行为）=====
__all__ = [
    # 包信息
    "__version__",
    # 异常类
    "KMSError",
    "KeyNotFoundError",
    "KeyAlreadyExistsError",
    "KeyInvalidStateError",
    "KeyDestroyedError",
    "PermissionDeniedError",
    "DestructionFailedError",
    "UnsupportedDestructionMethodError",
    "KMSConfigurationError",
    "InvalidKeyParameterError",
    # 工具函数
    "generate_random_bytes",
    "generate_key_id",
    "secure_zero_memory",
    "secure_overwrite_memory",
    "dod_overwrite_memory",
    "get_utc_timestamp",
    "timestamp_to_iso",
    "validate_key_size",
    "compute_key_fingerprint",
    # 核心类（待实现）
    "KeyManagementService",
    "KeyStatus",
    "DestructionMethod",
    "KeyMetadata",
    "SecureKey",
]


# ===== 包级别的便利函数 =====


def get_version() -> str:
    """
    获取KMS包版本号

    Returns:
        版本号字符串
    """
    return __version__


def get_package_info() -> dict[str, str]:
    """
    获取包的完整信息

    Returns:
        包含版本、作者、描述的字典
    """
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
    }


# ===== 包级别的初始化检查 =====


def _check_dependencies():
    """
    检查必要的依赖是否可用

    在包导入时自动执行，确保环境正确
    """
    required_modules = [
        "secrets",  # 密码学安全随机数
        "ctypes",  # 内存操作
        "hashlib",  # 哈希计算
        "datetime",  # 时间戳
    ]

    missing_modules = []
    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(module_name)

    if missing_modules:
        import warnings

        warnings.warn(
            f"KMS package missing dependencies: {', '.join(missing_modules)}. "
            f"Some features may not work correctly."
        )


# 执行依赖检查
_check_dependencies()
