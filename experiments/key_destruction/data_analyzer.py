"""
实验数据分析器

功能：
1. 读取实验CSV文件
2. 计算描述性统计
3. 执行ANOVA检验
4. 生成可视化图表
5. 输出分析报告

使用方法：
    python -m experiments.key_destruction.data_analyzer <csv_file>
"""

import sys
import csv
import json
from pathlib import Path
from typing import Any
from collections import defaultdict
import math

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class DataAnalyzer:
    """数据分析器类"""

    def __init__(self, csv_file: str):
        """
        初始化分析器

        Args:
            csv_file: CSV文件路径
        """
        self.csv_file = Path(csv_file)
        self.data: list[dict[str, Any]] = []
        self.by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def load_data(self):
        """加载CSV数据"""
        print(f"📂 加载数据: {self.csv_file}")

        try:
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 转换数据类型
                    processed_row = {
                        "trial_num": int(row["trial_num"]),
                        "method": row["method"],
                        "destroy_success": row["destroy_success"].lower() == "true",
                        "recoverable_bytes": int(row["recoverable_bytes"]),
                        "destroy_time_ms": float(row["destroy_time_ms"]),
                        "total_time_ms": float(row["total_time_ms"]),
                        "unique_bytes": int(row.get("unique_bytes", 0)),
                        "after_all_zeros": row.get("after_all_zeros", "false").lower()
                        == "true",
                    }
                    self.data.append(processed_row)
                    self.by_method[processed_row["method"]].append(processed_row)

            print(f"   ✅ 加载 {len(self.data)} 条记录")
            print(f"   ✅ 检测到 {len(self.by_method)} 种方法\n")

        except Exception as e:
            print(f"   ❌ 加载失败: {e}")
            sys.exit(1)

    def calculate_statistics(self, values: list[float]) -> dict[str, float]:
        """
        计算描述性统计

        Args:
            values: 数值列表

        Returns:
            统计结果字典
        """
        n = len(values)
        if n == 0:
            return {
                "count": 0,
                "mean": 0,
                "std": 0,
                "min": 0,
                "max": 0,
                "median": 0,
            }

        # 均值
        mean = sum(values) / n

        # 标准差
        if n > 1:
            variance = sum((x - mean) ** 2 for x in values) / (n - 1)
            std = math.sqrt(variance)
        else:
            std = 0.0

        # 最小最大
        min_val = min(values)
        max_val = max(values)

        # 中位数
        sorted_values = sorted(values)
        if n % 2 == 0:
            median = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            median = sorted_values[n // 2]

        return {
            "count": n,
            "mean": mean,
            "std": std,
            "min": min_val,
            "max": max_val,
            "median": median,
        }

    def descriptive_statistics(self):
        """计算并显示描述性统计"""
        print("=" * 70)
        print("描述性统计")
        print("=" * 70)

        print(
            f"\n{'方法':<20} {'N':<6} {'均值':<10} {'标准差':<10} {'最小':<8} {'最大':<8} {'中位数':<8}"
        )
        print("-" * 70)

        results = {}

        for method, records in sorted(self.by_method.items()):
            # 提取可恢复字节数
            recoverable = [r["recoverable_bytes"] for r in records]
            stats = self.calculate_statistics(recoverable)

            results[method] = stats

            print(
                f"{method:<20} {stats['count']:<6} "
                f"{stats['mean']:<10.2f} {stats['std']:<10.2f} "
                f"{stats['min']:<8.0f} {stats['max']:<8.0f} "
                f"{stats['median']:<8.2f}"
            )

        return results

    def performance_statistics(self):
        """性能统计"""
        print("\n" + "=" * 70)
        print("性能统计")
        print("=" * 70)

        print(f"\n{'方法':<20} {'平均销毁时间(ms)':<20} {'平均总时间(ms)':<20}")
        print("-" * 70)

        for method, records in sorted(self.by_method.items()):
            destroy_times = [r["destroy_time_ms"] for r in records]
            total_times = [r["total_time_ms"] for r in records]

            avg_destroy = sum(destroy_times) / len(destroy_times)
            avg_total = sum(total_times) / len(total_times)

            print(f"{method:<20} {avg_destroy:<20.4f} {avg_total:<20.4f}")

    def anova_test(self, stats_by_method: dict):
        """
        单因素ANOVA检验（简化版）

        Args:
            stats_by_method: 各方法的统计结果
        """
        print("\n" + "=" * 70)
        print("ANOVA 检验（方差分析）")
        print("=" * 70)

        # 计算总均值
        all_values = []
        for method, records in self.by_method.items():
            all_values.extend([r["recoverable_bytes"] for r in records])

        grand_mean = sum(all_values) / len(all_values)

        # 计算组间平方和 (SSB)
        ssb = 0
        for method, stats in stats_by_method.items():
            n = stats["count"]
            group_mean = stats["mean"]
            ssb += n * (group_mean - grand_mean) ** 2

        # 计算组内平方和 (SSW)
        ssw = 0
        for method, records in self.by_method.items():
            for record in records:
                value = record["recoverable_bytes"]
                group_mean = stats_by_method[method]["mean"]
                ssw += (value - group_mean) ** 2

        # 自由度
        k = len(self.by_method)  # 组数
        n = len(all_values)  # 总样本数
        df_between = k - 1
        df_within = n - k

        # 均方
        msb = ssb / df_between if df_between > 0 else 0
        msw = ssw / df_within if df_within > 0 else 0

        # F统计量
        f_statistic = msb / msw if msw > 0 else float("inf")

        print(f"\n组间平方和 (SSB): {ssb:.2f}")
        print(f"组内平方和 (SSW): {ssw:.2f}")
        print(f"总平方和 (SST): {ssb + ssw:.2f}")
        print(f"\n自由度 (组间): {df_between}")
        print(f"自由度 (组内): {df_within}")
        print(f"\n均方 (MSB): {msb:.2f}")
        print(f"均方 (MSW): {msw:.2f}")
        print(f"\nF统计量: {f_statistic:.2f}")

        # 临界值参考（简化）
        print(f"\n💡 解释:")
        if f_statistic > 10:
            print(f"   F值 > 10: 组间差异极显著 (p < 0.001)")
            print(f"   结论: 不同销毁方法的安全性存在极显著差异")
        elif f_statistic > 5:
            print(f"   F值 > 5: 组间差异显著 (p < 0.01)")
            print(f"   结论: 不同销毁方法的安全性存在显著差异")
        elif f_statistic > 3:
            print(f"   F值 > 3: 组间有一定差异 (p < 0.05)")
        else:
            print(f"   F值 < 3: 组间差异不显著")

    def pairwise_comparison(self):
        """两两比较"""
        print("\n" + "=" * 70)
        print("两两比较（可恢复字节数）")
        print("=" * 70)

        methods = sorted(self.by_method.keys())

        print(f"\n{'方法对比':<40} {'均值差':<15} {'差异显著性'}")
        print("-" * 70)

        for i in range(len(methods)):
            for j in range(i + 1, len(methods)):
                method1 = methods[i]
                method2 = methods[j]

                values1 = [r["recoverable_bytes"] for r in self.by_method[method1]]
                values2 = [r["recoverable_bytes"] for r in self.by_method[method2]]

                mean1 = sum(values1) / len(values1)
                mean2 = sum(values2) / len(values2)
                diff = abs(mean1 - mean2)

                # 简单判断
                if diff > 10:
                    significance = "⭐⭐⭐ 极显著"
                elif diff > 1:
                    significance = "⭐⭐ 显著"
                elif diff > 0.5:
                    significance = "⭐ 可能显著"
                else:
                    significance = "无显著差异"

                comparison = f"{method1} vs {method2}"
                print(f"{comparison:<40} {diff:<15.2f} {significance}")

    def security_classification(self):
        """安全性分类"""
        print("\n" + "=" * 70)
        print("安全性分类")
        print("=" * 70)

        print(f"\n{'方法':<20} {'平均可恢复':<15} {'安全等级':<15} {'推荐度'}")
        print("-" * 70)

        for method, records in sorted(self.by_method.items()):
            recoverable = [r["recoverable_bytes"] for r in records]
            avg = sum(recoverable) / len(recoverable)
            max_val = max(recoverable)

            # 分类
            if avg == 0 and max_val == 0:
                level = "A级（完全安全）"
                recommendation = "✅✅✅ 强烈推荐"
            elif avg < 0.5 and max_val <= 1:
                level = "B级（高度安全）"
                recommendation = "✅✅ 推荐"
            elif avg < 5:
                level = "C级（基本安全）"
                recommendation = "⚠️  谨慎使用"
            else:
                level = "D级（不安全）"
                recommendation = "❌ 不推荐"

            print(f"{method:<20} {avg:.2f}/32        {level:<15} {recommendation}")

    def generate_text_report(self, output_file: str | Path):
        """生成文本分析报告"""
        report_path = Path(output_file)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("密钥销毁实验数据分析报告\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"数据文件: {self.csv_file}\n")
            f.write(f"总记录数: {len(self.data)}\n")
            f.write(f"测试方法数: {len(self.by_method)}\n\n")

            # 描述性统计
            f.write("1. 描述性统计\n")
            f.write("-" * 70 + "\n\n")

            for method, records in sorted(self.by_method.items()):
                recoverable = [r["recoverable_bytes"] for r in records]
                stats = self.calculate_statistics(recoverable)

                f.write(f"方法: {method}\n")
                f.write(f"  样本数: {stats['count']}\n")
                f.write(f"  平均可恢复字节: {stats['mean']:.2f}\n")
                f.write(f"  标准差: {stats['std']:.2f}\n")
                f.write(f"  范围: [{stats['min']}, {stats['max']}]\n")
                f.write(f"  中位数: {stats['median']:.2f}\n\n")

        print(f"\n✅ 文本报告已保存: {report_path}")

    def run_analysis(self):
        """运行完整分析"""
        print("=" * 70)
        print("实验数据分析")
        print("=" * 70)
        print()

        # 加载数据
        self.load_data()

        # 描述性统计
        stats = self.descriptive_statistics()

        # 性能统计
        self.performance_statistics()

        # ANOVA检验
        self.anova_test(stats)

        # 两两比较
        self.pairwise_comparison()

        # 安全性分类
        self.security_classification()

        # 生成报告
        output_file = self.csv_file.parent / f"analysis_report_{self.csv_file.stem}.txt"
        self.generate_text_report(output_file)

        print("\n" + "=" * 70)
        print("✅ 分析完成！")
        print("=" * 70)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实验数据分析器")
    parser.add_argument("csv_file", type=str, help="实验结果CSV文件路径")

    args = parser.parse_args()

    # 创建分析器
    analyzer = DataAnalyzer(args.csv_file)

    # 运行分析
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
