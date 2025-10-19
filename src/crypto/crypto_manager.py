"""
数据加密管理器模块

提供用户数据的加密/解密功能，集成KMS进行密钥管理。
使用AES-256-GCM模式提供认证加密。

设计原则：
- 每个用户一个独立的数据加密密钥（DEK）
- DEK由KMS管理
- 支持密钥轮换
- 提供完整的加密元数据
"""

import json
from typing import Any
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os


class EncryptionMetadata:
    """加密元数据"""

    def __init__(
        self,
        key_id: str,
        algorithm: str,
        nonce: bytes,
        encrypted_at: datetime | None = None,
    ):
        self.key_id = key_id
        self.algorithm = algorithm
        self.nonce = nonce
        self.encrypted_at = encrypted_at or datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "nonce": self.nonce.hex(),
            "encrypted_at": self.encrypted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EncryptionMetadata":
        """从字典创建"""
        return cls(
            key_id=data["key_id"],
            algorithm=data["algorithm"],
            nonce=bytes.fromhex(data["nonce"]),
            encrypted_at=datetime.fromisoformat(data["encrypted_at"]),
        )


class CryptoManager:
    """
    数据加密管理器

    负责：
    1. 用户数据的加密/解密
    2. 与KMS集成管理密钥
    3. 加密元数据管理
    """

    def __init__(self, kms):
        """
        初始化加密管理器

        Args:
            kms: KeyManagementService实例
        """
        self.kms = kms
        self.algorithm = "AES-256-GCM"

    def encrypt_user_data(
        self,
        user_id: str,
        data: str | bytes,
        associated_data: str | None = None,
    ) -> tuple[bytes, EncryptionMetadata]:
        """
        加密用户数据

        Args:
            user_id: 用户ID
            data: 要加密的数据（字符串或字节）
            associated_data: 关联数据（用于AEAD认证，如用户ID）

        Returns:
            tuple[bytes, EncryptionMetadata]: (密文, 加密元数据)

        流程：
        1. 从KMS获取用户的数据加密密钥（DEK）
        2. 如果不存在，生成新密钥
        3. 使用AES-GCM加密数据
        4. 返回密文和元数据
        """
        # 1. 准备数据
        if isinstance(data, str):
            plaintext = data.encode("utf-8")
        else:
            plaintext = data

        # 2. 获取或生成用户的DEK
        key_id = f"user_{user_id}_dek"

        try:
            secure_key = self.kms.get_key(key_id)
            key_bytes = secure_key.key_data
        except Exception:
            # 密钥不存在，生成新密钥
            from src.kms.key_manager import SecureKey, KeyMetadata, KeyStatus
            from src.kms.utils import (
                generate_random_bytes,
                get_utc_timestamp,
                compute_key_fingerprint,
            )

            # 直接创建密钥，绕过 generate_key 的自动ID生成
            key_data = generate_random_bytes(32)

            metadata = KeyMetadata(
                key_id=key_id,
                created_at=get_utc_timestamp(),
                status=KeyStatus.ACTIVE,
                algorithm=self.algorithm,
                key_size=32,
                purpose="user_data_encryption",
                owner_id=user_id,
            )

            secure_key = SecureKey(key_data, metadata)
            self.kms._keys[key_id] = secure_key
            self.kms._stats["total_generated"] += 1

            # 记录审计日志
            self.kms._log_operation(
                "generate_key",
                key_id,
                {
                    "algorithm": self.algorithm,
                    "key_size": 32,
                    "purpose": "user_data_encryption",
                    "owner_id": user_id,
                    "fingerprint": secure_key.metadata.fingerprint,
                    "source": "crypto_manager",
                },
            )
            key_bytes = secure_key.key_data

        # 3. 生成随机nonce（96位，GCM推荐）
        nonce = os.urandom(12)

        # 4. 准备关联数据
        aad = None
        if associated_data:
            aad = (
                associated_data.encode("utf-8")
                if isinstance(associated_data, str)
                else associated_data
            )

        # 5. 使用AES-GCM加密
        aesgcm = AESGCM(key_bytes)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

        # 6. 创建元数据
        metadata = EncryptionMetadata(
            key_id=key_id,
            algorithm=self.algorithm,
            nonce=nonce,
        )

        return ciphertext, metadata

    def decrypt_user_data(
        self,
        ciphertext: bytes,
        metadata: EncryptionMetadata,
        associated_data: str | None = None,
    ) -> bytes:
        """
        解密用户数据

        Args:
            ciphertext: 密文
            metadata: 加密元数据
            associated_data: 关联数据（必须与加密时相同）

        Returns:
            bytes: 明文数据

        Raises:
            KeyDestroyedError: 密钥已被销毁
            DecryptionError: 解密失败
        """
        # 1. 从KMS获取密钥
        secure_key = self.kms.get_key(metadata.key_id)
        key_bytes = secure_key.key_data

        # 2. 准备关联数据
        aad = None
        if associated_data:
            aad = (
                associated_data.encode("utf-8")
                if isinstance(associated_data, str)
                else associated_data
            )

        # 3. 解密
        try:
            aesgcm = AESGCM(key_bytes)
            plaintext = aesgcm.decrypt(metadata.nonce, ciphertext, aad)
            return plaintext
        except Exception as e:
            raise DecryptionError(f"解密失败: {str(e)}")

    def delete_user_data(
        self,
        user_id: str,
        destruction_method,
    ) -> dict[str, Any]:
        """
        删除用户数据（销毁加密密钥）⭐ 核心方法

        这是整个协议的关键：通过销毁密钥使加密数据永久不可恢复

        Args:
            user_id: 用户ID
            destruction_method: 密钥销毁方法

        Returns:
            dict: 删除结果
                - success: 是否成功
                - key_id: 密钥ID
                - method: 销毁方法
                - blockchain_tx: 区块链交易哈希（如果有）
                - timestamp: 删除时间
        """
        key_id = f"user_{user_id}_dek"

        # 销毁密钥（会自动记录到区块链）
        success = self.kms.destroy_key(key_id, destruction_method)

        # 获取删除详情
        result = {
            "success": success,
            "key_id": key_id,
            "user_id": user_id,
            "method": destruction_method.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 如果有区块链，获取交易信息
        if self.kms._contract_manager:
            # 从审计日志获取区块链交易哈希
            logs = self.kms.get_audit_log(
                key_id=key_id, operation="blockchain_record_success"
            )
            if logs:
                latest_log = logs[-1]
                result["blockchain_tx"] = latest_log["details"]["tx_hash"]
                result["proof_hash"] = latest_log["details"]["proof_hash"]

        return result

    def verify_deletion(self, user_id: str) -> dict[str, Any]:
        """
        验证用户数据删除状态

        Args:
            user_id: 用户ID

        Returns:
            dict: 验证结果
                - deleted: 是否已删除
                - key_status: 密钥状态
                - blockchain_verified: 区块链验证结果
        """
        key_id = f"user_{user_id}_dek"

        result: dict[str, Any] = {
            "user_id": user_id,
            "key_id": key_id,
        }

        # 1. 检查KMS中的密钥状态
        try:
            secure_key = self.kms._keys.get(key_id)
            if secure_key:
                from src.kms.key_manager import KeyStatus

                result["deleted"] = secure_key.metadata.status == KeyStatus.DESTROYED
                result["key_status"] = secure_key.metadata.status.value
                result["destruction_method"] = (
                    secure_key.metadata.destruction_method.value
                    if secure_key.metadata.destruction_method
                    else None
                )
                result["destroyed_at"] = (
                    secure_key.metadata.destroyed_at.isoformat()
                    if secure_key.metadata.destroyed_at
                    else None
                )
            else:
                result["deleted"] = False
                result["key_status"] = "not_found"
        except Exception as e:
            result["error"] = str(e)

        # 2. 从区块链验证（如果有）
        if self.kms._contract_manager:
            try:
                record = self.kms.verify_deletion_on_blockchain(key_id)
                result["blockchain_verified"] = record is not None
                if record:
                    result["blockchain_record"] = {
                        "timestamp": record["timestamp_readable"],
                        "operator": record["operator"],
                        "proof_hash": record["proof_hash"],
                    }
            except Exception as e:
                result["blockchain_error"] = str(e)

        return result


class DecryptionError(Exception):
    """解密错误"""

    pass


# ===== 简单示例 =====

if __name__ == "__main__":
    """测试加密管理器"""
    from src.kms.key_manager import KeyManagementService, DestructionMethod

    print("=" * 60)
    print("数据加密管理器测试")
    print("=" * 60)

    # 1. 创建KMS和CryptoManager
    kms = KeyManagementService()
    crypto = CryptoManager(kms)

    # 2. 加密用户数据
    print("\n1. 加密用户数据...")
    user_id = "user_001"
    sensitive_data = "这是用户的敏感个人信息：身份证号123456789"

    ciphertext, metadata = crypto.encrypt_user_data(
        user_id=user_id,
        data=sensitive_data,
        associated_data=user_id,  # 使用用户ID作为关联数据
    )

    print(f"   ✓ 数据已加密")
    print(f"   密钥ID: {metadata.key_id}")
    print(f"   密文长度: {len(ciphertext)} 字节")
    print(f"   Nonce: {metadata.nonce.hex()[:16]}...")

    # 3. 解密数据
    print("\n2. 解密数据...")
    plaintext = crypto.decrypt_user_data(
        ciphertext=ciphertext,
        metadata=metadata,
        associated_data=user_id,
    )

    print(f"   ✓ 数据已解密: {plaintext.decode('utf-8')}")

    # 4. 删除用户数据（销毁密钥）
    print("\n3. 删除用户数据（销毁密钥）...")
    result = crypto.delete_user_data(user_id, DestructionMethod.DOD_OVERWRITE)

    print(f"   ✓ 删除成功: {result['success']}")
    print(f"   销毁方法: {result['method']}")
    print(f"   时间戳: {result['timestamp']}")

    # 5. 验证删除
    print("\n4. 验证删除状态...")
    verification = crypto.verify_deletion(user_id)

    print(f"   ✓ 已删除: {verification['deleted']}")
    print(f"   密钥状态: {verification['key_status']}")

    # 6. 尝试解密（应该失败）
    print("\n5. 尝试解密已删除用户的数据...")
    try:
        crypto.decrypt_user_data(ciphertext, metadata, user_id)
        print("   ❌ 错误：不应该能解密！")
    except Exception as e:
        print(f"   ✓ 正确：无法解密（{type(e).__name__}）")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
