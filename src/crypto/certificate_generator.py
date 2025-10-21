"""
删除证书生成器模块

生成可验证的删除证书，用于证明数据删除操作。
支持JSON格式，包含完整的删除信息和区块链证明。
"""

import json
import hashlib
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path


class DeletionCertificateGenerator:
    """
    删除证书生成器

    功能：
    - 生成JSON格式的删除证书
    - 包含用户信息、删除详情、区块链证明
    - 提供验证方法指引
    """

    def __init__(self, contract_manager=None, certificates_dir: str = "certificates"):
        """
        初始化证书生成器

        Args:
            contract_manager: ContractManager实例（用于获取区块链详情）
            certificates_dir: 证书存储目录
        """
        self.contract_manager = contract_manager
        self.certificates_dir = Path(certificates_dir)

        # 确保证书目录存在
        self.certificates_dir.mkdir(parents=True, exist_ok=True)

    def generate_certificate(
        self,
        deletion_result: Dict[str, Any],
        additional_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        生成删除证书

        Args:
            deletion_result: 删除结果（来自CryptoManager.delete_user_data()）
                必需字段：
                - user_id: 用户ID
                - key_id: 密钥ID
                - method: 销毁方法
                - timestamp: 删除时间戳
                - success: 是否成功
                可选字段：
                - blockchain_tx: 区块链交易哈希
                - proof_hash: 证明哈希
            additional_data: 额外数据（可选）

        Returns:
            dict: 证书信息
                - certificate_id: 证书ID
                - json_path: JSON文件路径
                - json_data: 证书数据

        Raises:
            ValueError: 如果缺少必需字段
        """
        # 1. 验证必需字段
        required_fields = ["user_id", "key_id", "method", "timestamp", "success"]
        for field in required_fields:
            if field not in deletion_result:
                raise ValueError(f"Missing required field: {field}")

        if not deletion_result["success"]:
            raise ValueError("Cannot generate certificate for failed deletion")

        # 2. 生成证书ID
        certificate_id = self._generate_certificate_id(deletion_result["user_id"])

        # 3. 获取区块链详细信息（如果有）
        blockchain_details = None
        if self.contract_manager and "blockchain_tx" in deletion_result:
            blockchain_details = self._fetch_blockchain_details(
                deletion_result["blockchain_tx"], deletion_result["key_id"]
            )

        # 4. 构建证书数据
        certificate_data = self._build_certificate_data(
            certificate_id=certificate_id,
            deletion_result=deletion_result,
            blockchain_details=blockchain_details,
            additional_data=additional_data,
        )

        # 5. 保存证书
        json_path = self._save_certificate(certificate_id, certificate_data)

        return {
            "certificate_id": certificate_id,
            "json_path": str(json_path),
            "json_data": certificate_data,
        }

    def _generate_certificate_id(self, user_id: str) -> str:
        """
        生成唯一的证书ID

        格式：CERT-YYYYMMDD-XXXXXXXX
        - YYYYMMDD: 日期
        - XXXXXXXX: 用户ID哈希的前8位（大写）

        Args:
            user_id: 用户ID

        Returns:
            str: 证书ID
        """
        # 当前日期
        date_str = datetime.utcnow().strftime("%Y%m%d")

        # 用户ID哈希（前8位）
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8].upper()

        return f"CERT-{date_str}-{user_hash}"

    def _fetch_blockchain_details(
        self, tx_hash: str, key_id: str
    ) -> Dict[str, Any] | None:
        """
        从区块链获取详细信息

        Args:
            tx_hash: 交易哈希
            key_id: 密钥ID

        Returns:
            dict: 区块链详情，如果获取失败返回None
        """
        if not self.contract_manager:
            return None

        try:
            # 获取交易收据
            receipt = self.contract_manager.get_transaction_receipt(tx_hash)

            # 获取删除记录
            record = self.contract_manager.get_deletion_record(key_id)

            if receipt and record:
                return {
                    "transaction_hash": tx_hash,
                    "block_number": receipt.get("blockNumber"),
                    "gas_used": receipt.get("gasUsed"),
                    "timestamp": record.get("timestamp"),
                    "timestamp_readable": record.get("timestamp_readable"),
                    "operator": record.get("operator"),
                    "proof_hash": record.get("proof_hash"),
                }
        except Exception as e:
            # 如果获取失败，返回None（使用deletion_result中的基本信息）
            print(f"Warning: Failed to fetch blockchain details: {e}")

        return None

    def _build_certificate_data(
        self,
        certificate_id: str,
        deletion_result: Dict[str, Any],
        blockchain_details: Dict[str, Any] | None,
        additional_data: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """
        构建证书数据结构

        Args:
            certificate_id: 证书ID
            deletion_result: 删除结果
            blockchain_details: 区块链详情
            additional_data: 额外数据

        Returns:
            dict: 完整的证书数据
        """
        now = datetime.utcnow().isoformat() + "Z"
        user_id = deletion_result["user_id"]

        # 基础证书结构
        certificate = {
            "certificate": {
                "id": certificate_id,
                "version": "1.0",
                "issue_date": now,
                "user": {
                    "user_id": user_id,
                    "user_id_hash": self._hash_user_id(user_id),
                    "deletion_request_time": deletion_result["timestamp"],
                },
                "deletion_details": {
                    "key_id": deletion_result["key_id"],
                    "deletion_method": deletion_result["method"],
                    "deletion_timestamp": deletion_result["timestamp"],
                    "verification_status": (
                        "CONFIRMED" if deletion_result["success"] else "FAILED"
                    ),
                },
                "technical_details": {
                    "encryption_algorithm": "AES-256-GCM",
                    "key_size_bits": 256,
                    "destruction_method": deletion_result["method"],
                },
            }
        }

        # 添加区块链证明（如果有）
        if blockchain_details:
            certificate["certificate"]["blockchain_proof"] = {
                "network": "ethereum_sepolia",
                "chain_id": 11155111,
                "transaction_hash": blockchain_details["transaction_hash"],
                "block_number": blockchain_details.get("block_number"),
                "gas_used": blockchain_details.get("gas_used"),
                "timestamp": blockchain_details.get("timestamp"),
                "timestamp_readable": blockchain_details.get("timestamp_readable"),
                "operator": blockchain_details.get("operator"),
                "proof_hash": blockchain_details.get("proof_hash"),
            }

            # 添加验证信息
            tx_hash = blockchain_details["transaction_hash"]
            certificate["certificate"]["verification"] = {
                "blockchain_explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}",
                "verification_tool_command": f"python tools/verify_deletion.py {certificate_id}.json",
                "contract_address": (
                    self.contract_manager.contract_address
                    if self.contract_manager
                    else None
                ),
            }
        elif "blockchain_tx" in deletion_result:
            # 如果有交易哈希但获取详情失败，使用基本信息
            tx_hash = deletion_result["blockchain_tx"]
            certificate["certificate"]["blockchain_proof"] = {
                "network": "ethereum_sepolia",
                "transaction_hash": tx_hash,
                "proof_hash": deletion_result.get("proof_hash"),
            }

            certificate["certificate"]["verification"] = {
                "blockchain_explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}",
                "verification_tool_command": f"python tools/verify_deletion.py {certificate_id}.json",
                "note": "Detailed blockchain information will be available after confirmation",
            }
        else:
            # 没有区块链证明
            certificate["certificate"]["verification"] = {
                "note": "This deletion was not recorded on blockchain"
            }

        # 添加额外数据（如果有）
        if additional_data:
            certificate["certificate"]["additional_data"] = additional_data

        # 添加元数据
        certificate["certificate"]["metadata"] = {
            "system_version": "1.0.0",
            "certificate_schema_version": "1.0",
            "issuer": "Verifiable Deletion Protocol System",
            "certificate_type": "DELETION_PROOF",
            "validity": "PERMANENT",
        }

        return certificate

    def _save_certificate(
        self, certificate_id: str, certificate_data: Dict[str, Any]
    ) -> Path:
        """
        保存证书到文件

        Args:
            certificate_id: 证书ID
            certificate_data: 证书数据

        Returns:
            Path: 保存的文件路径
        """
        filename = f"{certificate_id}.json"
        filepath = self.certificates_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(certificate_data, f, indent=2, ensure_ascii=False)

        return filepath

    def _hash_user_id(self, user_id: str) -> str:
        """
        哈希用户ID以保护隐私

        Args:
            user_id: 用户ID

        Returns:
            str: 哈希值（格式：sha256:...）
        """
        hash_value = hashlib.sha256(user_id.encode()).hexdigest()
        return f"sha256:{hash_value}"

    def load_certificate(self, certificate_id: str) -> Dict[str, Any]:
        """
        加载证书

        Args:
            certificate_id: 证书ID

        Returns:
            dict: 证书数据

        Raises:
            FileNotFoundError: 证书文件不存在
        """
        filename = f"{certificate_id}.json"
        filepath = self.certificates_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Certificate not found: {certificate_id}")

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_certificates(self) -> list[str]:
        """
        列出所有证书

        Returns:
            list[str]: 证书ID列表
        """
        certificates = []
        for filepath in self.certificates_dir.glob("CERT-*.json"):
            certificate_id = filepath.stem  # 文件名（不含扩展名）
            certificates.append(certificate_id)

        return sorted(certificates, reverse=True)  # 按日期倒序


# ===== 便捷函数 =====


def generate_deletion_certificate(
    deletion_result: Dict[str, Any],
    contract_manager=None,
    certificates_dir: str = "certificates",
) -> Dict[str, Any]:
    """
    便捷函数：生成删除证书

    Args:
        deletion_result: 删除结果
        contract_manager: ContractManager实例（可选）
        certificates_dir: 证书目录

    Returns:
        dict: 证书信息
    """
    generator = DeletionCertificateGenerator(
        contract_manager=contract_manager, certificates_dir=certificates_dir
    )

    return generator.generate_certificate(deletion_result)


# ===== 示例 =====

if __name__ == "__main__":
    """测试证书生成器"""

    print("=" * 60)
    print("删除证书生成器测试")
    print("=" * 60)

    # 模拟删除结果
    deletion_result = {
        "success": True,
        "user_id": "alice@example.com",
        "key_id": "user_alice@example.com_dek",
        "method": "ctypes_secure",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "blockchain_tx": "0x123abc456def789",
        "proof_hash": "0x789def456abc123",
    }

    # 生成证书
    print("\n1. 生成删除证书...")
    generator = DeletionCertificateGenerator()
    result = generator.generate_certificate(deletion_result)

    print(f"   ✓ 证书已生成")
    print(f"   证书ID: {result['certificate_id']}")
    print(f"   保存路径: {result['json_path']}")

    # 查看证书内容
    print("\n2. 证书内容预览...")
    cert_data = result["json_data"]
    print(f"   版本: {cert_data['certificate']['version']}")
    print(f"   发布日期: {cert_data['certificate']['issue_date']}")
    print(f"   用户: {cert_data['certificate']['user']['user_id']}")
    print(
        f"   删除方法: {cert_data['certificate']['deletion_details']['deletion_method']}"
    )

    if "blockchain_proof" in cert_data["certificate"]:
        print(
            f"   区块链交易: {cert_data['certificate']['blockchain_proof']['transaction_hash']}"
        )

    # 列出所有证书
    print("\n3. 列出所有证书...")
    certificates = generator.list_certificates()
    print(f"   共 {len(certificates)} 个证书:")
    for cert_id in certificates[:5]:  # 只显示前5个
        print(f"   - {cert_id}")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
