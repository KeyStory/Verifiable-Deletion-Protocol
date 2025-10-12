"""
KMS (Key Management Service) 工具函数模块

这个模块提供KMS所需的通用工具函数，包括：
1. 密码学安全的随机数生成
2. 内存安全操作（清零、覆写）- 使用ctypes直接操作内存
3. 时间戳生成
4. 数据验证

设计原则：
- 对于密钥销毁，安全性 > 性能 > 便利性
- 使用ctypes直接操作内存，确保数据真正被销毁
- 使用from_buffer()而不是魔法数字偏移，避免Python版本兼容性问题
"""

import secrets
import ctypes
import hashlib
from datetime import datetime, timezone


# ===== 密码学安全的随机数生成 =====


def generate_random_bytes(length: int) -> bytes:
    """
    生成密码学安全的随机字节串

    使用Python的secrets模块，它基于操作系统的CSPRNG：
    - Linux: /dev/urandom
    - Windows: CryptGenRandom
    - macOS: /dev/urandom

    Args:
        length: 需要生成的字节数

    Returns:
        随机字节串

    Raises:
        ValueError: 如果length <= 0
    """
    if length <= 0:
        raise ValueError(f"Length must be positive, got {length}")

    return secrets.token_bytes(length)


def generate_key_id(prefix: str = "key") -> str:
    """
    生成唯一的密钥ID

    格式: {prefix}_{32字符十六进制随机字符串}
    示例: key_a3f5c8d9e2b1f4a6c7d8e9f0a1b2c3d4

    Args:
        prefix: ID前缀

    Returns:
        唯一密钥ID
    """
    # 生成16字节随机数，转为32字符十六进制
    random_part = secrets.token_hex(16)
    return f"{prefix}_{random_part}"


# ===== 内存安全操作（使用ctypes）=====


def secure_zero_memory(data: bytearray) -> None:
    """
    安全地将内存清零（使用ctypes直接操作）

    使用ctypes.from_buffer()获取bytearray的内存缓冲区，
    然后用C的memset清零。这种方法：
    1. 不依赖Python对象内存布局的魔法数字
    2. 兼容所有Python 3.x版本
    3. 真正清零内存，不会被优化掉

    Args:
        data: 要清零的bytearray对象

    Raises:
        TypeError: 如果data不是bytearray
    """
    if not isinstance(data, bytearray):
        raise TypeError("Data must be bytearray, not bytes (bytes is immutable)")

    length = len(data)
    if length == 0:
        return

    # 使用from_buffer创建C数组，直接映射到bytearray的内存
    try:
        c_buffer = (ctypes.c_char * length).from_buffer(data)
        # 使用C的memset清零
        ctypes.memset(ctypes.addressof(c_buffer), 0, length)
    except Exception as e:
        # 如果ctypes方法失败，降级到Python循环（保证功能可用）
        for i in range(length):
            data[i] = 0
        # 但记录警告，因为这可能不够安全
        import warnings

        warnings.warn(f"ctypes.memset failed, using fallback method: {e}")


def secure_overwrite_memory(data: bytearray, pattern: bytes | None = None) -> None:
    """
    用指定模式覆写内存（使用ctypes直接操作）

    Args:
        data: 要覆写的bytearray对象
        pattern: 覆写模式，如果为None则使用随机数据

    Raises:
        TypeError: 如果data不是bytearray
        ValueError: 如果pattern长度与data不匹配
    """
    if not isinstance(data, bytearray):
        raise TypeError("Data must be bytearray")

    length = len(data)
    if length == 0:
        return

    if pattern is None:
        # 使用随机数据
        pattern = generate_random_bytes(length)

    if len(pattern) != length:
        raise ValueError(f"Pattern length {len(pattern)} != data length {length}")

    # 使用ctypes直接复制内存
    try:
        dst_buffer = (ctypes.c_char * length).from_buffer(data)
        src_buffer = (ctypes.c_char * length).from_buffer_copy(pattern)
        ctypes.memmove(
            ctypes.addressof(dst_buffer), ctypes.addressof(src_buffer), length
        )
    except Exception as e:
        # 降级到Python循环
        for i in range(length):
            data[i] = pattern[i]
        import warnings

        warnings.warn(f"ctypes.memmove failed, using fallback method: {e}")


def dod_overwrite_memory(data: bytearray) -> None:
    """
    使用DoD 5220.22-M标准覆写内存

    DoD标准要求3次覆写：
    1. Pass 1: 全0 (0x00)
    2. Pass 2: 全1 (0xFF)
    3. Pass 3: 随机数据

    这是美国国防部推荐的数据销毁标准，可以有效防止：
    - 软件数据恢复
    - 一般的硬件数据恢复
    - 大部分实验室级别的数据恢复

    Args:
        data: 要覆写的bytearray对象
    """
    if not isinstance(data, bytearray):
        raise TypeError("Data must be bytearray")

    length = len(data)
    if length == 0:
        return

    # Pass 1: 全零
    secure_overwrite_memory(data, b"\x00" * length)

    # Pass 2: 全一
    secure_overwrite_memory(data, b"\xff" * length)

    # Pass 3: 随机数据
    secure_overwrite_memory(data, None)


# ===== 时间戳工具 =====


def get_utc_timestamp() -> datetime:
    """
    获取UTC时间戳

    Returns:
        带时区信息的UTC时间
    """
    return datetime.now(timezone.utc)


def timestamp_to_iso(ts: datetime) -> str:
    """
    将时间戳转换为ISO 8601格式字符串

    Args:
        ts: datetime对象

    Returns:
        ISO格式字符串
    """
    return ts.isoformat()


# ===== 数据验证 =====


def validate_key_size(key_size: int, algorithm: str) -> bool:
    """
    验证密钥长度是否符合算法要求

    Args:
        key_size: 密钥长度（字节）
        algorithm: 加密算法名称

    Returns:
        是否有效
    """
    # 定义各算法的有效密钥长度
    valid_sizes = {
        "AES-128-GCM": [16],  # 128 bits
        "AES-256-GCM": [32],  # 256 bits
        "ChaCha20-Poly1305": [32],  # 256 bits
        "AES-128-CBC": [16],
        "AES-256-CBC": [32],
    }

    # 规范化算法名称（转大写）
    algorithm_upper = algorithm.upper()

    if algorithm_upper not in valid_sizes:
        # 未知算法，接受常见长度
        return key_size in [16, 24, 32]

    return key_size in valid_sizes[algorithm_upper]


def compute_key_fingerprint(key_data: bytes) -> str:
    """
    计算密钥指纹（用于日志，不泄露密钥内容）

    使用SHA-256哈希的前16个字符作为指纹

    Args:
        key_data: 密钥数据

    Returns:
        密钥指纹（16字符十六进制）
    """
    hash_obj = hashlib.sha256(key_data)
    return hash_obj.hexdigest()[:16]
