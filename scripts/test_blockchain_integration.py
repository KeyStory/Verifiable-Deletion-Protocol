"""
区块链集成测试脚本

测试 ContractManager 的所有核心功能：
1. 连接区块链
2. 记录删除
3. 查询记录
4. 验证证明
"""

import sys
import time
import hashlib
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.blockchain import (
    BlockchainConfig,
    ContractManager,
    ConnectionError,
    TransactionError,
)


def test_configuration():
    """测试配置"""
    print("\n" + "=" * 70)
    print("TEST 1: Configuration Validation")
    print("=" * 70)

    # 验证配置
    is_valid, errors = BlockchainConfig.validate_config()

    if is_valid:
        print("✓ Configuration is valid")
        BlockchainConfig.print_config(hide_sensitive=True)
        return True
    else:
        print("✗ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False


def test_connection():
    """测试连接"""
    print("\n" + "=" * 70)
    print("TEST 2: Blockchain Connection")
    print("=" * 70)

    try:
        manager = ContractManager(auto_connect=False)
        manager.connect()

        if manager.account is None or manager.w3 is None:
            raise ConnectionError("Failed to initialize manager")

        print(f"✓ Connected to network")
        print(f"  Account: {manager.account.address}")
        print(f"  Balance: {manager.get_balance():.4f} ETH")
        print(f"  Chain ID: {manager.w3.eth.chain_id}")
        print(f"  Contract: {manager.contract_address}")

        manager.disconnect()
        return True

    except ConnectionError as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_record_deletion():
    """测试记录删除"""
    print("\n" + "=" * 70)
    print("TEST 3: Record Deletion")
    print("=" * 70)

    try:
        with ContractManager() as manager:
            # 生成测试数据
            key_id = f"test_key_{int(time.time())}"
            method = "ctypes_secure"

            # 生成证明哈希（模拟）
            proof_data = f"{key_id}:{method}:{time.time()}"
            proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

            print(f"Recording deletion for:")
            print(f"  Key ID: {key_id}")
            print(f"  Method: {method}")
            print(f"  Proof Hash: {proof_hash[:16]}...")

            # 记录删除
            result = manager.record_deletion(
                key_id=key_id,
                destruction_method=method,
                proof_hash=proof_hash,
                wait_for_confirmation=True,
            )

            print(f"\n✓ Deletion recorded successfully")
            print(f"  Transaction: {result['tx_hash']}")
            print(f"  Block Number: {result.get('block_number', 'Pending')}")
            print(f"  Gas Used: {result.get('gas_used', 'N/A')}")
            print(f"  Status: {result['status']}")

            return True, key_id

    except TransactionError as e:
        print(f"✗ Transaction failed: {e}")
        return False, None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False, None


def test_query_record(key_id: str):
    """测试查询记录"""
    print("\n" + "=" * 70)
    print("TEST 4: Query Deletion Record")
    print("=" * 70)

    try:
        with ContractManager() as manager:
            print(f"Querying record for key: {key_id}")

            # 查询记录
            record = manager.get_deletion_record(key_id)

            if record:
                print(f"\n✓ Record found:")
                print(f"  Key ID: {record['key_id']}")
                print(f"  Method: {record['destruction_method']}")
                print(f"  Timestamp: {record['timestamp_readable']}")
                print(f"  Operator: {record['operator']}")
                print(f"  Proof Hash: {record['proof_hash'][:16]}...")
                print(f"  Exists: {record['exists']}")
                return True
            else:
                print(f"✗ Record not found")
                return False

    except Exception as e:
        print(f"✗ Query failed: {e}")
        return False


def test_check_deletion(key_id: str):
    """测试检查删除状态"""
    print("\n" + "=" * 70)
    print("TEST 5: Check Deletion Status")
    print("=" * 70)

    try:
        with ContractManager() as manager:
            is_deleted = manager.is_key_deleted(key_id)

            if is_deleted:
                print(f"✓ Key {key_id} is marked as deleted")
                return True
            else:
                print(f"✗ Key {key_id} is NOT marked as deleted")
                return False

    except Exception as e:
        print(f"✗ Check failed: {e}")
        return False


def test_verify_proof(key_id: str):
    """测试验证证明"""
    print("\n" + "=" * 70)
    print("TEST 6: Verify Deletion Proof")
    print("=" * 70)

    try:
        with ContractManager() as manager:
            # 获取原始记录
            record = manager.get_deletion_record(key_id)

            if not record:
                print("✗ Record not found, cannot verify proof")
                return False

            # 验证正确的证明
            is_valid = manager.verify_deletion_proof(
                key_id=record["key_id"],
                destruction_method=record["destruction_method"],
                proof_hash=record["proof_hash"],
            )

            if is_valid:
                print("✓ Proof verification PASSED (correct proof)")
            else:
                print("✗ Proof verification FAILED (correct proof should pass)")
                return False

            # 验证错误的证明（应该失败）
            fake_proof = hashlib.sha256(b"fake_proof").hexdigest()
            is_valid_fake = manager.verify_deletion_proof(
                key_id=record["key_id"],
                destruction_method=record["destruction_method"],
                proof_hash=fake_proof,
            )

            if not is_valid_fake:
                print("✓ Proof verification FAILED as expected (incorrect proof)")
                return True
            else:
                print(
                    "✗ Proof verification PASSED incorrectly (fake proof should fail)"
                )
                return False

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


def test_batch_deletion():
    """测试批量删除"""
    print("\n" + "=" * 70)
    print("TEST 7: Batch Record Deletion")
    print("=" * 70)

    try:
        with ContractManager() as manager:
            # 生成多个测试数据
            import time

            deletions = []
            for i in range(3):
                key_id = f"batch_test_key_{int(time.time())}_{i}"
                method = "dod_overwrite"
                proof_data = f"{key_id}:{method}:{time.time()}"
                proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

                deletions.append(
                    {
                        "key_id": key_id,
                        "destruction_method": method,
                        "proof_hash": proof_hash,
                    }
                )

            print(f"Recording {len(deletions)} deletions in batch...")

            result = manager.batch_record_deletion(
                deletions=deletions, wait_for_confirmation=True
            )

            print(f"\n✓ Batch deletion recorded successfully")
            print(f"  Transaction: {result['tx_hash']}")
            print(f"  Count: {result['count']}")
            print(f"  Block Number: {result.get('block_number', 'Pending')}")
            print(f"  Gas Used: {result.get('gas_used', 'N/A')}")

            # 验证每个记录
            print(f"\nVerifying individual records...")
            all_verified = True
            for deletion in deletions:
                is_deleted = manager.is_key_deleted(deletion["key_id"])
                status = "✓" if is_deleted else "✗"
                print(f"  {status} {deletion['key_id']}")
                all_verified = all_verified and is_deleted

            return all_verified

    except TransactionError as e:
        print(f"✗ Batch transaction failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("BLOCKCHAIN INTEGRATION TEST SUITE")
    print("=" * 70)

    import time

    results = {}

    # Test 1: Configuration
    results["config"] = test_configuration()
    if not results["config"]:
        print(
            "\n✗ Configuration test failed. Please fix configuration before continuing."
        )
        return

    # Test 2: Connection
    results["connection"] = test_connection()
    if not results["connection"]:
        print("\n✗ Connection test failed. Cannot proceed with other tests.")
        return

    # Test 3: Record Deletion
    success, test_key_id = test_record_deletion()
    results["record"] = success

    if success and test_key_id:
        # Wait a moment for blockchain to process
        time.sleep(3)

        # Test 4: Query Record
        results["query"] = test_query_record(test_key_id)

        # Test 5: Check Deletion
        results["check"] = test_check_deletion(test_key_id)

        # Test 6: Verify Proof
        results["verify"] = test_verify_proof(test_key_id)
    else:
        results["query"] = False
        results["check"] = False
        results["verify"] = False

    # Test 7: Batch Deletion
    results["batch"] = test_batch_deletion()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"  {status}  {test_name.upper()}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("=" * 70)


if __name__ == "__main__":
    main()
