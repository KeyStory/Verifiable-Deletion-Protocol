"""
智能合约交互管理模块

提供与 DeletionProof 智能合约交互的高级接口。
负责连接区块链、发送交易、查询数据等操作。
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import TransactionNotFound, TimeExhausted, ContractLogicError
from web3.types import TxReceipt, Wei
from eth_typing import ChecksumAddress
from eth_account.signers.local import LocalAccount
from .config import BlockchainConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContractManagerError(Exception):
    """合约管理器基础异常"""

    pass


class ConnectionError(ContractManagerError):
    """区块链连接异常"""

    pass


class TransactionError(ContractManagerError):
    """交易执行异常"""

    pass


class ContractManager:
    """
    智能合约管理器

    管理与 DeletionProof 智能合约的所有交互，包括：
    - 记录删除操作
    - 查询删除记录
    - 验证删除证明
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        contract_address: str | None = None,
        private_key: str | None = None,
        auto_connect: bool = True,
    ):
        """
        初始化合约管理器

        Args:
            rpc_url: RPC 节点 URL（默认从配置读取）
            contract_address: 合约地址（默认从配置读取）
            private_key: 私钥（默认从配置读取）
            auto_connect: 是否自动连接区块链
        """
        self.rpc_url = rpc_url or BlockchainConfig.get_rpc_url()
        self.contract_address = contract_address or BlockchainConfig.CONTRACT_ADDRESS
        self.private_key = private_key or BlockchainConfig.WALLET_PRIVATE_KEY

        # Web3 和合约实例
        self.w3: Web3 | None = None
        self.contract: Contract | None = None
        self.account: LocalAccount | None = None

        # 连接状态
        self._is_connected = False

        if auto_connect:
            self.connect()

    def connect(self) -> None:
        """
        连接到区块链网络并加载合约

        Raises:
            ConnectionError: 连接失败
        """

        try:
            # 1. 创建 Web3 实例
            logger.info(f"Connecting to {self.rpc_url}...")
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

            # 2. 检查连接
            if not self.w3.is_connected():
                raise ConnectionError("Failed to connect to blockchain network")

            logger.info(
                f"✓ Connected to {BlockchainConfig.NETWORK} (Chain ID: {self.w3.eth.chain_id})"
            )

            # 3. 设置账户
            if not self.private_key:
                raise ConnectionError("Private key not provided")

            self.account = self.w3.eth.account.from_key(self.private_key)
            if self.account:
                logger.info(f"✓ Loaded account: {self.account.address}")

            # 4. 加载合约
            abi = BlockchainConfig.load_contract_abi()
            checksum_address = Web3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(address=checksum_address, abi=abi)
            logger.info(f"✓ Loaded contract at: {self.contract_address}")

            # 5. 验证合约
            try:
                # 尝试调用一个只读方法验证合约存在
                code = self.w3.eth.get_code(checksum_address)
                if code == b"":
                    raise ConnectionError("No contract found at the specified address")
            except Exception as e:
                raise ConnectionError(f"Failed to verify contract: {str(e)}")

            self._is_connected = True
            logger.info("✓ Contract manager initialized successfully")

        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Failed to connect: {str(e)}")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected and self.w3 is not None and self.w3.is_connected()

    def get_balance(self, address: str | None = None) -> float:
        """
        获取账户余额

        Args:
            address: 账户地址（默认为当前账户）

        Returns:
            float: 余额（单位：ETH）
        """
        if not self.is_connected() or self.w3 is None or self.account is None:
            raise ConnectionError("Not connected to blockchain")

        addr = address or self.account.address
        checksum_addr = Web3.to_checksum_address(addr)
        balance_wei: Wei = self.w3.eth.get_balance(checksum_addr)
        balance_eth: int | Decimal = self.w3.from_wei(balance_wei, "ether")

        # 转换为 float
        if isinstance(balance_eth, Decimal):
            return float(balance_eth)
        return float(balance_eth)

    def record_deletion(
        self,
        key_id: str,
        destruction_method: str,
        proof_hash: str,
        wait_for_confirmation: bool = True,
    ) -> Dict[str, Any]:
        """
        记录密钥删除操作到区块链

        Args:
            key_id: 密钥 ID
            destruction_method: 销毁方法（如 "ctypes_secure"）
            proof_hash: 删除证明的哈希值（32字节）
            wait_for_confirmation: 是否等待交易确认

        Returns:
            dict: 交易信息
                - tx_hash: 交易哈希
                - block_number: 区块号（如果已确认）
                - gas_used: 使用的 gas（如果已确认）
                - status: 交易状态

        Raises:
            TransactionError: 交易失败
        """
        if (
            not self.is_connected()
            or self.w3 is None
            or self.contract is None
            or self.account is None
        ):
            raise ConnectionError("Not connected to blockchain")

        try:
            logger.info(f"Recording deletion for key: {key_id}")

            # 1. 构建交易
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            # 确保 proof_hash 是正确的格式（bytes32）
            if isinstance(proof_hash, str):
                if proof_hash.startswith("0x"):
                    proof_hash_bytes = bytes.fromhex(proof_hash[2:])
                else:
                    proof_hash_bytes = bytes.fromhex(proof_hash)
            else:
                proof_hash_bytes = proof_hash

            # 调用合约函数
            transaction = self.contract.functions.recordDeletion(
                key_id, destruction_method, proof_hash_bytes
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "gas": BlockchainConfig.GAS_LIMIT,
                    "maxFeePerGas": Web3.to_wei(BlockchainConfig.MAX_FEE, "gwei"),
                    "maxPriorityFeePerGas": Web3.to_wei(
                        BlockchainConfig.MAX_PRIORITY_FEE, "gwei"
                    ),
                    "chainId": self.w3.eth.chain_id,
                }
            )

            # 2. 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, private_key=self.private_key
            )

            # 3. 发送交易
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"✓ Transaction sent: {tx_hash_hex}")
            logger.info(
                f"  View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash_hex}"
            )

            result: Dict[str, Any] = {
                "tx_hash": tx_hash_hex,
                "key_id": key_id,
                "method": destruction_method,
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
            }

            # 4. 等待确认（可选）
            if wait_for_confirmation:
                logger.info("Waiting for transaction confirmation...")
                receipt = self._wait_for_transaction_receipt(
                    tx_hash, timeout=BlockchainConfig.TRANSACTION_TIMEOUT
                )

                result.update(
                    {
                        "block_number": int(receipt["blockNumber"]),
                        "gas_used": int(receipt["gasUsed"]),
                        "status": "success" if receipt["status"] == 1 else "failed",
                    }
                )

                if receipt["status"] == 1:
                    logger.info(
                        f"✓ Transaction confirmed in block {receipt['blockNumber']}"
                    )
                else:
                    raise TransactionError("Transaction failed on-chain")

            return result

        except Exception as e:
            logger.error(f"Failed to record deletion: {str(e)}")
            raise TransactionError(f"Failed to record deletion: {str(e)}")

    def batch_record_deletion(
        self, deletions: List[Dict[str, str]], wait_for_confirmation: bool = True
    ) -> Dict[str, Any]:
        """
        批量记录删除操作（节省 gas）

        Args:
            deletions: 删除记录列表，每个元素包含：
                - key_id: 密钥 ID
                - destruction_method: 销毁方法
                - proof_hash: 证明哈希
            wait_for_confirmation: 是否等待确认

        Returns:
            dict: 批量交易信息
        """
        if (
            not self.is_connected()
            or self.w3 is None
            or self.contract is None
            or self.account is None
        ):
            raise ConnectionError("Not connected to blockchain")

        try:
            logger.info(f"Recording batch deletion for {len(deletions)} keys")

            # 准备参数
            key_ids = [d["key_id"] for d in deletions]
            methods = [d["destruction_method"] for d in deletions]
            proof_hashes = [
                (
                    bytes.fromhex(d["proof_hash"][2:])
                    if d["proof_hash"].startswith("0x")
                    else bytes.fromhex(d["proof_hash"])
                )
                for d in deletions
            ]

            # 构建并发送交易
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            transaction = self.contract.functions.batchRecordDeletion(
                key_ids, methods, proof_hashes
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "gas": BlockchainConfig.GAS_LIMIT * len(deletions),  # 根据数量调整
                    "maxFeePerGas": Web3.to_wei(BlockchainConfig.MAX_FEE, "gwei"),
                    "maxPriorityFeePerGas": Web3.to_wei(
                        BlockchainConfig.MAX_PRIORITY_FEE, "gwei"
                    ),
                    "chainId": self.w3.eth.chain_id,
                }
            )

            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, self.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"✓ Batch transaction sent: {tx_hash_hex}")

            result = {
                "tx_hash": tx_hash_hex,
                "count": len(deletions),
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
            }

            if wait_for_confirmation:
                receipt = self._wait_for_transaction_receipt(tx_hash)
                result.update(
                    {
                        "block_number": int(receipt["blockNumber"]),
                        "gas_used": int(receipt["gasUsed"]),
                        "status": "success" if receipt["status"] == 1 else "failed",
                    }
                )

            return result

        except Exception as e:
            raise TransactionError(f"Batch deletion failed: {str(e)}")

    def get_deletion_record(self, key_id: str) -> Dict[str, Any] | None:
        """
        查询删除记录

        Args:
            key_id: 密钥 ID

        Returns:
            dict: 删除记录，如果不存在返回 None
                - key_id: 密钥 ID
                - destruction_method: 销毁方法
                - timestamp: 时间戳
                - operator: 操作者地址
                - proof_hash: 证明哈希
                - exists: 是否存在（始终为 True，因为能查到就是存在）
        """
        if not self.is_connected() or self.contract is None:
            raise ConnectionError("Not connected to blockchain")

        try:
            # 合约返回 list[str, str, int, str, bytes] - 5个元素
            record = self.contract.functions.getDeletionRecord(key_id).call()

            if not record or len(record) < 5:
                return None

            return {
                "key_id": str(record[0]),
                "destruction_method": str(record[1]),
                "timestamp": int(record[2]),
                "timestamp_readable": datetime.fromtimestamp(
                    int(record[2])
                ).isoformat(),
                "operator": str(record[3]),
                "proof_hash": (
                    record[4].hex() if isinstance(record[4], bytes) else str(record[4])
                ),
                "exists": True,
            }

        except ContractLogicError as e:
            # 合约逻辑错误（如记录不存在）
            if "does not exist" in str(e):
                return None
            raise ContractManagerError(f"Contract error: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to get deletion record: {str(e)}")
            raise ContractManagerError(f"Failed to query record: {str(e)}")

    def is_key_deleted(self, key_id: str) -> bool:
        """
        检查密钥是否已删除

        Args:
            key_id: 密钥 ID

        Returns:
            bool: 是否已删除
        """
        if not self.is_connected() or self.contract is None:
            raise ConnectionError("Not connected to blockchain")

        try:
            return self.contract.functions.isKeyDeleted(key_id).call()
        except Exception as e:
            logger.error(f"Failed to check deletion status: {str(e)}")
            return False

    def verify_deletion_proof(
        self, key_id: str, destruction_method: str, proof_hash: str
    ) -> bool:
        """
        验证删除证明

        Args:
            key_id: 密钥 ID
            destruction_method: 销毁方法（注意：合约可能不需要这个参数）
            proof_hash: 证明哈希

        Returns:
            bool: 证明是否有效
        """
        if not self.is_connected() or self.contract is None:
            raise ConnectionError("Not connected to blockchain")

        try:
            # 转换 proof_hash 格式为 bytes32
            if isinstance(proof_hash, str):
                if proof_hash.startswith("0x"):
                    proof_hash_bytes = bytes.fromhex(proof_hash[2:])
                else:
                    proof_hash_bytes = bytes.fromhex(proof_hash)
            else:
                proof_hash_bytes = proof_hash

            # 确保是 32 字节
            if len(proof_hash_bytes) != 32:
                # 如果不足32字节，用0填充；如果超过32字节，截断
                proof_hash_bytes = proof_hash_bytes.ljust(32, b"\x00")[:32]

            # 合约只需要 keyId 和 proofHash 两个参数
            return self.contract.functions.verifyDeletionProof(
                key_id, proof_hash_bytes
            ).call()

        except Exception as e:
            logger.error(f"Failed to verify proof: {str(e)}")
            return False

    def _wait_for_transaction_receipt(
        self, tx_hash: bytes, timeout: int = 120, poll_interval: float = 2.0
    ) -> TxReceipt:
        """
        等待交易确认并返回收据

        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            TxReceipt: 交易收据

        Raises:
            TimeExhausted: 超时
            TransactionNotFound: 交易未找到
        """
        if self.w3 is None:
            raise ConnectionError("Not connected to blockchain")

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                HexBytes(tx_hash), timeout=timeout, poll_latency=poll_interval
            )
            return receipt
        except TimeExhausted:
            raise TransactionError(
                f"Transaction confirmation timed out after {timeout}s"
            )
        except TransactionNotFound:
            raise TransactionError("Transaction not found on blockchain")

    def get_transaction_receipt(self, tx_hash: str) -> dict | None:
        """
        获取交易收据

        Args:
            tx_hash: 交易哈希

        Returns:
            dict: 交易收据，如果未找到返回 None
        """
        if not self.is_connected() or self.w3 is None:
            raise ConnectionError("Not connected to blockchain")

        try:
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash

            receipt = self.w3.eth.get_transaction_receipt(HexBytes(tx_hash))
            return dict(receipt)
        except TransactionNotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get transaction receipt: {str(e)}")
            return None

    def disconnect(self) -> None:
        """断开连接"""
        self._is_connected = False
        self.w3 = None
        self.contract = None
        logger.info("Disconnected from blockchain")

    def __enter__(self):
        """上下文管理器入口"""
        if not self.is_connected():
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
        return False


# 便捷函数
def quick_record_deletion(key_id: str, method: str, proof_hash: str) -> str:
    """
    快速记录删除（便捷函数）

    Args:
        key_id: 密钥 ID
        method: 销毁方法
        proof_hash: 证明哈希

    Returns:
        str: 交易哈希
    """
    with ContractManager() as manager:
        result = manager.record_deletion(key_id, method, proof_hash)
        return result["tx_hash"]


def quick_check_deletion(key_id: str) -> bool:
    """
    快速检查删除状态（便捷函数）

    Args:
        key_id: 密钥 ID

    Returns:
        bool: 是否已删除
    """
    with ContractManager() as manager:
        return manager.is_key_deleted(key_id)
