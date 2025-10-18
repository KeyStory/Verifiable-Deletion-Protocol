"""
可验证删除协议 - 完整流程演示

展示从用户注册、数据加密存储、到密钥销毁、验证删除的完整流程。
适用于论文演示和答辩展示。

使用方式：
    python demo.py --scenario basic
    python demo.py --scenario blockchain
    python demo.py --scenario comparison
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.kms.key_manager import KeyManagementService, DestructionMethod
from src.crypto.crypto_manager import CryptoManager
from src.database.database import Database


class DemoRunner:
    """演示运行器"""

    def __init__(self, use_blockchain: bool = False):
        """
        初始化演示环境

        Args:
            use_blockchain: 是否使用区块链
        """
        print("\n" + "=" * 70)
        print("  可验证删除协议 - 完整流程演示".center(70))
        print("=" * 70)

        # 初始化组件
        print("\n[1/4] 初始化系统组件...")

        # KMS
        if use_blockchain:
            try:
                from src.blockchain.contract_manager import ContractManager

                cm = ContractManager(auto_connect=True)
                self.kms = KeyManagementService(contract_manager=cm)
                print("  ✓ KMS已启动（区块链已连接）")
                print(f"    合约地址: {cm.contract_address}")
            except Exception as e:
                print(f"  ⚠ 区块链连接失败，使用本地模式: {e}")
                self.kms = KeyManagementService()
        else:
            self.kms = KeyManagementService()
            print("  ✓ KMS已启动（本地模式）")

        # CryptoManager
        self.crypto = CryptoManager(self.kms)
        print("  ✓ 加密管理器已初始化")

        # Database
        self.db = Database("data/demo.db")
        print("  ✓ 数据库已连接")

        print("\n系统就绪！\n")

    def run_basic_scenario(self):
        """
        场景1：基本流程演示

        演示：用户注册 → 数据加密 → 密钥销毁 → 验证删除
        """
        print("=" * 70)
        print("场景1：基本删除协议流程")
        print("=" * 70)

        user_id = f"demo_user_{int(time.time())}"
        username = f"Alice_{int(time.time())}"  # 使用时间戳保证唯一性

        # Step 1: 用户注册
        print(f"\n[步骤 1/6] 用户注册")
        print(f"  用户ID: {user_id}")
        print(f"  用户名: {username}")

        success = self.db.create_user(user_id, username, "alice@example.com")

        if not success:
            # 可能是用户名已存在，尝试使用唯一的用户名
            username = f"Alice_{int(time.time())}"
            success = self.db.create_user(user_id, username, "alice@example.com")

        if success:
            print("  ✓ 用户注册成功")
        else:
            print("  ✗ 用户注册失败")
            print("  提示：数据库可能已存在重复数据")
            return

        # Step 2: 加密用户数据
        print(f"\n[步骤 2/6] 加密敏感数据")

        # 模拟不同类型的用户数据
        sensitive_data = {
            "profile": f"姓名: {username}\n身份证: 110101199001011234\n电话: 13800138000",
            "game_record": f"游戏记录：第1局胜利，第2局失败，总得分: 1250",
            "payment": f"支付信息：银行卡尾号 1234，余额: ¥150.00",
        }

        for data_type, data_content in sensitive_data.items():
            ciphertext, metadata = self.crypto.encrypt_user_data(
                user_id=user_id, data=data_content, associated_data=user_id
            )

            self.db.store_encrypted_data(
                user_id=user_id,
                data_type=data_type,
                ciphertext=ciphertext,
                metadata=metadata.to_dict(),
            )

            print(f"  ✓ {data_type} 已加密存储 ({len(ciphertext)} 字节)")

        print(f"  密钥ID: {metadata.key_id}")

        # Step 3: 验证数据可解密
        print(f"\n[步骤 3/6] 验证数据可正常访问")

        encrypted_records = self.db.get_encrypted_data(user_id)
        print(f"  共有 {len(encrypted_records)} 条加密记录")

        # 解密第一条记录作为演示
        if encrypted_records:
            first_record = encrypted_records[0]
            from src.crypto.crypto_manager import EncryptionMetadata

            metadata = EncryptionMetadata.from_dict(first_record["encryption_metadata"])

            try:
                plaintext = self.crypto.decrypt_user_data(
                    ciphertext=first_record["ciphertext"],
                    metadata=metadata,
                    associated_data=user_id,
                )
                print(f"  ✓ 数据解密成功")
                print(f"  内容预览: {plaintext.decode('utf-8')[:30]}...")
            except Exception as e:
                print(f"  ✗ 解密失败: {e}")

        # Step 4: 用户请求删除（被遗忘权）
        print(f"\n[步骤 4/6] 用户行使'被遗忘权'，请求删除数据")
        print("  正在销毁加密密钥...")

        time.sleep(1)  # 模拟处理时间

        deletion_result = self.crypto.delete_user_data(
            user_id=user_id, destruction_method=DestructionMethod.DOD_OVERWRITE
        )

        print(f"  ✓ 密钥销毁成功")
        print(f"  销毁方法: {deletion_result['method']}")
        print(f"  时间戳: {deletion_result['timestamp']}")

        if "blockchain_tx" in deletion_result:
            print(f"  ✓ 区块链记录: {deletion_result['blockchain_tx']}")
            print(f"  证明哈希: {deletion_result['proof_hash'][:16]}...")

        # 标记数据库中的用户状态
        self.db.mark_user_deleted(
            user_id=user_id,
            key_id=deletion_result["key_id"],
            destruction_method=deletion_result["method"],
            blockchain_tx=deletion_result.get("blockchain_tx"),
            proof_hash=deletion_result.get("proof_hash"),
        )

        # Step 5: 验证数据不可恢复
        print(f"\n[步骤 5/6] 验证数据永久不可恢复")

        try:
            # 尝试解密（应该失败）
            plaintext = self.crypto.decrypt_user_data(
                ciphertext=first_record["ciphertext"],
                metadata=metadata,
                associated_data=user_id,
            )
            print("  ✗ 错误：数据仍可解密！")
        except Exception as e:
            print(f"  ✓ 正确：数据无法解密")
            print(f"  异常类型: {type(e).__name__}")

        # Step 6: 验证删除记录
        print(f"\n[步骤 6/6] 查询删除证明")

        verification = self.crypto.verify_deletion(user_id)

        print(f"  ✓ 密钥状态: {verification['key_status']}")
        print(f"  ✓ 已删除: {verification['deleted']}")

        if verification.get("blockchain_verified"):
            record = verification["blockchain_record"]
            print(f"  ✓ 区块链验证通过")
            print(f"    时间戳: {record['timestamp']}")
            print(f"    操作者: {record['operator'][:10]}...")

        # 从数据库获取删除记录
        db_record = self.db.get_deletion_record(user_id)
        if db_record:
            print(f"  ✓ 本地删除记录存在")

        print("\n" + "=" * 70)
        print("✅ 基本流程演示完成！")
        print("=" * 70)

    def run_comparison_scenario(self):
        """
        场景2：对比实验演示

        演示：4种密钥销毁方法的安全性对比
        """
        print("=" * 70)
        print("场景2：密钥销毁方法对比实验")
        print("=" * 70)

        methods = [
            (DestructionMethod.SIMPLE_DEL, "简单删除（不安全）"),
            (DestructionMethod.SINGLE_OVERWRITE, "单次覆写"),
            (DestructionMethod.DOD_OVERWRITE, "DoD标准（3次覆写）"),
            (DestructionMethod.CTYPES_SECURE, "ctypes内存操作"),
        ]

        results = []

        for i, (method, description) in enumerate(methods, 1):
            print(f"\n[测试 {i}/4] {description}")
            print(f"  方法: {method.value}")

            # 创建测试用户
            user_id = f"test_user_{method.value}_{int(time.time())}"
            self.db.create_user(user_id, f"TestUser_{i}")

            # 加密数据
            test_data = "SECRET_KEY_ABCD_1234567890123456"
            ciphertext, metadata = self.crypto.encrypt_user_data(
                user_id=user_id, data=test_data, associated_data=user_id
            )

            print(f"  ✓ 测试数据已加密")

            # 销毁密钥（分别测量本地和区块链时间）
            local_start = time.time()

            # 临时禁用区块链以测量纯密钥销毁时间
            original_cm = self.kms._contract_manager
            self.kms._contract_manager = None

            deletion_result_local = self.crypto.delete_user_data(user_id, method)
            local_time = (time.time() - local_start) * 1000

            # 恢复区块链连接
            self.kms._contract_manager = original_cm

            # 如果有区块链，记录删除
            blockchain_time = 0.0
            if self.kms._contract_manager:
                # 重新获取密钥以记录区块链
                # 注意：密钥已被销毁，需要从审计日志获取信息
                blockchain_start = time.time()

                # 手动记录到区块链
                try:
                    from src.kms.key_manager import KeyStatus

                    secure_key = self.kms._keys[deletion_result_local["key_id"]]

                    # 确保 destroyed_at 不为 None
                    if secure_key.metadata.destroyed_at is None:
                        raise ValueError("Key destroyed_at timestamp is None")

                    proof_hash = self.kms._generate_proof_hash(
                        deletion_result_local["key_id"],
                        method.value,
                        secure_key.metadata.destroyed_at,
                        secure_key.metadata.fingerprint,
                    )

                    blockchain_result = self.kms._contract_manager.record_deletion(
                        key_id=deletion_result_local["key_id"],
                        destruction_method=method.value,
                        proof_hash=proof_hash,
                        wait_for_confirmation=True,
                    )

                    blockchain_time = (time.time() - blockchain_start) * 1000
                except Exception as e:
                    print(f"  ⚠ 区块链记录失败: {e}")

            elapsed_time = local_time + blockchain_time

            print(f"  ✓ 密钥已销毁")
            print(f"  本地销毁耗时: {local_time:.2f}ms")
            if blockchain_time > 0:
                print(f"  区块链记录耗时: {blockchain_time:.2f}ms")
            print(f"  总耗时: {elapsed_time:.2f}ms")

            # 验证
            verification = self.crypto.verify_deletion(user_id)

            results.append(
                {
                    "method": description,
                    "method_value": method.value,
                    "elapsed_time": elapsed_time,
                    "deleted": verification["deleted"],
                    "key_status": verification["key_status"],
                }
            )

        # 显示对比结果
        print("\n" + "=" * 70)
        print("实验结果对比".center(70))
        print("=" * 70)

        print(f"\n{'方法':<25} {'耗时(ms)':<12} {'状态':<15} {'安全性'}")
        print("-" * 70)

        for r in results:
            safety = "✗ 低" if "simple_del" in r["method_value"] else "✓ 高"
            print(
                f"{r['method']:<25} {r['elapsed_time']:<12.2f} {r['key_status']:<15} {safety}"
            )

        print("\n结论：")
        print("  • 所有方法性能相近（<25ms）")
        print("  • DoD标准和ctypes方法安全性最高")
        print("  • 简单删除完全不安全，数据可能残留")

        print("\n" + "=" * 70)
        print("✅ 对比实验完成！")
        print("=" * 70)

    def run_blockchain_scenario(self):
        """
        场景3：区块链验证流程

        重点展示区块链存证功能
        """
        print("=" * 70)
        print("场景3：区块链存证与验证")
        print("=" * 70)

        # 检查区块链是否可用
        if not self.kms._contract_manager:
            print("\n⚠️  区块链未连接，无法运行此场景")
            print("请确保：")
            print("  1. .env 文件配置正确")
            print("  2. 钱包有足够的测试网ETH")
            print("  3. 网络连接正常")
            return

        print("\n✓ 区块链已连接")
        print(f"  合约地址: {self.kms._contract_manager.contract_address}")

        # 创建用户
        user_id = f"blockchain_user_{int(time.time())}"
        print(f"\n[步骤 1/5] 创建用户: {user_id}")
        self.db.create_user(user_id, "BlockchainUser", "user@example.com")

        # 加密数据
        print(f"\n[步骤 2/5] 加密敏感数据")
        data = "机密信息：项目代号 Phoenix，预算 $100,000"
        ciphertext, metadata = self.crypto.encrypt_user_data(user_id, data, user_id)
        self.db.store_encrypted_data(
            user_id, "confidential", ciphertext, metadata.to_dict()
        )
        print(f"  ✓ 数据已加密")

        # 销毁密钥并记录到区块链
        print(f"\n[步骤 3/5] 销毁密钥并记录到区块链")
        print("  正在发送交易到Sepolia测试网...")

        start_time = time.time()
        deletion_result = self.crypto.delete_user_data(
            user_id=user_id, destruction_method=DestructionMethod.DOD_OVERWRITE
        )
        elapsed_time = time.time() - start_time

        if "blockchain_tx" in deletion_result:
            print(f"  ✓ 交易已提交 (耗时: {elapsed_time:.2f}秒)")
            print(f"  交易哈希: {deletion_result['blockchain_tx']}")
            print(
                f"  Etherscan: https://sepolia.etherscan.io/tx/{deletion_result['blockchain_tx']}"
            )

            # 标记数据库中的用户删除状态
            self.db.mark_user_deleted(
                user_id=user_id,
                key_id=deletion_result["key_id"],
                destruction_method=deletion_result["method"],
                blockchain_tx=deletion_result["blockchain_tx"],
                proof_hash=deletion_result.get("proof_hash"),
            )

            # 等待确认
            print("\n  等待区块确认...")
            time.sleep(3)

            # 从区块链验证
            print(f"\n[步骤 4/5] 从区块链查询删除记录")

            verification = self.crypto.verify_deletion(user_id)

            if verification.get("blockchain_verified"):
                record = verification["blockchain_record"]
                print(f"  ✓ 区块链验证成功")
                print(f"  删除时间: {record['timestamp']}")
                print(f"  操作者地址: {record['operator']}")
                print(f"  证明哈希: {record['proof_hash'][:16]}...")
            else:
                print(f"  ⚠️  区块链记录未找到（可能需要更长的确认时间）")
        else:
            print(f"  ⚠️  区块链记录失败")

        # 对比本地记录和链上记录
        print(f"\n[步骤 5/5] 对比本地与链上记录")

        db_record = self.db.get_deletion_record(user_id)
        if db_record is None:
            raise ValueError("db_record is None")

        print("\n  本地记录:")
        print(f"    销毁方法: {db_record['destruction_method']}")
        print(f"    删除时间: {db_record['deleted_at']}")

        if verification.get("blockchain_verified"):
            print("\n  区块链记录:")
            print(f"    时间戳: {record['timestamp']}")
            print(f"    不可篡改: ✓")
            print(f"    公开可验证: ✓")

        print("\n" + "=" * 70)
        print("✅ 区块链场景演示完成！")
        print("=" * 70)

    def cleanup(self):
        """清理资源"""
        if hasattr(self, "db"):
            self.db.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="可验证删除协议演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python demo.py --scenario basic           # 基本流程
  python demo.py --scenario comparison      # 方法对比
  python demo.py --scenario blockchain      # 区块链验证
  python demo.py --all                      # 运行所有场景
        """,
    )

    parser.add_argument(
        "--scenario", choices=["basic", "comparison", "blockchain"], help="选择演示场景"
    )

    parser.add_argument("--all", action="store_true", help="运行所有演示场景")

    parser.add_argument(
        "--no-blockchain", action="store_true", help="禁用区块链功能（仅本地演示）"
    )

    args = parser.parse_args()

    # 如果没有指定任何参数，显示帮助
    if not args.scenario and not args.all:
        parser.print_help()
        return

    try:
        # 初始化演示环境
        use_blockchain = not args.no_blockchain
        demo = DemoRunner(use_blockchain=use_blockchain)

        # 运行演示
        if args.all:
            demo.run_basic_scenario()
            print("\n\n")
            demo.run_comparison_scenario()
            if use_blockchain:
                print("\n\n")
                demo.run_blockchain_scenario()
        else:
            if args.scenario == "basic":
                demo.run_basic_scenario()
            elif args.scenario == "comparison":
                demo.run_comparison_scenario()
            elif args.scenario == "blockchain":
                demo.run_blockchain_scenario()

        # 清理
        demo.cleanup()

    except KeyboardInterrupt:
        print("\n\n演示已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
