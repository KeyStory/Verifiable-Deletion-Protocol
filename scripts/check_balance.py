"""
检查钱包余额
"""

import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


def check_balance():
    """检查钱包余额"""
    # 连接到Infura
    project_id = os.getenv("INFURA_PROJECT_ID")
    wallet_address = os.getenv("WALLET_ADDRESS")

    if not project_id or not wallet_address:
        print("❌ 错误：环境变量未配置")
        print("   请在 .env 文件中配置：")
        print("   - INFURA_PROJECT_ID")
        print("   - WALLET_ADDRESS")
        return False

    infura_url = f"https://sepolia.infura.io/v3/{project_id}"
    web3 = Web3(Web3.HTTPProvider(infura_url))

    if not web3.is_connected():
        print("❌ 无法连接到网络")
        return False

    # 转换为校验和地址
    address = Web3.to_checksum_address(wallet_address)

    # 获取余额
    balance_wei = web3.eth.get_balance(address)
    balance_eth = web3.from_wei(balance_wei, "ether")

    print("=" * 60)
    print("钱包余额查询".center(60))
    print("=" * 60)
    print(f"\n地址: {address}")
    print(f"余额: {balance_eth} ETH")
    print(f"     ({balance_wei} Wei)")

    # 余额评估
    if balance_eth >= 0.5:
        print(f"\n✅ 余额充足 (>= 0.5 ETH)")
    elif balance_eth >= 0.1:
        print(f"\n✅ 余额足够测试 (>= 0.1 ETH)")
    elif balance_eth > 0:
        print(f"\n⚠️  余额较少 ({balance_eth} ETH)")
        print(f"   建议从水龙头获取更多测试ETH")
    else:
        print(f"\n❌ 余额为零")
        print(f"   请从水龙头获取测试ETH:")
        print(f"   - https://sepoliafaucet.com/")
        print(f"   - https://www.infura.io/faucet/sepolia")

    print("=" * 60)

    return balance_eth > 0


if __name__ == "__main__":
    check_balance()
