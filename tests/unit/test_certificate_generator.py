"""
删除证书生成器单元测试
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from src.crypto.certificate_generator import DeletionCertificateGenerator


@pytest.fixture
def temp_cert_dir(tmp_path):
    """临时证书目录"""
    return str(tmp_path / "test_certificates")


@pytest.fixture
def sample_deletion_result():
    """示例删除结果"""
    return {
        "success": True,
        "user_id": "test_user@example.com",
        "key_id": "user_test_user@example.com_dek",
        "method": "ctypes_secure",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "blockchain_tx": "0x123abc456def",
        "proof_hash": "0x789def456abc",
    }


def test_generate_certificate_basic(temp_cert_dir, sample_deletion_result):
    """测试基本证书生成"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    result = generator.generate_certificate(sample_deletion_result)

    # 验证返回值
    assert "certificate_id" in result
    assert "json_path" in result
    assert "json_data" in result

    # 验证证书ID格式
    cert_id = result["certificate_id"]
    assert cert_id.startswith("CERT-")
    assert len(cert_id.split("-")) == 3  # CERT-YYYYMMDD-XXXXXXXX

    # 验证文件已创建
    cert_path = Path(result["json_path"])
    assert cert_path.exists()

    # 验证JSON格式
    with open(cert_path, "r") as f:
        cert_data = json.load(f)

    assert "certificate" in cert_data
    assert cert_data["certificate"]["id"] == cert_id


def test_certificate_structure(temp_cert_dir, sample_deletion_result):
    """测试证书数据结构"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)
    result = generator.generate_certificate(sample_deletion_result)

    cert = result["json_data"]["certificate"]

    # 验证必需字段
    assert "id" in cert
    assert "version" in cert
    assert "issue_date" in cert
    assert "user" in cert
    assert "deletion_details" in cert
    assert "technical_details" in cert
    assert "metadata" in cert

    # 验证用户信息
    assert cert["user"]["user_id"] == sample_deletion_result["user_id"]
    assert "user_id_hash" in cert["user"]

    # 验证删除详情
    assert cert["deletion_details"]["key_id"] == sample_deletion_result["key_id"]
    assert (
        cert["deletion_details"]["deletion_method"] == sample_deletion_result["method"]
    )
    assert cert["deletion_details"]["verification_status"] == "CONFIRMED"


def test_certificate_with_blockchain(temp_cert_dir, sample_deletion_result):
    """测试包含区块链信息的证书"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)
    result = generator.generate_certificate(sample_deletion_result)

    cert = result["json_data"]["certificate"]

    # 应该包含区块链证明（即使没有详细信息）
    assert "blockchain_proof" in cert
    assert (
        cert["blockchain_proof"]["transaction_hash"]
        == sample_deletion_result["blockchain_tx"]
    )

    # 应该包含验证信息
    assert "verification" in cert
    assert "blockchain_explorer_url" in cert["verification"]


def test_certificate_without_blockchain(temp_cert_dir):
    """测试不包含区块链的证书"""
    deletion_result = {
        "success": True,
        "user_id": "test_user",
        "key_id": "user_test_user_dek",
        "method": "ctypes_secure",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        # 没有 blockchain_tx 和 proof_hash
    }

    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)
    result = generator.generate_certificate(deletion_result)

    cert = result["json_data"]["certificate"]

    # 不应该有完整的区块链证明
    if "blockchain_proof" in cert:
        pytest.fail("Should not have blockchain_proof without blockchain data")

    # 验证信息应该有提示
    assert "verification" in cert
    assert "note" in cert["verification"]


def test_missing_required_fields(temp_cert_dir):
    """测试缺少必需字段时的错误处理"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    # 缺少 user_id
    incomplete_result = {
        "success": True,
        "key_id": "test_key",
        "method": "ctypes_secure",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    with pytest.raises(ValueError, match="Missing required field"):
        generator.generate_certificate(incomplete_result)


def test_failed_deletion_certificate(temp_cert_dir, sample_deletion_result):
    """测试为失败的删除生成证书时的错误处理"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    sample_deletion_result["success"] = False

    with pytest.raises(
        ValueError, match="Cannot generate certificate for failed deletion"
    ):
        generator.generate_certificate(sample_deletion_result)


def test_certificate_id_uniqueness(temp_cert_dir):
    """测试同一用户的证书ID唯一性"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    user_id = "same_user@example.com"

    result1 = {
        "success": True,
        "user_id": user_id,
        "key_id": f"user_{user_id}_dek",
        "method": "ctypes_secure",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cert1 = generator.generate_certificate(result1)
    cert2 = generator.generate_certificate(result1)

    # 同一天同一用户的证书ID应该相同（会覆盖）
    assert cert1["certificate_id"] == cert2["certificate_id"]


def test_list_certificates(temp_cert_dir, sample_deletion_result):
    """测试列出证书功能"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    # 生成多个证书
    for i in range(3):
        result = sample_deletion_result.copy()
        result["user_id"] = f"user_{i}@example.com"
        result["key_id"] = f"user_user_{i}@example.com_dek"
        generator.generate_certificate(result)

    # 列出证书
    certificates = generator.list_certificates()

    assert len(certificates) == 3
    assert all(cert_id.startswith("CERT-") for cert_id in certificates)


def test_load_certificate(temp_cert_dir, sample_deletion_result):
    """测试加载证书功能"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    # 生成证书
    result = generator.generate_certificate(sample_deletion_result)
    cert_id = result["certificate_id"]

    # 加载证书
    loaded_cert = generator.load_certificate(cert_id)

    assert loaded_cert == result["json_data"]


def test_load_nonexistent_certificate(temp_cert_dir):
    """测试加载不存在的证书"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    with pytest.raises(FileNotFoundError):
        generator.load_certificate("CERT-20251021-NONEXIST")


def test_additional_data(temp_cert_dir, sample_deletion_result):
    """测试添加额外数据"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    additional_data = {
        "deletion_reason": "GDPR Article 17 Request",
        "requester_ip": "192.168.1.1",
        "notes": "User requested full data deletion",
    }

    result = generator.generate_certificate(
        sample_deletion_result, additional_data=additional_data
    )

    cert = result["json_data"]["certificate"]

    assert "additional_data" in cert
    assert cert["additional_data"] == additional_data


def test_user_id_hash_consistency(temp_cert_dir):
    """测试用户ID哈希的一致性"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)

    user_id = "test_user@example.com"
    hash1 = generator._hash_user_id(user_id)
    hash2 = generator._hash_user_id(user_id)

    # 同一用户ID的哈希应该一致
    assert hash1 == hash2
    assert hash1.startswith("sha256:")


def test_certificate_json_format(temp_cert_dir, sample_deletion_result):
    """测试证书JSON格式的正确性"""
    generator = DeletionCertificateGenerator(certificates_dir=temp_cert_dir)
    result = generator.generate_certificate(sample_deletion_result)

    # 读取文件并验证JSON格式
    cert_path = Path(result["json_path"])
    with open(cert_path, "r", encoding="utf-8") as f:
        content = f.read()
        cert_data = json.loads(content)  # 应该能正确解析

    # 验证缩进格式（应该是2空格）
    assert '  "certificate": {' in content

    # 验证UTF-8编码
    assert isinstance(content, str)
