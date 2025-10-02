"""
测试Infura连接
验证API密钥是否有效
"""

import os
from web3 import Web3
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def test_infura_connection():
    """测试Infura连接"""
    print("=" * 60)
    print("测试Infura连接".center(60))
    print("=" * 60 + "\n")

    # 1. 获取配置
    project_id = os.getenv("INFURA_PROJECT_ID")
    network = os.getenv("ETHEREUM_NETWORK", "sepolia")

    if not project_id:
        print("❌ 错误：未找到INFURA_PROJECT_ID")
        print("   请在 .env 文件中配置")
        return False

    # 显示部分Project ID（隐藏敏感信息）
    masked_id = f"{project_id[:8]}...{project_id[-4:]}"
    print(f"✅ Project ID: {masked_id}")
    print(f"✅ 网络: {network}\n")

    # 2. 构建连接URL
    infura_url = f"https://{network}.infura.io/v3/{project_id}"

    # 3. 创建Web3实例
    try:
        web3 = Web3(Web3.HTTPProvider(infura_url))
    except Exception as e:
        print(f"❌ 创建Web3实例失败: {e}")
        return False

    # 4. 测试连接
    print("正在连接到Sepolia测试网...")
    try:
        is_connected = web3.is_connected()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

    if not is_connected:
        print("❌ 无法连接到Infura节点")
        print("   可能的原因：")
        print("   1. Project ID 错误")
        print("   2. 网络连接问题")
        print("   3. Infura服务异常")
        return False

    print("✅ 成功连接到Sepolia测试网!\n")

    # 5. 获取网络信息
    try:
        chain_id = web3.eth.chain_id
        block_number = web3.eth.block_number
        gas_price = web3.eth.gas_price

        print(f"📊 网络信息:")
        print(f"   Chain ID: {chain_id}")
        print(f"   当前区块高度: {block_number:,}")
        print(f"   当前Gas价格: {web3.from_wei(gas_price, 'gwei'):.2f} Gwei")
        print(f"   ({web3.from_wei(gas_price, 'ether'):.10f} ETH)")

    except Exception as e:
        print(f"⚠️  获取网络信息失败: {e}")

    print("\n" + "=" * 60)
    print("✅ Infura配置验证成功!".center(60))
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_infura_connection()
    exit(0 if success else 1)
