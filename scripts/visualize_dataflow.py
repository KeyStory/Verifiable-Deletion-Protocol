"""
数据流可视化工具
帮助理解系统中数据如何流动
"""


def visualize_deletion_flow():
    """可视化删除操作的数据流"""

    print("=" * 70)
    print("可验证删除协议 - 数据流分析".center(70))
    print("=" * 70)

    steps = [
        {
            "step": 1,
            "action": "用户发起删除请求",
            "data": "user_id, session_token",
            "component": "API Gateway",
            "security": "验证session_token，确认用户身份",
        },
        {
            "step": 2,
            "action": "API验证用户权限",
            "data": "user_id, permissions",
            "component": "API Service",
            "security": "检查用户是否有权删除自己的数据",
        },
        {
            "step": 3,
            "action": "调用KMS销毁密钥",
            "data": "user_id → 查询密钥 → 销毁",
            "component": "KMS",
            "security": "⚠️ 关键步骤：密钥必须彻底从内存中清除",
        },
        {
            "step": 4,
            "action": "生成删除证明",
            "data": "hash(user_id + timestamp + operation)",
            "component": "API Service",
            "security": "使用加密哈希保证唯一性和不可伪造",
        },
        {
            "step": 5,
            "action": "调用智能合约",
            "data": "proof_hash, timestamp",
            "component": "Blockchain Layer",
            "security": "签名验证，防止未授权存证",
        },
        {
            "step": 6,
            "action": "等待区块链确认",
            "data": "transaction_hash",
            "component": "Ethereum Network",
            "security": "等待足够的区块确认（建议6个）",
        },
        {
            "step": 7,
            "action": "返回结果给用户",
            "data": "tx_hash, block_number, status",
            "component": "API Service",
            "security": "记录操作日志，提供审计线索",
        },
    ]

    for step_info in steps:
        print(f"\n{'─' * 70}")
        print(f"步骤 {step_info['step']}: {step_info['action']}")
        print(f"{'─' * 70}")
        print(f"数据: {step_info['data']}")
        print(f"组件: {step_info['component']}")
        print(f"安全考虑: {step_info['security']}")

    print("\n" + "=" * 70)
    print("关键观察".center(70))
    print("=" * 70)
    print(
        """
1. 密钥流动路径：
   KMS内存 → [销毁操作] → 不再存在
   ⚠️ 如果内存中残留，整个协议失效

2. 信任链：
   用户 → API → KMS → 区块链
   每一跳都需要验证和审计

3. 攻击面：
   - API层：身份伪造、重放攻击
   - KMS层：密钥残留、内存dump
   - 区块链层：Gas耗尽、合约漏洞
    """
    )
    print("=" * 70)


if __name__ == "__main__":
    visualize_deletion_flow()
