"""
STRIDE威胁分析辅助工具
帮助系统化地识别威胁
"""


class STRIDEAnalyzer:
    """STRIDE分析器"""

    def __init__(self):
        self.threats = []

    def analyze_component(self, component_name, description):
        """分析单个组件的威胁"""
        print(f"\n{'=' * 70}")
        print(f"分析组件: {component_name}".center(70))
        print(f"{'=' * 70}")
        print(f"描述: {description}\n")

        stride_questions = {
            "Spoofing": [
                "是否有身份验证机制？",
                "凭证（密钥/token）是否安全存储？",
                "是否可能伪造请求来源？",
            ],
            "Tampering": [
                "数据传输是否加密？",
                "是否有完整性校验（MAC/签名）？",
                "内存数据是否可被修改？",
            ],
            "Repudiation": [
                "是否有操作日志？",
                "日志是否防篡改？",
                "是否有数字签名证明操作？",
            ],
            "Information Disclosure": [
                "敏感数据是否加密？",
                "日志是否包含敏感信息？",
                "是否存在信息泄露渠道（内存dump、错误消息）？",
            ],
            "Denial of Service": [
                "是否有速率限制？",
                "资源消耗是否可控？",
                "是否有防护措施防止资源耗尽？",
            ],
            "Elevation of Privilege": [
                "是否有权限控制？",
                "默认权限是否最小化？",
                "是否存在权限绕过漏洞？",
            ],
        }

        for threat_type, questions in stride_questions.items():
            print(f"\n【{threat_type}】")
            print("─" * 70)
            for i, question in enumerate(questions, 1):
                print(f"  {i}. {question}")

        print(f"\n{'=' * 70}\n")

    def add_threat(
        self, threat_id, category, description, likelihood, impact, mitigation
    ):
        """添加识别的威胁"""
        self.threats.append(
            {
                "id": threat_id,
                "category": category,
                "description": description,
                "likelihood": likelihood,  # 低/中/高
                "impact": impact,  # 低/中/高/极高
                "mitigation": mitigation,
            }
        )

    def generate_report(self):
        """生成威胁报告"""
        print("=" * 70)
        print("威胁分析报告".center(70))
        print("=" * 70)

        # 按优先级排序
        priority_map = {
            ("高", "极高"): "P0",
            ("高", "高"): "P0",
            ("中", "极高"): "P1",
            ("中", "高"): "P1",
            ("低", "极高"): "P1",
            ("高", "中"): "P2",
            ("中", "中"): "P2",
            ("低", "高"): "P2",
        }

        for threat in self.threats:
            priority = priority_map.get((threat["likelihood"], threat["impact"]), "P3")

            print(f"\n威胁ID: {threat['id']}")
            print(f"类别: {threat['category']}")
            print(f"优先级: {priority}")
            print(f"描述: {threat['description']}")
            print(f"可能性: {threat['likelihood']} | 影响: {threat['impact']}")
            print(f"缓解措施: {threat['mitigation']}")
            print("─" * 70)


def main():
    """主函数：分析各个组件"""
    analyzer = STRIDEAnalyzer()

    # 分析各个组件
    components = [
        ("API服务层", "接收用户请求，协调各组件操作"),
        ("KMS（密钥管理服务）", "管理密钥的生成、存储、销毁"),
        ("区块链存证层", "在以太坊上存储不可篡改的删除证明"),
        ("数据存储层", "存储加密的用户数据"),
    ]

    for name, desc in components:
        analyzer.analyze_component(name, desc)
        input("按Enter继续分析下一个组件...")

    print("\n提示：请根据上述问题，在威胁模型文档中详细记录识别的威胁。")


if __name__ == "__main__":
    main()
