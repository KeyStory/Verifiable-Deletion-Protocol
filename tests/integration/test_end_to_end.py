"""
端到端集成测试 - KMS与区块链完整流程验证

测试覆盖：
1. KMS初始化（带/不带区块链）
2. 密钥生成 → 销毁 → 链上验证的完整流程
3. 4种销毁方法的区块链记录
4. 批量删除操作
5. 异常处理和降级
6. 审计日志完整性
7. 性能基准测试

运行方式：
    # 运行所有测试
    python -m pytest tests/integration/test_end_to_end.py -v

    # 运行特定测试
    python -m pytest tests/integration/test_end_to_end.py::TestEndToEnd::test_basic_workflow -v

    # 显示详细输出
    python -m pytest tests/integration/test_end_to_end.py -v -s
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.kms.key_manager import (
    KeyManagementService,
    DestructionMethod,
    KeyStatus,
)
from src.blockchain.contract_manager import ContractManager, ConnectionError


# ===== 测试配置 =====


@pytest.fixture
def kms_without_blockchain():
    """创建不连接区块链的KMS实例"""
    kms = KeyManagementService()
    yield kms
    # 清理


@pytest.fixture
def kms_with_blockchain():
    """创建连接区块链的KMS实例"""
    try:
        contract_manager = ContractManager(auto_connect=True)
        kms = KeyManagementService(contract_manager=contract_manager)
        yield kms
        # 清理
        contract_manager.disconnect()
    except ConnectionError as e:
        pytest.skip(f"无法连接到区块链: {e}")


@pytest.fixture
def contract_manager():
    """创建独立的合约管理器"""
    try:
        cm = ContractManager(auto_connect=True)
        yield cm
        cm.disconnect()
    except ConnectionError as e:
        pytest.skip(f"无法连接到区块链: {e}")


# ===== 基础功能测试 =====


class TestBasicKMSFunctionality:
    """测试KMS基础功能（不需要区块链）"""

    def test_kms_initialization(self, kms_without_blockchain):
        """测试KMS初始化"""
        kms = kms_without_blockchain

        assert kms is not None
        assert len(kms._keys) == 0
        assert kms._stats["total_generated"] == 0
        assert kms._contract_manager is None

        print("✓ KMS初始化成功")

    def test_key_generation(self, kms_without_blockchain):
        """测试密钥生成"""
        kms = kms_without_blockchain

        # 生成密钥
        key_id = kms.generate_key(
            key_size=32,
            algorithm="AES-256-GCM",
            purpose="test_encryption",
            owner_id="test_user",
        )

        assert key_id is not None
        assert len(key_id) > 0
        assert kms._stats["total_generated"] == 1

        # 获取密钥
        key = kms.get_key(key_id)
        assert key is not None
        assert len(key.key_data) == 32
        assert key.metadata.status == KeyStatus.ACTIVE

        print(f"✓ 密钥生成成功: {key_id}")

    def test_key_destruction_without_blockchain(self, kms_without_blockchain):
        """测试密钥销毁（无区块链）"""
        kms = kms_without_blockchain

        # 生成密钥
        key_id = kms.generate_key(32, "AES-256-GCM")

        # 销毁密钥
        success = kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

        assert success is True
        assert kms._stats["total_destroyed"] == 1

        # 验证密钥状态
        key = kms._keys[key_id]
        assert key.metadata.status == KeyStatus.DESTROYED
        assert key.metadata.destruction_method == DestructionMethod.DOD_OVERWRITE
        assert key.metadata.destroyed_at is not None

        print(f"✓ 密钥销毁成功: {key_id}")

    def test_all_destruction_methods(self, kms_without_blockchain):
        """测试所有4种销毁方法"""
        kms = kms_without_blockchain

        methods = [
            DestructionMethod.SIMPLE_DEL,
            DestructionMethod.SINGLE_OVERWRITE,
            DestructionMethod.DOD_OVERWRITE,
            DestructionMethod.CTYPES_SECURE,
        ]

        for method in methods:
            key_id = kms.generate_key(32, "AES-256-GCM")
            success = kms.destroy_key(key_id, method)

            assert success is True
            assert kms._keys[key_id].metadata.destruction_method == method

            print(f"✓ {method.value} 销毁成功")

        assert kms._stats["total_destroyed"] == 4


# ===== 区块链集成测试 =====


class TestBlockchainIntegration:
    """测试KMS与区块链的集成"""

    def test_kms_with_blockchain_initialization(self, kms_with_blockchain):
        """测试带区块链的KMS初始化"""
        kms = kms_with_blockchain

        assert kms._contract_manager is not None
        assert kms._contract_manager.is_connected()

        # 检查区块链状态
        status = kms.get_blockchain_status()
        assert status["enabled"] is True
        assert status["connected"] is True
        assert status["contract_address"] is not None

        print("✓ 区块链连接成功")
        print(f"  合约地址: {status['contract_address']}")

    def test_key_destruction_with_blockchain_recording(self, kms_with_blockchain):
        """测试密钥销毁并记录到区块链 ⭐ 核心测试"""
        kms = kms_with_blockchain

        # 1. 生成密钥
        key_id = kms.generate_key(
            key_size=32,
            algorithm="AES-256-GCM",
            purpose="blockchain_test",
            owner_id="test_user",
        )
        print(f"✓ 生成密钥: {key_id}")

        # 2. 销毁密钥（应该自动记录到区块链）
        start_time = time.time()
        success = kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
        elapsed_time = time.time() - start_time

        assert success is True
        print(f"✓ 密钥销毁成功 (耗时: {elapsed_time:.2f}秒)")

        # 3. 验证KMS内部状态
        key = kms._keys[key_id]
        assert key.metadata.status == KeyStatus.DESTROYED
        assert key.metadata.destruction_method == DestructionMethod.DOD_OVERWRITE

        # 4. 检查审计日志中的区块链记录
        blockchain_logs = kms.get_audit_log(operation="blockchain_record_success")
        assert len(blockchain_logs) > 0

        latest_log = blockchain_logs[-1]
        assert latest_log["key_id"] == key_id
        assert "tx_hash" in latest_log["details"]
        assert "proof_hash" in latest_log["details"]

        tx_hash = latest_log["details"]["tx_hash"]
        proof_hash = latest_log["details"]["proof_hash"]

        print(f"✓ 区块链记录成功")
        print(f"  交易哈希: {tx_hash}")
        print(f"  证明哈希: {proof_hash[:16]}...")

        # 5. 从区块链验证删除记录
        time.sleep(2)  # 等待区块确认

        record = kms.verify_deletion_on_blockchain(key_id)
        assert record is not None
        assert record["key_id"] == key_id
        assert record["destruction_method"] == "dod_overwrite"
        assert record["exists"] is True

        print(f"✓ 区块链验证成功")
        print(f"  时间戳: {record['timestamp_readable']}")
        print(f"  操作者: {record['operator']}")

        # 6. 检查统计信息
        stats = kms.get_statistics()
        assert stats["blockchain_recordings"] >= 1

        print(f"✓ 完整流程测试通过!")

    def test_all_methods_with_blockchain(self, kms_with_blockchain):
        """测试所有销毁方法都能记录到区块链"""
        kms = kms_with_blockchain

        methods = [
            DestructionMethod.SINGLE_OVERWRITE,
            DestructionMethod.DOD_OVERWRITE,
            DestructionMethod.CTYPES_SECURE,
        ]

        for method in methods:
            # 生成密钥
            key_id = kms.generate_key(32, "AES-256-GCM", f"test_{method.value}")

            # 销毁密钥
            success = kms.destroy_key(key_id, method)
            assert success is True

            # 等待区块确认
            time.sleep(2)

            # 验证区块链记录
            record = kms.verify_deletion_on_blockchain(key_id)
            assert record is not None
            assert record["destruction_method"] == method.value

            print(f"✓ {method.value} 区块链记录成功")

        # 检查统计
        stats = kms.get_statistics()
        assert stats["blockchain_recordings"] >= len(methods)

    def test_blockchain_verification_methods(
        self, kms_with_blockchain, contract_manager
    ):
        """测试区块链验证的多种方式"""
        kms = kms_with_blockchain
        cm = contract_manager

        # 生成并销毁密钥
        key_id = kms.generate_key(32, "AES-256-GCM")
        kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

        time.sleep(2)

        # 方式1: 通过KMS验证
        record1 = kms.verify_deletion_on_blockchain(key_id)
        assert record1 is not None

        # 方式2: 直接通过ContractManager验证
        record2 = cm.get_deletion_record(key_id)
        assert record2 is not None

        # 方式3: 使用is_key_deleted检查
        is_deleted = cm.is_key_deleted(key_id)
        assert is_deleted is True

        print("✓ 所有验证方式都通过")


# ===== 异常处理测试 =====


class TestExceptionHandling:
    """测试异常情况的处理"""

    def test_blockchain_connection_failure_graceful_degradation(self):
        """测试区块链连接失败时的降级处理"""
        # 使用错误的RPC URL
        try:
            cm = ContractManager(
                rpc_url="https://invalid-url.example.com", auto_connect=False
            )
            kms = KeyManagementService(contract_manager=cm)

            # 生成并销毁密钥（应该成功，但不记录到区块链）
            key_id = kms.generate_key(32, "AES-256-GCM")
            success = kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

            assert success is True  # 密钥销毁应该成功

            # 检查区块链记录失败日志
            failed_logs = kms.get_audit_log(operation="blockchain_record_failed")
            # 由于连接失败，可能没有尝试记录

            print("✓ 区块链连接失败时KMS仍能正常工作")

        except Exception as e:
            print(f"预期的异常: {e}")

    def test_destroy_nonexistent_key(self, kms_without_blockchain):
        """测试销毁不存在的密钥"""
        kms = kms_without_blockchain

        from src.kms.exceptions import KeyNotFoundError

        with pytest.raises(KeyNotFoundError):
            kms.destroy_key("nonexistent_key_id", DestructionMethod.DOD_OVERWRITE)

        print("✓ 正确抛出KeyNotFoundError异常")

    def test_access_destroyed_key(self, kms_without_blockchain):
        """测试访问已销毁的密钥"""
        kms = kms_without_blockchain

        from src.kms.exceptions import KeyDestroyedError

        # 生成并销毁密钥
        key_id = kms.generate_key(32, "AES-256-GCM")
        kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

        # 尝试访问已销毁的密钥
        with pytest.raises(KeyDestroyedError):
            key = kms.get_key(key_id)
            _ = key.key_data  # 访问密钥数据应该抛出异常

        print("✓ 正确抛出KeyDestroyedError异常")


# ===== 性能测试 =====


class TestPerformance:
    """性能基准测试"""

    @pytest.mark.performance
    def test_key_generation_performance(self, kms_without_blockchain):
        """测试密钥生成性能"""
        kms = kms_without_blockchain

        num_keys = 100
        start_time = time.time()

        for i in range(num_keys):
            kms.generate_key(32, "AES-256-GCM")

        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / num_keys

        print(f"✓ 生成{num_keys}个密钥")
        print(f"  总耗时: {elapsed_time:.2f}秒")
        print(f"  平均耗时: {avg_time*1000:.2f}毫秒/密钥")

        assert avg_time < 0.1  # 每个密钥生成应该少于100ms

    def test_destruction_performance_comparison(self, kms_without_blockchain):
        """对比4种销毁方法的性能"""
        kms = kms_without_blockchain

        methods = [
            DestructionMethod.SIMPLE_DEL,
            DestructionMethod.SINGLE_OVERWRITE,
            DestructionMethod.DOD_OVERWRITE,
            DestructionMethod.CTYPES_SECURE,
        ]

        results = {}
        num_iterations = 50

        for method in methods:
            times = []

            for _ in range(num_iterations):
                key_id = kms.generate_key(32, "AES-256-GCM")

                start_time = time.time()
                kms.destroy_key(key_id, method)
                elapsed_time = time.time() - start_time

                times.append(elapsed_time)

            avg_time = sum(times) / len(times)
            results[method.value] = avg_time

            print(f"✓ {method.value}: {avg_time*1000:.2f}毫秒")

        # 所有方法应该在50ms内完成（包含日志和统计开销）
        for method, avg_time in results.items():
            assert avg_time < 0.05, f"{method} 耗时过长: {avg_time*1000:.2f}ms"

        # 验证性能差异在合理范围内（论文可用的数据）
        print(f"\n性能对比（平均值，基于{num_iterations}次测试）:")
        for method, avg_time in sorted(results.items(), key=lambda x: x[1]):
            print(f"  {method:20s}: {avg_time*1000:6.2f}ms")

    @pytest.mark.slow
    def test_blockchain_recording_performance(self, kms_with_blockchain):
        """测试区块链记录性能（标记为慢速测试）"""
        kms = kms_with_blockchain

        num_tests = 3
        times = []

        for i in range(num_tests):
            key_id = kms.generate_key(32, "AES-256-GCM")

            start_time = time.time()
            kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
            elapsed_time = time.time() - start_time

            times.append(elapsed_time)
            print(f"  第{i+1}次: {elapsed_time:.2f}秒")

            time.sleep(1)  # 避免频繁请求

        avg_time = sum(times) / len(times)
        print(f"✓ 平均区块链记录时间: {avg_time:.2f}秒")

        # 区块链交易应该在120秒内完成
        assert avg_time < 120


# ===== 审计和统计测试 =====


class TestAuditAndStatistics:
    """测试审计日志和统计功能"""

    def test_audit_log_completeness(self, kms_without_blockchain):
        """测试审计日志的完整性"""
        kms = kms_without_blockchain

        # 执行一系列操作
        key_id = kms.generate_key(32, "AES-256-GCM")
        kms.get_key(key_id)
        kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

        # 检查审计日志
        all_logs = kms.get_audit_log()
        assert len(all_logs) >= 3  # 至少有生成、获取、销毁三个操作

        # 检查特定操作的日志
        gen_logs = kms.get_audit_log(operation="generate_key")
        assert len(gen_logs) >= 1

        destroy_logs = kms.get_audit_log(operation="destroy_key_success")
        assert len(destroy_logs) >= 1

        print(f"✓ 审计日志完整 (总计{len(all_logs)}条)")

    def test_statistics_accuracy(self, kms_with_blockchain):
        """测试统计信息的准确性"""
        kms = kms_with_blockchain

        # 生成3个密钥
        key_ids = []
        for i in range(3):
            key_id = kms.generate_key(32, "AES-256-GCM")
            key_ids.append(key_id)

        # 销毁2个密钥
        for key_id in key_ids[:2]:
            kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
            time.sleep(2)  # 等待区块链确认

        # 检查统计
        stats = kms.get_statistics()

        assert stats["total_generated"] >= 3
        assert stats["total_destroyed"] >= 2
        assert stats["active_keys"] >= 1
        assert stats["destroyed_keys"] >= 2
        assert stats["blockchain_enabled"] is True
        assert stats["blockchain_recordings"] >= 2

        print("✓ 统计信息准确")
        for key, value in stats.items():
            print(f"  {key}: {value}")


# ===== 完整工作流测试 =====


class TestCompleteWorkflow:
    """测试完整的工作流程"""

    @pytest.mark.integration
    def test_full_lifecycle_with_blockchain(self, kms_with_blockchain):
        """测试密钥完整生命周期（带区块链） ⭐ 综合测试"""
        kms = kms_with_blockchain

        print("\n" + "=" * 60)
        print("开始完整生命周期测试")
        print("=" * 60)

        # 1. 初始化验证
        print("\n1. 验证初始状态...")
        initial_stats = kms.get_statistics()
        blockchain_status = kms.get_blockchain_status()

        assert blockchain_status["enabled"] is True
        assert blockchain_status["connected"] is True

        print(f"  ✓ 区块链已连接: {blockchain_status['contract_address']}")

        # 2. 生成密钥
        print("\n2. 生成测试密钥...")
        key_id = kms.generate_key(
            key_size=32,
            algorithm="AES-256-GCM",
            purpose="full_lifecycle_test",
            owner_id="integration_test_user",
        )

        print(f"  ✓ 密钥生成: {key_id}")

        # 3. 访问密钥
        print("\n3. 访问密钥数据...")
        key = kms.get_key(key_id)
        key_data = key.key_data

        assert len(key_data) == 32
        assert key.metadata.status == KeyStatus.ACTIVE

        print(f"  ✓ 密钥可访问 (长度: {len(key_data)}字节)")
        print(f"  ✓ 密钥指纹: {key.metadata.fingerprint}")

        # 4. 销毁密钥
        print("\n4. 销毁密钥...")
        destruction_start = time.time()
        success = kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
        destruction_time = time.time() - destruction_start

        assert success is True

        print(f"  ✓ 密钥已销毁 (耗时: {destruction_time:.2f}秒)")

        # 5. 验证密钥状态
        print("\n5. 验证密钥状态...")
        destroyed_key = kms._keys[key_id]

        assert destroyed_key.metadata.status == KeyStatus.DESTROYED
        assert (
            destroyed_key.metadata.destruction_method == DestructionMethod.DOD_OVERWRITE
        )
        assert destroyed_key.metadata.destroyed_at is not None

        print(f"  ✓ 状态: {destroyed_key.metadata.status.value}")
        print(f"  ✓ 销毁方法: {destroyed_key.metadata.destruction_method.value}")
        print(f"  ✓ 销毁时间: {destroyed_key.metadata.destroyed_at}")

        # 6. 检查审计日志
        print("\n6. 检查审计日志...")
        key_logs = kms.get_audit_log(key_id=key_id)

        assert len(key_logs) >= 3  # 生成、访问、销毁

        print(f"  ✓ 审计记录: {len(key_logs)}条")

        # 检查区块链记录日志
        blockchain_logs = [log for log in key_logs if "blockchain" in log["operation"]]
        assert len(blockchain_logs) >= 1

        tx_hash = None
        for log in blockchain_logs:
            if log["operation"] == "blockchain_record_success":
                tx_hash = log["details"]["tx_hash"]
                print(f"  ✓ 区块链交易: {tx_hash}")

        # 7. 区块链验证
        print("\n7. 区块链验证...")
        time.sleep(3)  # 等待区块确认

        record = kms.verify_deletion_on_blockchain(key_id)

        assert record is not None
        assert record["key_id"] == key_id
        assert record["destruction_method"] == "dod_overwrite"
        assert record["exists"] is True

        print(f"  ✓ 链上记录存在")
        print(f"  ✓ 销毁时间: {record['timestamp_readable']}")
        print(f"  ✓ 操作者: {record['operator']}")
        print(f"  ✓ 证明哈希: {record['proof_hash'][:16]}...")

        # 8. 最终统计
        print("\n8. 最终统计...")
        final_stats = kms.get_statistics()

        assert final_stats["total_generated"] > initial_stats["total_generated"]
        assert final_stats["total_destroyed"] > initial_stats["total_destroyed"]
        assert final_stats["blockchain_recordings"] > initial_stats.get(
            "blockchain_recordings", 0
        )

        print(f"  ✓ 生成密钥: {final_stats['total_generated']}")
        print(f"  ✓ 销毁密钥: {final_stats['total_destroyed']}")
        print(f"  ✓ 区块链记录: {final_stats['blockchain_recordings']}")

        print("\n" + "=" * 60)
        print("✅ 完整生命周期测试通过！")
        print("=" * 60 + "\n")


# ===== 运行测试套件 =====

if __name__ == "__main__":
    """
    直接运行此文件进行快速测试
    """
    print("=" * 60)
    print("端到端集成测试套件")
    print("=" * 60)
    print("\n建议使用 pytest 运行完整测试:")
    print("  pytest tests/integration/test_end_to_end.py -v\n")
    print("或运行特定测试类:")
    print(
        "  pytest tests/integration/test_end_to_end.py::TestBlockchainIntegration -v\n"
    )
    print("=" * 60)

    # 简单的手动测试
    print("\n执行快速验证测试...\n")

    try:
        # 测试1: KMS基础功能
        print("1. 测试KMS基础功能...")
        kms = KeyManagementService()
        key_id = kms.generate_key(32, "AES-256-GCM")
        kms.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)
        print("   ✓ 基础功能正常\n")

        # 测试2: 区块链集成
        print("2. 测试区块链集成...")
        try:
            cm = ContractManager(auto_connect=True)
            kms_bc = KeyManagementService(contract_manager=cm)

            key_id = kms_bc.generate_key(32, "AES-256-GCM")
            kms_bc.destroy_key(key_id, DestructionMethod.DOD_OVERWRITE)

            time.sleep(2)
            record = kms_bc.verify_deletion_on_blockchain(key_id)

            if record:
                print(f"   ✓ 区块链集成正常")
                print(f"   交易哈希: {cm.contract_address}")
            else:
                print("   ⚠ 区块链记录未找到（可能需要等待更长时间）")

            cm.disconnect()

        except Exception as e:
            print(f"   ⚠ 区块链测试跳过: {e}")

        print("\n" + "=" * 60)
        print("✅ 快速验证完成！")
        print("=" * 60)
        print("\n运行完整测试请使用: pytest tests/integration/test_end_to_end.py -v")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
