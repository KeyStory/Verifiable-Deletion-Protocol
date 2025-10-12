# Python-区块链集成使用指南

**版本**: 1.0  
**创建日期**: 2025-10-11  
**状态**: ✅ 实现完成

---

## 📋 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [核心组件](#核心组件)
4. [API 参考](#api-参考)
5. [使用示例](#使用示例)
6. [错误处理](#错误处理)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)

---

## 概述

`src/blockchain/` 模块提供了与以太坊智能合约交互的完整功能，主要用于记录和验证密钥删除操作。

### 主要功能

- ✅ 连接 Sepolia 测试网
- ✅ 记录单个/批量删除操作
- ✅ 查询链上删除记录
- ✅ 验证删除证明的有效性
- ✅ 完整的错误处理和重试机制

### 文件结构

```
src/blockchain/
├── __init__.py              # 模块导出
├── config.py                # 配置管理
└── contract_manager.py      # 合约交互核心类
```

---

## 快速开始

### 1. 环境准备

确保 `.env` 文件包含以下配置：

```bash
# Infura 配置
INFURA_PROJECT_ID=your_infura_project_id
INFURA_PROJECT_SECRET=your_infura_secret

# 网络
ETHEREUM_NETWORK=sepolia

# 钱包
WALLET_ADDRESS=0xYourAddress
WALLET_PRIVATE_KEY=0xYourPrivateKey
```

### 2. 验证配置

```python
from src.blockchain import BlockchainConfig

# 验证配置
is_valid, errors = BlockchainConfig.validate_config()
if is_valid:
    print("✓ Configuration OK")
    BlockchainConfig.print_config()
else:
    print("✗ Configuration errors:", errors)
```

### 3. 第一个交易

```python
from src.blockchain import ContractManager
import hashlib

# 连接区块链
manager = ContractManager()

# 生成测试数据
key_id = "my_first_key"
method = "ctypes_secure"
proof_hash = hashlib.sha256(b"my_proof").hexdigest()

# 记录删除
result = manager.record_deletion(
    key_id=key_id,
    destruction_method=method,
    proof_hash=proof_hash,
    wait_for_confirmation=True
)

print(f"Transaction: {result['tx_hash']}")
print(f"View on Etherscan: https://sepolia.etherscan.io/tx/{result['tx_hash']}")
```

---

## 核心组件

### BlockchainConfig

配置管理类，负责加载和验证所有配置参数。

**关键属性**:
- `CONTRACT_ADDRESS`: 合约地址（已部署）
- `NETWORK`: 网络名称（sepolia）
- `CHAIN_ID`: 链 ID（11155111）
- `ABI_PATH`: 合约 ABI 路径

**关键方法**:
```python
# 获取 RPC URL
url = BlockchainConfig.get_rpc_url()

# 加载合约 ABI
abi = BlockchainConfig.load_contract_abi()

# 验证配置
is_valid, errors = BlockchainConfig.validate_config()

# 打印配置（用于调试）
BlockchainConfig.print_config(hide_sensitive=True)
```

### ContractManager

合约交互核心类，提供所有区块链操作。

**初始化**:
```python
# 使用默认配置（自动连接）
manager = ContractManager()

# 自定义配置（不自动连接）
manager = ContractManager(
    rpc_url="https://sepolia.infura.io/v3/YOUR_ID",
    contract_address="0x...",
    private_key="0x...",
    auto_connect=False
)
manager.connect()
```

**主要方法**:
| 方法 | 功能 | 返回值 |
|------|------|--------|
| `connect()` | 连接区块链 | None |
| `is_connected()` | 检查连接状态 | bool |
| `get_balance(address)` | 查询余额 | float (ETH) |
| `record_deletion(...)` | 记录删除 | dict (交易信息) |
| `batch_record_deletion(...)` | 批量记录 | dict (交易信息) |
| `get_deletion_record(key_id)` | 查询记录 | dict or None |
| `is_key_deleted(key_id)` | 检查删除状态 | bool |
| `verify_deletion_proof(...)` | 验证证明 | bool |
| `disconnect()` | 断开连接 | None |

---

## API 参考

### record_deletion()

记录单个密钥删除操作。

**签名**:
```python
def record_deletion(
    self,
    key_id: str,
    destruction_method: str,
    proof_hash: str,
    wait_for_confirmation: bool = True
) -> Dict[str, Any]
```

**参数**:
- `key_id` (str): 密钥唯一标识符
- `destruction_method` (str): 销毁方法（如 "ctypes_secure", "dod_overwrite"）
- `proof_hash` (str): 删除证明的 SHA-256 哈希（64位十六进制字符串）
- `wait_for_confirmation` (bool): 是否等待交易确认（默认 True）

**返回值**:
```python
{
    'tx_hash': '0x123...',           # 交易哈希
    'key_id': 'my_key',              # 密钥 ID
    'method': 'ctypes_secure',       # 销毁方法
    'timestamp': '2025-10-11T...',   # 时间戳
    'status': 'success',             # 状态: 'success', 'failed', 'pending'
    'block_number': 12345,           # 区块号（如果已确认）
    'gas_used': 45678                # 使用的 gas（如果已确认）
}
```

**异常**:
- `ConnectionError`: 未连接到区块链
- `TransactionError`: 交易失败或超时

**示例**:
```python
result = manager.record_deletion(
    key_id="user_001_key",
    destruction_method="ctypes_secure",
    proof_hash="a3b2c1...",
    wait_for_confirmation=True
)
```

---

### batch_record_deletion()

批量记录删除操作（节省 gas）。

**签名**:
```python
def batch_record_deletion(
    self,
    deletions: List[Dict[str, str]],
    wait_for_confirmation: bool = True
) -> Dict[str, Any]
```

**参数**:
```python
deletions = [
    {
        'key_id': 'key_001',
        'destruction_method': 'ctypes_secure',
        'proof_hash': 'abc123...'
    },
    {
        'key_id': 'key_002',
        'destruction_method': 'dod_overwrite',
        'proof_hash': 'def456...'
    }
]
```

**返回值**:
```python
{
    'tx_hash': '0x...',
    'count': 2,                      # 批量数量
    'timestamp': '2025-10-11T...',
    'status': 'success',
    'block_number': 12345,
    'gas_used': 78900
}
```

**示例**:
```python
deletions = [
    {'key_id': 'k1', 'destruction_method': 'ctypes_secure', 'proof_hash': 'a1...'},
    {'key_id': 'k2', 'destruction_method': 'dod_overwrite', 'proof_hash': 'b2...'},
]
result = manager.batch_record_deletion(deletions)
```

---

### get_deletion_record()

查询链上删除记录。

**签名**:
```python
def get_deletion_record(self, key_id: str) -> Optional[Dict[str, Any]]
```

**返回值**:
```python
{
    'key_id': 'my_key',
    'destruction_method': 'ctypes_secure',
    'timestamp': 1633024800,                    # Unix 时间戳
    'timestamp_readable': '2025-10-11T14:30:00', # ISO 格式时间
    'operator': '0x123...',                     # 操作者地址
    'proof_hash': 'abc123...',                  # 证明哈希
    'exists': True                              # 是否存在
}
```

如果记录不存在，返回 `None`。

**示例**:
```python
record = manager.get_deletion_record("user_001_key")
if record:
    print(f"Key deleted at: {record['timestamp_readable']}")
    print(f"Method used: {record['destruction_method']}")
else:
    print("Record not found")
```

---

### is_key_deleted()

检查密钥是否已被标记为删除。

**签名**:
```python
def is_key_deleted(self, key_id: str) -> bool
```

**示例**:
```python
if manager.is_key_deleted("user_001_key"):
    print("Key has been deleted")
else:
    print("Key not deleted or doesn't exist")
```

---

### verify_deletion_proof()

验证删除证明的有效性。

**签名**:
```python
def verify_deletion_proof(
    self,
    key_id: str,
    destruction_method: str,
    proof_hash: str
) -> bool
```

**示例**:
```python
is_valid = manager.verify_deletion_proof(
    key_id="user_001_key",
    destruction_method="ctypes_secure",
    proof_hash="a3b2c1..."
)

if is_valid:
    print("✓ Proof is valid")
else:
    print("✗ Proof is invalid")
```

---

## 使用示例

### 示例 1: 完整的删除流程

```python
from src.blockchain import ContractManager
from src.kms import KeyManagementService, DestructionMethod
import hashlib

# 1. 初始化服务
kms = KeyManagementService()
manager = ContractManager()

# 2. 生成密钥
key_id = kms.generate_key(32, "AES-256-GCM")
print(f"Generated key: {key_id}")

# 3. 使用密钥（加密数据等）
# ... 业务逻辑 ...

# 4. 销毁密钥
success = kms.destroy_key(key_id, DestructionMethod.CTYPES_SECURE)
if not success:
    raise Exception("Key destruction failed")

# 5. 生成删除证明
proof_data = f"{key_id}:ctypes_secure:{kms.get_metadata(key_id)}"
proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

# 6. 记录到区块链
result = manager.record_deletion(
    key_id=key_id,
    destruction_method="ctypes_secure",
    proof_hash=proof_hash
)

print(f"✓ Deletion recorded on blockchain")
print(f"  Transaction: {result['tx_hash']}")
print(f"  Block: {result['block_number']}")

# 7. 验证删除
is_deleted = manager.is_key_deleted(key_id)
assert is_deleted, "Deletion verification failed"
```

---

### 示例 2: 使用上下文管理器

```python
from src.blockchain import ContractManager

# 自动连接和断开
with ContractManager() as manager:
    # 查询余额
    balance = manager.get_balance()
    print(f"Current balance: {balance:.4f} ETH")
    
    # 执行操作
    result = manager.record_deletion(
        key_id="test_key",
        destruction_method="dod_overwrite",
        proof_hash="abc123..."
    )
    
    print(f"Transaction: {result['tx_hash']}")

# 这里已经自动断开连接
```

---

### 示例 3: 批量删除多个用户

```python
from src.blockchain import ContractManager
import hashlib

# 准备批量删除数据
users_to_delete = ["user_001", "user_002", "user_003"]
deletions = []

for user_id in users_to_delete:
    key_id = f"{user_id}_encryption_key"
    method = "ctypes_secure"
    
    # 生成证明
    proof_data = f"{key_id}:{method}"
    proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()
    
    deletions.append({
        'key_id': key_id,
        'destruction_method': method,
        'proof_hash': proof_hash
    })

# 批量记录
with ContractManager() as manager:
    result = manager.batch_record_deletion(deletions)
    
    print(f"✓ Batch deletion recorded")
    print(f"  Count: {result['count']}")
    print(f"  Gas used: {result['gas_used']}")
    print(f"  Saved gas vs individual: ~{result['count'] * 50000 - result['gas_used']}")
```

---

### 示例 4: 查询和验证历史记录

```python
from src.blockchain import ContractManager

def audit_deletion(key_id: str):
    """审计密钥删除记录"""
    with ContractManager() as manager:
        # 查询记录
        record = manager.get_deletion_record(key_id)
        
        if not record:
            print(f"✗ No deletion record found for {key_id}")
            return False
        
        print(f"Deletion Record for {key_id}:")
        print(f"  Method: {record['destruction_method']}")
        print(f"  Time: {record['timestamp_readable']}")
        print(f"  Operator: {record['operator']}")
        print(f"  Proof: {record['proof_hash'][:16]}...")
        
        # 验证证明
        is_valid = manager.verify_deletion_proof(
            key_id=record['key_id'],
            destruction_method=record['destruction_method'],
            proof_hash=record['proof_hash']
        )
        
        if is_valid:
            print(f"  ✓ Proof verified")
            return True
        else:
            print(f"  ✗ Proof verification failed!")
            return False

# 使用
audit_deletion("user_001_key")
```

---

### 示例 5: 便捷函数（快速操作）

```python
from src.blockchain import quick_record_deletion, quick_check_deletion
import hashlib

# 快速记录删除
key_id = "quick_test_key"
proof_hash = hashlib.sha256(b"proof").hexdigest()
tx_hash = quick_record_deletion(key_id, "ctypes_secure", proof_hash)
print(f"Transaction: {tx_hash}")

# 快速检查状态
is_deleted = quick_check_deletion(key_id)
print(f"Is deleted: {is_deleted}")
```

---

## 错误处理

### 常见异常

#### ConnectionError

**原因**:
- Infura 配置错误
- 网络连接问题
- 合约地址不存在

**处理**:
```python
from src.blockchain import ContractManager, ConnectionError

try:
    manager = ContractManager()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    # 检查配置
    from src.blockchain import BlockchainConfig
    is_valid, errors = BlockchainConfig.validate_config()
    if not is_valid:
        print("Configuration errors:", errors)
```

#### TransactionError

**原因**:
- Gas 不足
- 交易超时
- 合约执行失败

**处理**:
```python
from src.blockchain import TransactionError
import time

def record_with_retry(manager, key_id, method, proof_hash, max_retries=3):
    """带重试的记录删除"""
    for attempt in range(max_retries):
        try:
            result = manager.record_deletion(
                key_id=key_id,
                destruction_method=method,
                proof_hash=proof_hash,
                wait_for_confirmation=True
            )
            return result
        except TransactionError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # 等待后重试
            else:
                raise
```

---

### 完整的错误处理示例

```python
from src.blockchain import (
    ContractManager,
    ConnectionError,
    TransactionError,
    BlockchainConfig
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_record_deletion(key_id: str, method: str, proof_hash: str):
    """安全的删除记录函数"""
    
    # 1. 验证配置
    is_valid, errors = BlockchainConfig.validate_config()
    if not is_valid:
        logger.error(f"Configuration invalid: {errors}")
        return None
    
    # 2. 连接区块链
    try:
        manager = ContractManager()
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        return None
    
    # 3. 检查余额
    try:
        balance = manager.get_balance()
        if balance < 0.01:  # 至少需要 0.01 ETH
            logger.warning(f"Low balance: {balance:.4f} ETH")
    except Exception as e:
        logger.warning(f"Could not check balance: {e}")
    
    # 4. 记录删除
    try:
        result = manager.record_deletion(
            key_id=key_id,
            destruction_method=method,
            proof_hash=proof_hash,
            wait_for_confirmation=True
        )
        
        logger.info(f"✓ Deletion recorded: {result['tx_hash']}")
        return result
        
    except TransactionError as e:
        logger.error(f"Transaction failed: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
    
    finally:
        manager.disconnect()

# 使用
result = safe_record_deletion("key_001", "ctypes_secure", "abc123...")
if result:
    print(f"Success: {result['tx_hash']}")
else:
    print("Failed to record deletion")
```

---

## 最佳实践

### 1. 使用上下文管理器

```python
# ✓ 推荐：自动管理连接
with ContractManager() as manager:
    result = manager.record_deletion(...)

# ✗ 不推荐：手动管理
manager = ContractManager()
try:
    result = manager.record_deletion(...)
finally:
    manager.disconnect()
```

### 2. 批量操作节省 Gas

```python
# ✓ 推荐：批量删除（节省 ~30-50% gas）
deletions = [...]  # 多个删除
manager.batch_record_deletion(deletions)

# ✗ 不推荐：循环单个删除
for d in deletions:
    manager.record_deletion(...)  # 每次都是独立交易
```

### 3. 合理使用 wait_for_confirmation

```python
# ✓ 关键操作：等待确认
result = manager.record_deletion(..., wait_for_confirmation=True)

# ✓ 批量操作：不等待确认，后续统一查询
result = manager.record_deletion(..., wait_for_confirmation=False)
tx_hash = result['tx_hash']
# 稍后查询
receipt = manager.get_transaction_receipt(tx_hash)
```

### 4. 错误处理和日志

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 所有操作都会自动记录日志
manager = ContractManager()  # 日志: "Connected to sepolia..."
```

### 5. 定期检查余额

```python
def check_balance_and_alert(manager, threshold=0.05):
    """检查余额并预警"""
    balance = manager.get_balance()
    if balance < threshold:
        print(f"⚠️  Low balance: {balance:.4f} ETH")
        print(f"   Get more from: https://sepoliafaucet.com/")
        return False
    return True
```

---

## 故障排除

### 问题 1: "INFURA_PROJECT_ID not found"

**原因**: `.env` 文件缺失或配置错误

**解决**:
```bash
# 检查 .env 文件
cat .env | grep INFURA

# 如果没有，添加配置
echo "INFURA_PROJECT_ID=your_project_id" >> .env
echo "WALLET_PRIVATE_KEY=0x..." >> .env
```

### 问题 2: "Contract ABI not found"

**原因**: 合约未编译

**解决**:
```bash
cd contracts
npx hardhat compile
```

### 问题 3: "Insufficient funds for gas"

**原因**: 钱包余额不足

**解决**:
1. 访问水龙头: https://sepoliafaucet.com/
2. 输入你的钱包地址
3. 等待接收测试 ETH

### 问题 4: 交易一直 pending

**原因**: Gas 设置过低或网络拥堵

**解决**:
```python
# 增加 gas 配置
BlockchainConfig.MAX_FEE = 150  # 增加到 150 Gwei
BlockchainConfig.MAX_PRIORITY_FEE = 3  # 增加优先费
```

### 问题 5: "Transaction failed on-chain"

**原因**: 合约执行失败（如重复的 key_id）

**解决**:
```python
# 检查是否已存在
if manager.is_key_deleted(key_id):
    print(f"Key {key_id} already deleted")
else:
    manager.record_deletion(...)
```

---

## 测试

### 运行单元测试

```bash
# 安装 pytest
pip install pytest pytest-cov

# 运行所有测试
pytest tests/unit/test_contract_manager.py -v

# 运行特定测试
pytest tests/unit/test_contract_manager.py::TestContractManager::test_connection -v

# 生成覆盖率报告
pytest tests/unit/test_contract_manager.py --cov=src.blockchain --cov-report=html
```

### 运行集成测试

```bash
# 完整的集成测试（需要真实区块链连接）
python scripts/test_blockchain_integration.py
```

**预期输出**:
```
======================================================================
BLOCKCHAIN INTEGRATION TEST SUITE
======================================================================

======================================================================
TEST 1: Configuration Validation
======================================================================
✓ Configuration is valid
...

======================================================================
TEST SUMMARY
======================================================================
  ✓ PASS  CONFIG
  ✓ PASS  CONNECTION
  ✓ PASS  RECORD
  ✓ PASS  QUERY
  ✓ PASS  CHECK
  ✓ PASS  VERIFY
  ✓ PASS  BATCH

Total: 7/7 tests passed

🎉 All tests passed successfully!
```

---

## 性能优化

### Gas 优化建议

| 操作 | 单次 Gas | 批量 Gas (3个) | 节省 |
|------|---------|---------------|------|
| 单个删除 | ~50,000 | N/A | - |
| 批量删除 | N/A | ~100,000 | ~33% |

**建议**: 如果需要删除 ≥3 个密钥，使用批量操作。

### 网络优化

```python
# 使用较短的超时（快速失败）
manager._wait_for_transaction_receipt(tx_hash, timeout=60)

# 异步处理（不等待确认）
result = manager.record_deletion(..., wait_for_confirmation=False)
# 继续其他操作
# 稍后检查状态
```

---

## 下一步

- [ ] 集成到 KMS 系统（自动记录删除）
- [ ] 实现数据库模块
- [ ] 创建端到端测试
- [ ] 编写性能基准测试

---

**最后更新**: 2025-10-11  
**维护者**: Project Team  
**问题反馈**: 请在项目仓库提交 Issue