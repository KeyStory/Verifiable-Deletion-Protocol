"""
区块链配置管理模块

管理区块链连接参数、合约地址、ABI路径等配置信息。
从环境变量和配置文件中读取敏感信息。
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class BlockchainConfig:
    """区块链配置类"""

    # 网络配置
    NETWORK = os.getenv("ETHEREUM_NETWORK", "sepolia")
    CHAIN_ID = 11155111  # Sepolia Chain ID

    # Infura 配置
    INFURA_PROJECT_ID = os.getenv("INFURA_PROJECT_ID")
    INFURA_PROJECT_SECRET = os.getenv("INFURA_PROJECT_SECRET")

    # 钱包配置
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

    # 合约配置
    CONTRACT_ADDRESS = "0x742f6158A12f1C3BBae97EC262024658ae42685a"

    # 项目路径
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    CONTRACTS_DIR = PROJECT_ROOT / "contracts"
    ARTIFACTS_DIR = CONTRACTS_DIR / "artifacts" / "contracts" / "DeletionProof.sol"
    ABI_PATH = ARTIFACTS_DIR / "DeletionProof.json"

    # 交易配置
    GAS_LIMIT = 300000  # 默认 gas 限制
    MAX_PRIORITY_FEE = 1  # Gwei
    MAX_FEE = 20  # Gwei

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒
    TRANSACTION_TIMEOUT = 120  # 秒

    @classmethod
    def get_rpc_url(cls) -> str:
        """获取 RPC URL"""
        if not cls.INFURA_PROJECT_ID:
            raise ValueError("INFURA_PROJECT_ID not found in environment variables")
        return f"https://{cls.NETWORK}.infura.io/v3/{cls.INFURA_PROJECT_ID}"

    @classmethod
    def load_contract_abi(cls) -> dict:
        """
        从编译产物中加载合约 ABI

        Returns:
            dict: 合约 ABI 对象

        Raises:
            FileNotFoundError: 如果 ABI 文件不存在
            json.JSONDecodeError: 如果 ABI 文件格式错误
        """
        if not cls.ABI_PATH.exists():
            raise FileNotFoundError(
                f"Contract ABI not found at {cls.ABI_PATH}\n"
                f"Please compile the contract first: cd contracts && npx hardhat compile"
            )

        with open(cls.ABI_PATH, "r", encoding="utf-8") as f:
            contract_json = json.load(f)

        # Hardhat 编译产物包含 abi 字段
        if "abi" not in contract_json:
            raise ValueError(f"Invalid contract ABI file: 'abi' field not found")

        return contract_json["abi"]

    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        验证配置完整性

        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 检查必需的环境变量
        if not cls.INFURA_PROJECT_ID:
            errors.append("INFURA_PROJECT_ID not set")

        if not cls.WALLET_ADDRESS:
            errors.append("WALLET_ADDRESS not set")

        if not cls.WALLET_PRIVATE_KEY:
            errors.append("WALLET_PRIVATE_KEY not set")

        # 检查合约地址格式
        if not cls.CONTRACT_ADDRESS.startswith("0x"):
            errors.append("Invalid CONTRACT_ADDRESS format")

        # 检查 ABI 文件
        if not cls.ABI_PATH.exists():
            errors.append(f"Contract ABI not found at {cls.ABI_PATH}")

        return (len(errors) == 0, errors)

    @classmethod
    def print_config(cls, hide_sensitive: bool = True) -> None:
        """
        打印当前配置（用于调试）

        Args:
            hide_sensitive: 是否隐藏敏感信息
        """

        def mask_value(value: str | None, show_length: int = 6) -> str:
            """遮盖敏感信息"""
            if not value:
                return "Not Set"
            if hide_sensitive and len(value) > show_length:
                return f"{value[:show_length]}...{value[-4:]}"
            return value if not hide_sensitive else "***HIDDEN***"

        print("=" * 60)
        print("Blockchain Configuration")
        print("=" * 60)
        print(f"Network:              {cls.NETWORK}")
        print(f"Chain ID:             {cls.CHAIN_ID}")
        print(
            f"RPC URL:              {cls.get_rpc_url() if cls.INFURA_PROJECT_ID else 'Not Set'}"
        )
        print(f"Contract Address:     {cls.CONTRACT_ADDRESS}")
        print(f"Wallet Address:       {mask_value(cls.WALLET_ADDRESS)}")
        print(f"Private Key:          {mask_value(cls.WALLET_PRIVATE_KEY, 4)}")
        print(f"ABI Path:             {cls.ABI_PATH}")
        print(f"ABI Exists:           {cls.ABI_PATH.exists()}")
        print("=" * 60)


# 配置验证（模块加载时执行）
if __name__ == "__main__":
    # 验证配置
    is_valid, errors = BlockchainConfig.validate_config()

    if is_valid:
        print("✓ Configuration is valid")
        BlockchainConfig.print_config(hide_sensitive=True)
    else:
        print("✗ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file and contract compilation.")
