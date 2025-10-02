"""
区块链连接完整验证脚本
目的：验证从连接到发送交易的整个流程
"""

import os
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class BlockchainVerifier:
    """区块链验证器"""

    def __init__(self):
        self.web3 = None
        self.account = None
        self.wallet_address = None

    def step1_connect(self):
        """步骤1：连接到测试网"""
        print("\n" + "=" * 60)
        print("步骤1：连接到Sepolia测试网")
        print("=" * 60)

        project_id = os.getenv("INFURA_PROJECT_ID")
        if not project_id:
            print("❌ 未找到INFURA_PROJECT_ID")
            return False

        infura_url = f"https://sepolia.infura.io/v3/{project_id}"
        self.web3 = Web3(Web3.HTTPProvider(infura_url))

        if not self.web3.is_connected():
            print("❌ 无法连接到Sepolia测试网")
            return False

        print("✅ 成功连接到Sepolia测试网")

        # 获取网络信息
        chain_id = self.web3.eth.chain_id
        block_number = self.web3.eth.block_number

        print(f"   Chain ID: {chain_id}")
        print(f"   当前区块: {block_number:,}")

        return True

    def step2_load_wallet(self):
        """步骤2：加载钱包"""
        print("\n" + "=" * 60)
        print("步骤2：加载钱包")
        print("=" * 60)

        wallet_address = os.getenv("WALLET_ADDRESS")
        private_key = os.getenv("WALLET_PRIVATE_KEY")

        if not wallet_address or not private_key:
            print("❌ 钱包配置不完整")
            return False

        try:
            self.account = Account.from_key(private_key)
            self.wallet_address = Web3.to_checksum_address(wallet_address)

            print(f"✅ 钱包加载成功")
            print(f"   地址: {self.wallet_address}")

        except Exception as e:
            print(f"❌ 钱包加载失败: {e}")
            return False

        return True

    def step3_check_balance(self):
        """步骤3：检查余额"""
        print("\n" + "=" * 60)
        print("步骤3：检查余额")
        print("=" * 60)

        # 添加空值检查
        if not self.web3 or not self.wallet_address:
            print("❌ Web3或钱包未初始化")
            return False

        try:
            balance_wei = self.web3.eth.get_balance(self.wallet_address)
            balance_eth = self.web3.from_wei(balance_wei, "ether")

            print(f"✅ 余额: {balance_eth} ETH")

            if balance_eth < 0.01:
                print(f"⚠️  警告：余额不足 0.01 ETH")
                print(f"   建议从水龙头获取测试ETH")
                return False

            return True

        except Exception as e:
            print(f"❌ 查询余额失败: {e}")
            return False

    def step4_estimate_gas(self):
        """步骤4：估算Gas"""
        print("\n" + "=" * 60)
        print("步骤4：估算交易成本")
        print("=" * 60)

        # 添加空值检查
        if not self.web3:
            print("❌ Web3未初始化")
            return False

        try:
            # 获取当前Gas价格
            gas_price = self.web3.eth.gas_price
            gas_price_gwei = self.web3.from_wei(gas_price, "gwei")

            # 简单转账需要21000 gas
            gas_limit = 21000

            # 计算总成本
            total_cost_wei = gas_price * gas_limit
            total_cost_eth = self.web3.from_wei(total_cost_wei, "ether")

            print(f"✅ Gas估算:")
            print(f"   Gas价格: {gas_price_gwei:.2f} Gwei")
            print(f"   Gas限制: {gas_limit:,}")
            print(f"   预计成本: {total_cost_eth:.6f} ETH")

            return True

        except Exception as e:
            print(f"❌ Gas估算失败: {e}")
            return False

    def step5_send_transaction(self):
        """步骤5：发送测试交易"""
        print("\n" + "=" * 60)
        print("步骤5：发送测试交易（发送给自己）")
        print("=" * 60)

        # 添加空值检查
        if not self.web3 or not self.wallet_address:
            print("❌ Web3或钱包未初始化")
            return None

        private_key = os.getenv("WALLET_PRIVATE_KEY")
        if not private_key:
            print("❌ 未找到私钥")
            return None

        try:
            # 构建交易
            transaction = {
                "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
                "to": self.wallet_address,  # 发送给自己
                "value": self.web3.to_wei(0.0001, "ether"),  # 0.0001 ETH
                "gas": 21000,
                "gasPrice": self.web3.eth.gas_price,
                "chainId": 11155111,  # Sepolia Chain ID
            }

            print(f"📤 交易详情:")
            print(f"   从: {self.wallet_address}")
            print(f"   到: {self.wallet_address}")
            print(f"   金额: 0.0001 ETH")
            print(f"   Nonce: {transaction['nonce']}")

            # 签名交易
            print(f"\n🔏 正在签名交易...")
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, private_key=private_key
            )

            print(f"✅ 交易已签名")

            # 发送交易
            print(f"\n📡 正在发送交易到区块链...")
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            print(f"✅ 交易已发送!")
            print(f"   交易哈希: {tx_hash_hex}")
            print(f"   区块浏览器: https://sepolia.etherscan.io/tx/{tx_hash_hex}")

            return tx_hash_hex

        except Exception as e:
            print(f"❌ 交易发送失败: {e}")
            return None

    def step6_wait_confirmation(self, tx_hash):
        """步骤6：等待交易确认"""
        print("\n" + "=" * 60)
        print("步骤6：等待交易确认")
        print("=" * 60)

        # 添加空值检查
        if not self.web3:
            print("❌ Web3未初始化")
            return False

        print(f"⏳ 等待交易确认（这可能需要15-60秒）...")
        print(f"   提示：您可以在浏览器中打开上述链接查看实时状态")

        try:
            # 等待交易收据（超时时间120秒）
            start_time = time.time()
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )
            elapsed_time = time.time() - start_time

            # 检查交易状态
            if tx_receipt["status"] == 1:
                print(f"\n✅ 交易成功确认!")
                print(f"   确认时间: {elapsed_time:.2f} 秒")
                print(f"   区块号: {tx_receipt['blockNumber']:,}")
                print(f"   Gas消耗: {tx_receipt['gasUsed']:,}")
                print(
                    f"   实际成本: {self.web3.from_wei(tx_receipt['gasUsed'] * tx_receipt['effectiveGasPrice'], 'ether'):.6f} ETH"
                )
                return True
            else:
                print(f"\n❌ 交易失败")
                print(f"   状态码: {tx_receipt['status']}")
                return False

        except Exception as e:
            print(f"\n❌ 等待确认超时或失败: {e}")
            return False

    def run_full_verification(self):
        """运行完整验证流程"""
        print("\n" + "=" * 70)
        print("区块链技术完整验证".center(70))
        print("=" * 70)

        steps = [
            ("连接测试网", self.step1_connect),
            ("加载钱包", self.step2_load_wallet),
            ("检查余额", self.step3_check_balance),
            ("估算Gas", self.step4_estimate_gas),
        ]

        # 执行前4个步骤
        for step_name, step_func in steps:
            if not step_func():
                print(f"\n" + "=" * 70)
                print(f"❌ 验证失败于: {step_name}".center(70))
                print("=" * 70)
                return False

        # 询问是否发送交易
        print("\n" + "=" * 70)
        print("准备发送测试交易".center(70))
        print("=" * 70)
        print("\n⚠️  这将消耗少量测试ETH（约0.0001-0.001 ETH）")

        # 自动确认（在脚本中）
        confirm = input("\n是否继续发送交易? (yes/no): ").strip().lower()

        if confirm != "yes":
            print("\n⏸️  验证已取消")
            return False

        # 发送交易
        tx_hash = self.step5_send_transaction()
        if not tx_hash:
            print(f"\n" + "=" * 70)
            print("❌ 交易发送失败".center(70))
            print("=" * 70)
            return False

        # 等待确认
        if not self.step6_wait_confirmation(tx_hash):
            print(f"\n" + "=" * 70)
            print("❌ 交易确认失败".center(70))
            print("=" * 70)
            return False

        # 全部成功
        print("\n" + "=" * 70)
        print("✅ 区块链技术验证完成!".center(70))
        print("所有功能正常，可以开始开发！".center(70))
        print("=" * 70)

        return True


def main():
    """主函数"""
    verifier = BlockchainVerifier()
    success = verifier.run_full_verification()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
