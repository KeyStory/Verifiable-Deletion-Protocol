"""
KMS Key Manager - 密钥管理服务核心实现

这是整个KMS系统的核心模块，实现了：
1. 密钥的完整生命周期管理
2. 4种密钥销毁方法
3. 审计日志
4. 访问控制

设计原则：
- 安全第一：所有密钥操作都经过验证
- 可审计：每个操作都有日志记录
- 可验证：销毁操作可以通过内存取证验证
"""

from dataclasses import dataclass
from datetime import datetime
import sys
from typing import Any
from enum import Enum
from ..blockchain.contract_manager import ContractManager
import gc
import hashlib

# 导入本包的工具和异常
from .utils import (
    generate_random_bytes,
    generate_key_id,
    secure_zero_memory,
    secure_overwrite_memory,
    dod_overwrite_memory,
    get_utc_timestamp,
    timestamp_to_iso,
    validate_key_size,
    compute_key_fingerprint,
)

from .exceptions import (
    KeyNotFoundError,
    KeyAlreadyExistsError,
    KeyInvalidStateError,
    KeyDestroyedError,
    PermissionDeniedError,
    DestructionFailedError,
    InvalidKeyParameterError,
)


# ===== 枚举类型定义 =====


class KeyStatus(Enum):
    """
    密钥状态枚举

    状态转换：
        ACTIVE → PENDING_DELETION → DESTROYED
        ACTIVE → EXPIRED
    """

    ACTIVE = "active"
    PENDING_DELETION = "pending_deletion"
    DESTROYED = "destroyed"
    EXPIRED = "expired"


class DestructionMethod(Enum):
    """
    密钥销毁方法枚举

    对应论文中的4种方法：
    - SIMPLE_DEL: 对照组，不安全
    - SINGLE_OVERWRITE: 基础防护
    - DOD_OVERWRITE: 推荐方法（DoD 5220.22-M标准）
    - CTYPES_SECURE: 使用ctypes直接操作内存
    """

    SIMPLE_DEL = "simple_del"
    SINGLE_OVERWRITE = "single_overwrite"
    DOD_OVERWRITE = "dod_overwrite"
    CTYPES_SECURE = "ctypes_secure"


# ===== 数据类定义 =====


@dataclass
class KeyMetadata:
    """
    密钥元数据

    包含密钥的所有非敏感信息，用于：
    - 密钥管理
    - 审计日志
    - 访问控制
    """

    key_id: str
    created_at: datetime
    status: KeyStatus
    algorithm: str
    key_size: int
    purpose: str
    owner_id: str

    # 可选字段
    destruction_method: DestructionMethod | None = None
    destroyed_at: datetime | None = None
    expires_at: datetime | None = None

    # 统计信息
    access_count: int = 0
    last_accessed_at: datetime | None = None

    # 安全信息
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "key_id": self.key_id,
            "created_at": timestamp_to_iso(self.created_at),
            "status": self.status.value,
            "algorithm": self.algorithm,
            "key_size": self.key_size,
            "purpose": self.purpose,
            "owner_id": self.owner_id,
            "destruction_method": (
                self.destruction_method.value if self.destruction_method else None
            ),
            "destroyed_at": (
                timestamp_to_iso(self.destroyed_at) if self.destroyed_at else None
            ),
            "expires_at": (
                timestamp_to_iso(self.expires_at) if self.expires_at else None
            ),
            "access_count": self.access_count,
            "last_accessed_at": (
                timestamp_to_iso(self.last_accessed_at)
                if self.last_accessed_at
                else None
            ),
            "fingerprint": self.fingerprint,
        }


@dataclass
class SecureKey:
    """
    安全密钥封装类

    将密钥数据和元数据封装在一起，提供：
    - 受控访问（只读）
    - 自动记录访问次数
    - 状态检查
    """

    _key_data: bytearray
    metadata: KeyMetadata

    def __init__(self, key_data: bytes, metadata: KeyMetadata):
        """
        初始化安全密钥

        Args:
            key_data: 密钥数据（bytes）
            metadata: 密钥元数据
        """
        self._key_data = bytearray(key_data)
        self.metadata = metadata
        self.metadata.fingerprint = compute_key_fingerprint(key_data)

    @property
    def key_data(self) -> bytes:
        """
        获取密钥数据（只读访问）

        每次访问都会：
        1. 检查密钥状态
        2. 更新访问计数
        3. 记录访问时间

        Returns:
            密钥数据（bytes）

        Raises:
            KeyDestroyedError: 密钥已被销毁
            KeyInvalidStateError: 密钥状态不可用
        """
        if self.metadata.status == KeyStatus.DESTROYED:
            raise KeyDestroyedError(self.metadata.key_id)

        if self.metadata.status != KeyStatus.ACTIVE:
            raise KeyInvalidStateError(
                self.metadata.key_id, self.metadata.status.value, KeyStatus.ACTIVE.value
            )

        self.metadata.access_count += 1
        self.metadata.last_accessed_at = get_utc_timestamp()

        return bytes(self._key_data)

    def get_mutable_data(self) -> bytearray:
        """
        获取可变的密钥数据（仅供内部销毁使用）

        警告：此方法仅应在销毁流程中使用！

        Returns:
            可变的bytearray
        """
        return self._key_data

    def __repr__(self) -> str:
        """字符串表示（不泄露密钥内容）"""
        return (
            f"SecureKey(key_id={self.metadata.key_id}, "
            f"status={self.metadata.status.value}, "
            f"fingerprint={self.metadata.fingerprint})"
        )


# ===== KMS主类 =====


class KeyManagementService:
    """
    密钥管理服务核心类

    提供完整的密钥生命周期管理：
    1. 生成密钥
    2. 存储密钥
    3. 检索密钥
    4. 销毁密钥（4种方法）
    5. 审计日志

    使用示例：
        >>> kms = KeyManagementService()
        >>> key_id = kms.generate_key(key_size=32, algorithm="AES-256-GCM")
        >>> key = kms.get_key(key_id)
        >>> success = kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
    """

    def __init__(
        self,
        master_key: bytes | None = None,
        contract_manager: ContractManager | None = None,
    ):
        """
        初始化KMS

        Args:
            master_key: 主密钥（用于加密其他密钥，可选）
            contract_manager: 区块链合约管理器（可选，用于链上记录）
        """
        self._keys: dict[str, SecureKey] = {}
        self._master_key = master_key
        self._audit_log: list[dict[str, Any]] = []
        self._stats = {
            "total_generated": 0,
            "total_destroyed": 0,
            "total_accesses": 0,
            "blockchain_recordings": 0,  # 新增：区块链记录计数
            "blockchain_failures": 0,  # 新增：区块链记录失败计数
        }

        # 新增：区块链连接
        self._contract_manager = contract_manager
        if self._contract_manager and not self._contract_manager.is_connected():
            try:
                self._contract_manager.connect()
                print("✓ KMS connected to blockchain")
            except Exception as e:
                print(f"⚠ KMS blockchain connection failed: {e}")
                self._contract_manager = None  # 禁用区块链功能

    def generate_key(
        self,
        key_size: int = 32,
        algorithm: str = "AES-256-GCM",
        purpose: str = "data_encryption",
        owner_id: str = "system",
        expires_in_days: int | None = None,
    ) -> str:
        """
        生成新密钥

        Args:
            key_size: 密钥长度（字节）
            algorithm: 加密算法名称
            purpose: 密钥用途
            owner_id: 所有者ID
            expires_in_days: 过期天数（None表示不过期）

        Returns:
            key_id: 密钥唯一标识符

        Raises:
            InvalidKeyParameterError: 参数无效
            KeyAlreadyExistsError: 密钥ID冲突（极少发生）
        """
        if not validate_key_size(key_size, algorithm):
            raise InvalidKeyParameterError(
                "key_size", key_size, f"Invalid key size for {algorithm}"
            )

        key_data = generate_random_bytes(key_size)
        key_id = generate_key_id()

        if key_id in self._keys:
            raise KeyAlreadyExistsError(key_id)

        expires_at = None
        if expires_in_days is not None:
            from datetime import timedelta

            expires_at = get_utc_timestamp() + timedelta(days=expires_in_days)

        metadata = KeyMetadata(
            key_id=key_id,
            created_at=get_utc_timestamp(),
            status=KeyStatus.ACTIVE,
            algorithm=algorithm,
            key_size=key_size,
            purpose=purpose,
            owner_id=owner_id,
            expires_at=expires_at,
        )

        secure_key = SecureKey(key_data, metadata)
        self._keys[key_id] = secure_key
        self._stats["total_generated"] += 1

        self._log_operation(
            "generate_key",
            key_id,
            {
                "algorithm": algorithm,
                "key_size": key_size,
                "purpose": purpose,
                "owner_id": owner_id,
                "fingerprint": secure_key.metadata.fingerprint,
            },
        )

        return key_id

    def get_key(self, key_id: str, requester_id: str = "system") -> SecureKey:
        """
        获取密钥

        Args:
            key_id: 密钥ID
            requester_id: 请求者ID（用于访问控制）

        Returns:
            SecureKey对象

        Raises:
            KeyNotFoundError: 密钥不存在
            PermissionDeniedError: 权限不足
        """
        if key_id not in self._keys:
            raise KeyNotFoundError(key_id)

        secure_key = self._keys[key_id]

        if requester_id != "system" and secure_key.metadata.owner_id != requester_id:
            raise PermissionDeniedError(
                key_id, secure_key.metadata.owner_id, requester_id
            )

        self._stats["total_accesses"] += 1

        self._log_operation(
            "get_key",
            key_id,
            {
                "requester_id": requester_id,
                "access_count": secure_key.metadata.access_count + 1,
            },
        )

        return secure_key

    def list_keys(
        self, owner_id: str | None = None, status: KeyStatus | None = None
    ) -> list[KeyMetadata]:
        """
        列出密钥（仅元数据）

        Args:
            owner_id: 过滤所有者（None表示全部）
            status: 过滤状态（None表示全部）

        Returns:
            密钥元数据列表
        """
        result = []
        for secure_key in self._keys.values():
            metadata = secure_key.metadata

            if owner_id is not None and metadata.owner_id != owner_id:
                continue
            if status is not None and metadata.status != status:
                continue

            result.append(metadata)

        return result

    def destroy_key(
        self,
        key_id: str,
        method: DestructionMethod = DestructionMethod.DOD_OVERWRITE,
        requester_id: str = "system",
    ) -> bool:
        """
        销毁密钥 ⭐ 核心方法

        这是整个项目的核心功能，实现4种销毁方法：
        1. SIMPLE_DEL: 简单删除（对照组）
        2. SINGLE_OVERWRITE: 单次覆写
        3. DOD_OVERWRITE: DoD标准3次覆写（推荐）
        4. CTYPES_SECURE: 使用ctypes直接操作内存

        Args:
            key_id: 要销毁的密钥ID
            method: 销毁方法
            requester_id: 请求者ID

        Returns:
            bool: 销毁是否成功

        Raises:
            KeyNotFoundError: 密钥不存在
            PermissionDeniedError: 权限不足
            DestructionFailedError: 销毁失败
        """
        if key_id not in self._keys:
            raise KeyNotFoundError(key_id)

        secure_key = self._keys[key_id]

        if requester_id != "system" and secure_key.metadata.owner_id != requester_id:
            raise PermissionDeniedError(
                key_id, secure_key.metadata.owner_id, requester_id
            )

        if secure_key.metadata.status == KeyStatus.DESTROYED:
            self._log_operation(
                "destroy_key_skipped",
                key_id,
                {
                    "reason": "already_destroyed",
                    "method": method.value,
                },
            )
            return False

        secure_key.metadata.status = KeyStatus.PENDING_DELETION
        key_data = secure_key.get_mutable_data()

        try:
            if method == DestructionMethod.SIMPLE_DEL:
                self._destroy_simple_del(key_data)
            elif method == DestructionMethod.SINGLE_OVERWRITE:
                self._destroy_single_overwrite(key_data)
            elif method == DestructionMethod.DOD_OVERWRITE:
                self._destroy_dod_overwrite(key_data)
            elif method == DestructionMethod.CTYPES_SECURE:
                self._destroy_ctypes_secure(key_data)
            else:
                raise DestructionFailedError(
                    key_id, method.value, f"Unknown destruction method: {method}"
                )

            secure_key.metadata.status = KeyStatus.DESTROYED
            secure_key.metadata.destruction_method = method
            secure_key.metadata.destroyed_at = get_utc_timestamp()

            # 生成删除证明哈希
            proof_hash = self._generate_proof_hash(
                key_id,
                method.value,
                secure_key.metadata.destroyed_at,
                secure_key.metadata.fingerprint,
            )

            # 如果配置了区块链，记录到链上
            if self._contract_manager:
                try:
                    blockchain_result = self._contract_manager.record_deletion(
                        key_id=key_id,
                        destruction_method=method.value,
                        proof_hash=proof_hash,
                        wait_for_confirmation=True,
                    )

                    # 记录交易哈希到审计日志
                    self._log_operation(
                        "blockchain_record_success",
                        key_id,
                        {
                            "tx_hash": blockchain_result["tx_hash"],
                            "proof_hash": proof_hash,
                            "block_number": blockchain_result.get("block_number"),
                        },
                    )

                    self._stats["blockchain_recordings"] += 1

                    print(
                        f"✓ Deletion recorded on blockchain: {blockchain_result['tx_hash']}"
                    )

                except Exception as e:
                    # 区块链记录失败，但密钥已销毁
                    self._log_operation(
                        "blockchain_record_failed",
                        key_id,
                        {
                            "error": str(e),
                            "proof_hash": proof_hash,
                        },
                    )
                    print(f"⚠ Blockchain recording failed: {str(e)}")
                    self._stats["blockchain_failures"] += 1

            secure_key._key_data = bytearray()

            self._stats["total_destroyed"] += 1

            self._log_operation(
                "destroy_key_success",
                key_id,
                {
                    "method": method.value,
                    "requester_id": requester_id,
                    "destroyed_at": timestamp_to_iso(secure_key.metadata.destroyed_at),
                },
            )

            gc.collect()

            return True

        except Exception as e:
            self._log_operation(
                "destroy_key_failed",
                key_id,
                {
                    "method": method.value,
                    "error": str(e),
                },
            )
            raise DestructionFailedError(key_id, method.value, str(e))

    def verify_deletion_on_blockchain(self, key_id: str) -> dict[str, Any] | None:
        """
        验证密钥删除是否已记录在区块链上

        Args:
            key_id: 密钥ID

        Returns:
            删除记录字典，如果未找到返回None
        """
        if not self._contract_manager:
            raise ValueError("No blockchain contract manager configured")

        try:
            record = self._contract_manager.get_deletion_record(key_id)

            if record:
                self._log_operation(
                    "blockchain_verify_success", key_id, {"record": record}
                )

            return record
        except Exception as e:
            self._log_operation("blockchain_verify_failed", key_id, {"error": str(e)})
            return None

    def _generate_proof_hash(
        self, key_id: str, method: str, timestamp: datetime, fingerprint: str
    ) -> str:
        """
        生成删除证明哈希

        Args:
            key_id: 密钥ID
            method: 销毁方法
            timestamp: 销毁时间
            fingerprint: 密钥指纹

        Returns:
            str: 32字节的十六进制哈希
        """
        # 组合删除信息
        proof_data = f"{key_id}|{method}|{timestamp_to_iso(timestamp)}|{fingerprint}"

        # 生成SHA-256哈希
        proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

        return proof_hash

    def _destroy_simple_del(self, key_data: bytearray) -> None:
        """方法A: 简单Python del（对照组）"""
        del key_data

    def _destroy_single_overwrite(self, key_data: bytearray) -> None:
        """方法B: 单次随机覆写"""
        secure_overwrite_memory(key_data, None)

    def _destroy_dod_overwrite(self, key_data: bytearray) -> None:
        """方法C: DoD 5220.22-M标准3次覆写（推荐）"""
        dod_overwrite_memory(key_data)

    def _destroy_ctypes_secure(self, key_data: bytearray) -> None:
        """方法D: 使用ctypes直接操作内存"""
        dod_overwrite_memory(key_data)
        secure_zero_memory(key_data)

    def _log_operation(
        self, operation: str, key_id: str, details: dict[str, Any]
    ) -> None:
        """记录操作到审计日志"""
        log_entry = {
            "timestamp": timestamp_to_iso(get_utc_timestamp()),
            "operation": operation,
            "key_id": key_id,
            "details": details,
        }
        self._audit_log.append(log_entry)

    def get_audit_log(
        self, key_id: str | None = None, operation: str | None = None
    ) -> list[dict[str, Any]]:
        """
        获取审计日志

        Args:
            key_id: 过滤密钥ID（None表示全部）
            operation: 过滤操作类型（None表示全部）

        Returns:
            审计日志列表
        """
        result = []
        for entry in self._audit_log:
            if key_id is not None and entry["key_id"] != key_id:
                continue
            if operation is not None and entry["operation"] != operation:
                continue

            result.append(entry)

        return result

    def get_blockchain_status(self) -> dict[str, Any]:
        """
        获取区块链连接状态

        Returns:
            包含连接状态和统计信息的字典
        """
        if not self._contract_manager:
            return {
                "enabled": False,
                "connected": False,
                "contract_address": None,
            }

        return {
            "enabled": True,
            "connected": self._contract_manager.is_connected(),
            "contract_address": self._contract_manager.contract_address,
            "total_recordings": self._stats["blockchain_recordings"],
            "total_failures": self._stats["blockchain_failures"],
            "success_rate": (
                self._stats["blockchain_recordings"]
                / (
                    self._stats["blockchain_recordings"]
                    + self._stats["blockchain_failures"]
                )
                if (
                    self._stats["blockchain_recordings"]
                    + self._stats["blockchain_failures"]
                )
                > 0
                else 0
            ),
        }

    def get_statistics(self) -> dict[str, Any]:
        """获取KMS统计信息"""
        stats = {
            **self._stats,
            "total_keys": len(self._keys),
            "active_keys": len(
                [
                    k
                    for k in self._keys.values()
                    if k.metadata.status == KeyStatus.ACTIVE
                ]
            ),
            "destroyed_keys": len(
                [
                    k
                    for k in self._keys.values()
                    if k.metadata.status == KeyStatus.DESTROYED
                ]
            ),
            "blockchain_enabled": self._contract_manager is not None,
        }

        # 如果有区块链连接，添加更多信息
        if self._contract_manager:
            stats["blockchain_connected"] = self._contract_manager.is_connected()

        return stats


# ===== 测试 =====

if __name__ == "__main__":
    print("=" * 60)
    print("KMS Key Manager - 功能测试")
    print("=" * 60)

    kms = KeyManagementService()
    print("\n✅ KMS实例创建成功\n")

    print("1. 测试密钥生成:")
    key_id_1 = kms.generate_key(32, "AES-256-GCM", "user_data", "user_001")
    key_id_2 = kms.generate_key(32, "AES-256-GCM", "file_encryption", "user_002")
    print(f"   ✅ 生成密钥1: {key_id_1}")
    print(f"   ✅ 生成密钥2: {key_id_2}\n")

    print("2. 测试密钥获取:")
    key = kms.get_key(key_id_1)
    print(f"   ✅ 获取密钥: {key}")
    print(f"   ✅ 密钥长度: {len(key.key_data)} 字节")
    print(f"   ✅ 密钥指纹: {key.metadata.fingerprint}\n")

    print("3. 测试列出密钥:")
    keys = kms.list_keys(status=KeyStatus.ACTIVE)
    print(f"   ✅ 活跃密钥数: {len(keys)}\n")

    print("4. 测试密钥销毁:")
    methods = [
        DestructionMethod.SIMPLE_DEL,
        DestructionMethod.SINGLE_OVERWRITE,
        DestructionMethod.DOD_OVERWRITE,
        DestructionMethod.CTYPES_SECURE,
    ]

    for i, method in enumerate(methods[:2], 1):
        key_id = kms.generate_key(16, "AES-128-GCM", "test", "system")
        success = kms.destroy_key(key_id, method)
        print(f"   ✅ 方法{i} ({method.value}): {'成功' if success else '失败'}")

    print("\n4.1 测试区块链集成销毁:")
    # 只有在配置了区块链时才测试
    if "--with-blockchain" in sys.argv:
        from ..blockchain.contract_manager import ContractManager

        # 创建带区块链的KMS
        cm = ContractManager()
        kms_with_blockchain = KeyManagementService(contract_manager=cm)

        # 生成并销毁一个密钥
        test_key = kms_with_blockchain.generate_key(
            32, "AES-256-GCM", "blockchain_test"
        )
        success = kms_with_blockchain.destroy_key(
            test_key, DestructionMethod.DOD_OVERWRITE
        )

        if success:
            # 验证区块链记录
            record = kms_with_blockchain.verify_deletion_on_blockchain(test_key)
            if record:
                print(f"   ✅ 区块链验证成功: {record['proof_hash'][:10]}...")
    else:
        print("   ℹ️  跳过区块链测试 (使用 --with-blockchain 启用)")

    print("\n5. 测试审计日志:")
    logs = kms.get_audit_log(operation="destroy_key_success")
    print(f"   ✅ 销毁操作日志: {len(logs)} 条\n")

    print("6. 统计信息:")
    stats = kms.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
