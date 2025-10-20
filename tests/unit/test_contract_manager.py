"""
ContractManager 单元测试

测试合约管理器的各项功能，包括：
- 配置验证
- 连接管理
- 交易发送
- 数据查询
"""

import pytest
import hashlib
import time
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3

# 假设项目结构允许这样导入
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.blockchain import (
    BlockchainConfig,
    ContractManager,
    ConnectionError,
    TransactionError,
)


class TestBlockchainConfig:
    """测试配置类"""

    def test_config_validation_with_valid_env(self):
        """测试有效配置的验证"""
        # 这个测试需要有效的环境变量
        is_valid, errors = BlockchainConfig.validate_config()

        # 如果环境变量配置正确，应该通过
        if is_valid:
            assert len(errors) == 0
        else:
            # 如果失败，至少应该有错误信息
            assert len(errors) > 0

    def test_get_rpc_url(self):
        """测试 RPC URL 生成"""
        if BlockchainConfig.INFURA_PROJECT_ID:
            url = BlockchainConfig.get_rpc_url()
            assert "sepolia.infura.io" in url
            assert BlockchainConfig.INFURA_PROJECT_ID in url

    def test_load_contract_abi(self):
        """测试 ABI 加载"""
        try:
            abi = BlockchainConfig.load_contract_abi()
            assert isinstance(abi, list)
            assert len(abi) > 0
            # 检查是否包含关键函数
            function_names = [
                item.get("name") for item in abi if item.get("type") == "function"
            ]
            assert "recordDeletion" in function_names
            assert "getDeletionRecord" in function_names
        except FileNotFoundError:
            pytest.skip("Contract ABI not compiled yet")


class TestContractManager:
    """测试合约管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例（用于需要真实连接的测试）"""
        try:
            manager = ContractManager(auto_connect=True)
            yield manager
            manager.disconnect()
        except ConnectionError:
            pytest.skip("Cannot connect to blockchain (check .env configuration)")

    def test_initialization_without_auto_connect(self):
        """测试不自动连接的初始化"""
        manager = ContractManager(auto_connect=False)
        assert manager.w3 is None
        assert manager.contract is None
        assert not manager.is_connected()

    def test_connection(self, manager):
        """测试连接功能"""
        assert manager.is_connected()
        assert manager.w3 is not None
        assert manager.contract is not None
        assert manager.account is not None

    def test_get_balance(self, manager):
        """测试获取余额"""
        balance = manager.get_balance()
        assert isinstance(balance, float)
        assert balance >= 0

    def test_record_deletion_integration(self, manager):
        """集成测试：记录删除操作"""
        # 生成唯一的测试数据
        key_id = f"unittest_key_{int(time.time())}"
        method = "ctypes_secure"
        proof_data = f"{key_id}:{method}:{time.time()}"
        proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

        # 记录删除
        result = manager.record_deletion(
            key_id=key_id,
            destruction_method=method,
            proof_hash=proof_hash,
            wait_for_confirmation=True,
        )

        # 验证结果
        assert "tx_hash" in result
        assert result["status"] in ["success", "pending"]
        assert len(result["tx_hash"]) in [
            64,
            66,
        ], f"Unexpected tx_hash length: {len(result['tx_hash'])}"

        # 等待确认
        if result["status"] == "pending":
            time.sleep(5)

        # 验证记录存在
        is_deleted = manager.is_key_deleted(key_id)
        assert is_deleted is True

        # 查询完整记录
        record = manager.get_deletion_record(key_id)
        assert record is not None
        assert record["key_id"] == key_id
        assert record["destruction_method"] == method
        assert record["exists"] is True

    def test_query_nonexistent_record(self, manager):
        """测试查询不存在的记录"""
        fake_key_id = f"nonexistent_key_{int(time.time())}"
        record = manager.get_deletion_record(fake_key_id)
        assert record is None

    def test_is_key_deleted_false(self, manager):
        """测试未删除的密钥"""
        fake_key_id = f"never_deleted_{int(time.time())}"
        is_deleted = manager.is_key_deleted(fake_key_id)
        assert is_deleted is False

    def test_verify_deletion_proof_valid(self, manager):
        """测试验证有效的删除证明"""
        # 先创建一个删除记录
        key_id = f"verify_test_{int(time.time())}"
        method = "dod_overwrite"
        proof_data = f"{key_id}:{method}:{time.time()}"
        proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

        # 记录删除
        manager.record_deletion(key_id, method, proof_hash, wait_for_confirmation=True)
        time.sleep(3)

        # 验证正确的证明
        is_valid = manager.verify_deletion_proof(key_id, method, proof_hash)
        assert is_valid is True

        # 验证错误的证明
        fake_proof = hashlib.sha256(b"fake").hexdigest()
        is_invalid = manager.verify_deletion_proof(key_id, method, fake_proof)
        assert is_invalid is False

    def test_context_manager(self):
        """测试上下文管理器"""
        try:
            with ContractManager() as manager:
                assert manager.is_connected()
                balance = manager.get_balance()
                assert isinstance(balance, float)

            # 退出后应该断开连接
            assert not manager.is_connected()
        except ConnectionError:
            pytest.skip("Cannot connect to blockchain")

    def test_batch_record_deletion(self, manager):
        """测试批量记录删除"""
        # 生成多个测试数据
        deletions = []
        for i in range(3):
            key_id = f"batch_unittest_{int(time.time())}_{i}"
            method = "single_overwrite"
            proof_data = f"{key_id}:{method}:{time.time()}"
            proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

            deletions.append(
                {
                    "key_id": key_id,
                    "destruction_method": method,
                    "proof_hash": proof_hash,
                }
            )

        # 批量记录
        result = manager.batch_record_deletion(deletions, wait_for_confirmation=True)

        assert "tx_hash" in result
        assert result["count"] == 3
        assert result["status"] in ["success", "pending"]

        # 等待确认
        time.sleep(5)

        # 验证每个记录
        for deletion in deletions:
            is_deleted = manager.is_key_deleted(deletion["key_id"])
            assert is_deleted is True


class TestErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def manager(self):
        """为错误处理测试提供ContractManager实例"""
        from src.blockchain.contract_manager import ContractManager

        return ContractManager()

    def test_connection_without_config(self):
        """测试缺少配置时的连接"""
        with patch.object(BlockchainConfig, "INFURA_PROJECT_ID", None):
            with pytest.raises(ValueError):
                BlockchainConfig.get_rpc_url()

    def test_record_deletion_without_connection(self):
        """测试未连接时记录删除"""
        manager = ContractManager(auto_connect=False)

        with pytest.raises(ConnectionError):
            manager.record_deletion("key", "method", "hash")

    def test_invalid_proof_hash_format(self, manager):
        """测试无效的证明哈希格式"""
        # 这应该能够处理或抛出适当的异常
        try:
            result = manager.record_deletion(
                key_id="test",
                destruction_method="method",
                proof_hash="invalid_hash",  # 无效格式
                wait_for_confirmation=False,
            )
            # 如果没有抛出异常，至少应该是有效的交易
            assert "tx_hash" in result
        except (TransactionError, ValueError):
            # 预期的异常
            pass


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.mark.skip(reason="需要真实的区块链连接，慎重运行")
    def test_quick_record_deletion(self):
        """测试快速记录删除函数"""
        from src.blockchain import quick_record_deletion

        key_id = f"quick_test_{int(time.time())}"
        method = "ctypes_secure"
        proof_hash = hashlib.sha256(f"{key_id}:{method}".encode()).hexdigest()

        tx_hash = quick_record_deletion(key_id, method, proof_hash)
        assert isinstance(tx_hash, str)
        assert len(tx_hash) == 66

    @pytest.mark.skip(reason="需要真实的区块链连接，慎重运行")
    def test_quick_check_deletion(self):
        """测试快速检查删除函数"""
        from src.blockchain import quick_check_deletion

        # 检查不存在的密钥
        is_deleted = quick_check_deletion(f"nonexistent_{time.time()}")
        assert is_deleted is False


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
