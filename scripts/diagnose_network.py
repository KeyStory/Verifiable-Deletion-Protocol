"""
网络连接综合诊断工具
用于排查区块链连接问题
"""

import os
import sys
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import time

load_dotenv()


def diagnose_all():
    """运行所有诊断"""
    print("=" * 70)
    print("区块链网络诊断工具".center(70))
    print("=" * 70)

    results = []

    # 诊断1：环境变量
    print("\n📋 诊断1：环境变量检查")
    print("-" * 70)

    env_vars = [
        "INFURA_PROJECT_ID",
        "ETHEREUM_NETWORK",
        "WALLET_ADDRESS",
        "WALLET_PRIVATE_KEY",
    ]

    env_ok = True
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if "KEY" in var or "SECRET" in var:
                display = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display = value
            print(f"✅ {var}: {display}")
        else:
            print(f"❌ {var}: 未设置")
            env_ok = False

    results.append(("环境变量", env_ok))

    if not env_ok:
        print("\n⚠️  请在 .env 文件中配置缺失的环境变量")
        return results

    # 诊断2：网络连接
    print("\n🌐 诊断2：网络连接测试")
    print("-" * 70)

    project_id = os.getenv("INFURA_PROJECT_ID")
    network = os.getenv("ETHEREUM_NETWORK", "sepolia")
    infura_url = f"https://{network}.infura.io/v3/{project_id}"

    try:
        web3 = Web3(Web3.HTTPProvider(infura_url))

        # 测试连接速度
        start = time.time()
        is_connected = web3.is_connected()
        latency = (time.time() - start) * 1000

        if is_connected:
            print(f"✅ 连接成功")
            print(f"   延迟: {latency:.2f} ms")

            # 获取网络信息
            chain_id = web3.eth.chain_id
            block_number = web3.eth.block_number
            gas_price = web3.eth.gas_price

            print(f"   Chain ID: {chain_id}")
            print(f"   当前区块: {block_number:,}")
            print(f"   Gas价格: {web3.from_wei(gas_price, 'gwei'):.2f} Gwei")

            results.append(("网络连接", True))
        else:
            print(f"❌ 连接失败")
            results.append(("网络连接", False))
            return results

    except Exception as e:
        print(f"❌ 连接错误: {e}")
        results.append(("网络连接", False))
        return results

    # 诊断3：钱包配置
    print("\n👛 诊断3：钱包配置验证")
    print("-" * 70)

    wallet_address = os.getenv("WALLET_ADDRESS")
    private_key = os.getenv("WALLET_PRIVATE_KEY")

    if not wallet_address or not private_key:
        print("❌ 钱包配置不完整")
        results.append(("钱包配置", False))
        return results

    try:
        # 验证地址格式
        if not Web3.is_address(wallet_address):
            print(f"❌ 地址格式错误")
            results.append(("钱包配置", False))
            return results

        checksum_address = Web3.to_checksum_address(wallet_address)
        print(f"✅ 地址格式正确: {checksum_address}")

        # 验证私钥
        account = Account.from_key(private_key)
        if account.address.lower() != wallet_address.lower():
            print(f"❌ 私钥与地址不匹配")
            results.append(("钱包配置", False))
            return results

        print(f"✅ 私钥与地址匹配")
        results.append(("钱包配置", True))

    except Exception as e:
        print(f"❌ 钱包验证错误: {e}")
        results.append(("钱包配置", False))
        return results

    # 诊断4：余额检查
    print("\n💰 诊断4：余额检查")
    print("-" * 70)

    try:
        balance_wei = web3.eth.get_balance(checksum_address)
        balance_eth = web3.from_wei(balance_wei, "ether")

        print(f"余额: {balance_eth} ETH")

        if balance_eth >= 0.1:
            print(f"✅ 余额充足")
            results.append(("余额充足", True))
        elif balance_eth > 0:
            print(f"⚠️  余额较少，建议从水龙头获取更多")
            results.append(("余额充足", False))
        else:
            print(f"❌ 余额为零，请从水龙头获取测试ETH")
            results.append(("余额充足", False))

    except Exception as e:
        print(f"❌ 余额查询错误: {e}")
        results.append(("余额充足", False))

    # 诊断5：交易历史
    print("\n📜 诊断5：交易历史")
    print("-" * 70)

    try:
        nonce = web3.eth.get_transaction_count(checksum_address)
        print(f"交易计数: {nonce}")

        if nonce > 0:
            print(f"✅ 已有 {nonce} 笔交易")
        else:
            print(f"ℹ️  尚未发送过交易")

        results.append(("交易历史", True))

    except Exception as e:
        print(f"❌ 查询错误: {e}")
        results.append(("交易历史", False))

    # 诊断6：Gas估算
    print("\n⛽ 诊断6：Gas估算测试")
    print("-" * 70)

    try:
        gas_price = web3.eth.gas_price
        gas_limit = 21000
        total_cost = web3.from_wei(gas_price * gas_limit, "ether")

        print(f"当前Gas价格: {web3.from_wei(gas_price, 'gwei'):.2f} Gwei")
        print(f"简单转账成本: {total_cost:.6f} ETH")

        if balance_eth > total_cost * 10:
            print(f"✅ 余额足够支付至少10笔交易")
            results.append(("Gas估算", True))
        else:
            print(f"⚠️  余额仅够 {int(balance_eth / total_cost)} 笔交易")
            results.append(("Gas估算", False))

    except Exception as e:
        print(f"❌ Gas估算错误: {e}")
        results.append(("Gas估算", False))

    # 总结
    print("\n" + "=" * 70)
    print("诊断总结".center(70))
    print("=" * 70)

    for name, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")

    passed = sum(1 for _, status in results if status)
    total = len(results)

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n✅ 所有诊断通过，环境配置正常！")
    else:
        print("\n⚠️  部分诊断未通过，请根据上述提示修复")

    print("=" * 70)

    return results


if __name__ == "__main__":
    results = diagnose_all()
    all_passed = all(status for _, status in results)
    sys.exit(0 if all_passed else 1)
