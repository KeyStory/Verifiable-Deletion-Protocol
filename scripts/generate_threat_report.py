"""
威胁报告生成工具
自动从威胁模型生成格式化报告
"""

import json
from datetime import datetime


class ThreatReport:
    """威胁报告生成器"""

    def __init__(self):
        self.threats = []
        self.project_name = "可验证删除协议"
        self.version = "1.0"
        self.date = datetime.now().strftime("%Y-%m-%d")

    def add_threat(self, threat_data):
        """添加威胁"""
        self.threats.append(threat_data)

    def generate_markdown_report(self, output_file):
        """生成Markdown格式报告"""

        with open(output_file, "w", encoding="utf-8") as f:
            # 标题
            f.write(f"# {self.project_name} - 威胁分析报告\n\n")
            f.write(f"**版本**: {self.version}  \n")
            f.write(f"**日期**: {self.date}\n\n")

            # 执行摘要
            f.write("## 执行摘要\n\n")
            total = len(self.threats)
            p0 = sum(1 for t in self.threats if t.get("priority") == "P0")
            p1 = sum(1 for t in self.threats if t.get("priority") == "P1")

            f.write(f"本报告识别了**{total}个威胁**，其中：\n")
            f.write(f"- **P0（极高优先级）**: {p0}个\n")
            f.write(f"- **P1（高优先级）**: {p1}个\n")
            f.write(f"- **P2/P3**: {total - p0 - p1}个\n\n")

            # 按优先级排序
            sorted_threats = sorted(
                self.threats,
                key=lambda t: ("P0", "P1", "P2", "P3").index(t.get("priority", "P3")),
            )

            # 详细威胁列表
            f.write("## 威胁详情\n\n")

            for threat in sorted_threats:
                f.write(f"### {threat['id']}: {threat['name']}\n\n")
                f.write(f"**优先级**: {threat['priority']}  \n")
                f.write(f"**类别**: {threat['category']}  \n")
                f.write(f"**可能性**: {threat['likelihood']}  \n")
                f.write(f"**影响**: {threat['impact']}  \n\n")

                f.write(f"**描述**:  \n{threat['description']}\n\n")

                if "mitigation" in threat:
                    f.write(f"**缓解措施**:  \n{threat['mitigation']}\n\n")

                f.write("---\n\n")

        print(f"✅ 报告已生成: {output_file}")


# 使用示例
def example_usage():
    report = ThreatReport()

    # 添加威胁
    report.add_threat(
        {
            "id": "T-I-001",
            "name": "密钥销毁后内存残留",
            "priority": "P0",
            "category": "Information Disclosure",
            "likelihood": "高",
            "impact": "极高",
            "description": "KMS销毁密钥后，内存中可能仍有残留数据...",
            "mitigation": "使用多次覆写方法，结合ctypes直接操作内存...",
        }
    )

    # 生成报告
    report.generate_markdown_report("threat-report-generated.md")


if __name__ == "__main__":
    example_usage()
