"""
区块链交互模块

提供与以太坊智能合约交互的功能，包括：
- 合约管理（ContractManager）
- 配置管理（BlockchainConfig）
- 删除记录的链上存证
"""

from .config import BlockchainConfig
from .contract_manager import (
    ContractManager,
    ContractManagerError,
    ConnectionError,
    TransactionError,
    quick_record_deletion,
    quick_check_deletion,
)

__all__ = [
    "BlockchainConfig",
    "ContractManager",
    "ContractManagerError",
    "ConnectionError",
    "TransactionError",
    "quick_record_deletion",
    "quick_check_deletion",
]

__version__ = "0.1.0"
