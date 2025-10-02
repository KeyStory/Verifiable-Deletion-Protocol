"""
测试钱包配置
验证钱包地址和私钥是否正确
"""

import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct  # 新增这一行
from dotenv import load_dotenv

load_dotenv()


def test_wallet_config():
    """测试钱包配置"""
    print("=" * 60)
    print("测试钱包配置".center(60))
    print("=" * 60 + "\n")

    # 1. 获取配置
    wallet_address = os.getenv("WALLET_ADDRESS")
    private_key = os.getenv("WALLET_PRIVATE_KEY")

    if not wallet_address or not private_key:
        print("❌ 错误：钱包配置不完整")
        print("   请在 .env 文件中配置：")
        print("   - WALLET_ADDRESS")
        print("   - WALLET_PRIVATE_KEY")
        return False

    # 2. 验证地址格式
    if not Web3.is_address(wallet_address):
        print(f"❌ 地址格式错误: {wallet_address}")
        return False

    # 转换为校验和地址
    checksum_address = Web3.to_checksum_address(wallet_address)
    print(f"✅ 钱包地址: {checksum_address}")

    # 3. 验证私钥
    try:
        # 从私钥派生地址
        account = Account.from_key(private_key)
        derived_address = account.address

        print(f"✅ 私钥有效")
        print(f"   从私钥派生的地址: {derived_address}")

        # 4. 验证地址匹配
        if derived_address.lower() != wallet_address.lower():
            print(f"\n❌ 错误：地址不匹配!")
            print(f"   .env中的地址: {wallet_address}")
            print(f"   私钥对应的地址: {derived_address}")
            print(f"   请检查是否复制了正确的私钥")
            return False

        print(f"✅ 地址与私钥匹配")

    except Exception as e:
        print(f"❌ 私钥验证失败: {e}")
        return False

    # 5. 测试签名功能 (修改这部分)
    try:
        message = "Test message for verification"
        # 使用 encode_defunct 包装消息
        message_encoded = encode_defunct(text=message)
        # 使用 account 对象的 sign_message 方法
        signed = account.sign_message(message_encoded)

        print(f"✅ 签名功能正常")
        print(f"   签名示例: {signed.signature.hex()[:32]}...")

    except Exception as e:
        print(f"❌ 签名测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 钱包配置验证成功!".center(60))
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_wallet_config()
    exit(0 if success else 1)
