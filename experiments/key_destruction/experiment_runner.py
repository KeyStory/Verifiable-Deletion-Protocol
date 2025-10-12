"""
密钥销毁实验运行器

执行规模化重复实验：
- 每种销毁方法重复30次
- 记录详细数据
- 保存到CSV文件
- 用于统计分析

使用方法：
    python -m experiments.key_destruction.experiment_runner
"""

import os
import sys
import csv
import time
import gc
from pathlib import Path
from datetime import datetime
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kms import (
    KeyManagementService,
    DestructionMethod,
)


class ExperimentRunner:
    """实验运行器类"""

    def __init__(self, output_dir: str = "experiments/key_destruction/results"):
        """
        初始化实验运行器

        Args:
            output_dir: 结果输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 测试模式（32字节，符合AES-256）
        self.test_pattern = b"SECRET_KEY_ABCD_1234567890123456"
        assert len(self.test_pattern) == 32

        # 实验参数
        self.num_trials = 30  # 每种方法重复30次

        # 所有销毁方法
        self.methods = [
            DestructionMethod.SIMPLE_DEL,
            DestructionMethod.SINGLE_OVERWRITE,
            DestructionMethod.DOD_OVERWRITE,
            DestructionMethod.CTYPES_SECURE,
        ]

    def run_single_trial(
        self, method: DestructionMethod, trial_num: int
    ) -> dict[str, Any]:
        """
        运行单次实验

        Args:
            method: 销毁方法
            trial_num: 实验编号

        Returns:
            实验结果字典
        """
        # 创建新的KMS实例（避免状态污染）
        kms = KeyManagementService()

        # 记录开始时间
        start_time = time.perf_counter()

        # 1. 生成密钥
        key_id = kms.generate_key(
            key_size=32,
            algorithm="AES-256-GCM",
            purpose=f"experiment_trial_{trial_num}",
        )

        # 2. 替换为测试模式
        key = kms.get_key(key_id)
        key._key_data = bytearray(self.test_pattern)

        # 3. 保存销毁前的引用
        data_ref = key._key_data

        # 4. 记录销毁前状态
        before_matches = bytes(data_ref) == self.test_pattern
        before_hash = hash(bytes(data_ref))

        # 5. 执行销毁
        destroy_start = time.perf_counter()
        destroy_success = kms.destroy_key(key_id, method)
        destroy_time = time.perf_counter() - destroy_start

        # 强制垃圾回收
        gc.collect()

        # 6. 记录销毁后状态
        after_data = bytes(data_ref)
        after_matches = after_data == self.test_pattern
        after_all_zeros = all(b == 0 for b in data_ref)
        after_unique_bytes = len(set(data_ref))

        # 7. 计算可恢复字节数
        if after_matches:
            recoverable_bytes = 32  # 完全可恢复
        else:
            # 计算有多少字节与原模式相同
            recoverable_bytes = sum(
                1 for i in range(len(data_ref)) if data_ref[i] == self.test_pattern[i]
            )

        # 8. 总时间
        total_time = time.perf_counter() - start_time

        # 9. 构建结果
        result = {
            "trial_num": trial_num,
            "method": method.value,
            "destroy_success": destroy_success,
            "before_matches": before_matches,
            "after_matches": after_matches,
            "after_all_zeros": after_all_zeros,
            "unique_bytes": after_unique_bytes,
            "recoverable_bytes": recoverable_bytes,
            "destroy_time_ms": destroy_time * 1000,  # 转为毫秒
            "total_time_ms": total_time * 1000,
            "timestamp": datetime.now().isoformat(),
        }

        return result

    def run_method_experiments(self, method: DestructionMethod) -> list[dict[str, Any]]:
        """
        对单个方法运行所有实验

        Args:
            method: 销毁方法

        Returns:
            实验结果列表
        """
        print(f"\n{'='*70}")
        print(f"测试方法: {method.value}")
        print(f"{'='*70}")
        print(f"运行 {self.num_trials} 次重复实验...\n")

        results = []

        for i in range(1, self.num_trials + 1):
            try:
                # 显示进度
                if i % 5 == 0 or i == 1:
                    print(f"  进度: {i}/{self.num_trials} ({i*100//self.num_trials}%)")

                # 运行单次实验
                result = self.run_single_trial(method, i)
                results.append(result)

            except Exception as e:
                print(f"  ❌ Trial {i} 失败: {e}")
                # 记录失败
                results.append(
                    {
                        "trial_num": i,
                        "method": method.value,
                        "destroy_success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 统计
        successful = sum(1 for r in results if r.get("destroy_success", False))
        print(f"\n  ✅ 成功: {successful}/{self.num_trials}")

        if successful > 0:
            avg_recoverable = (
                sum(r.get("recoverable_bytes", 0) for r in results) / successful
            )
            print(f"  📊 平均可恢复字节: {avg_recoverable:.2f}/32")

        return results

    def save_results_to_csv(self, all_results: list[dict[str, Any]], filename: str):
        """
        保存结果到CSV文件

        Args:
            all_results: 所有实验结果
            filename: 输出文件名
        """
        output_file = self.output_dir / filename

        if not all_results:
            print(f"⚠️  没有结果可保存")
            return

        # CSV字段
        fieldnames = [
            "trial_num",
            "method",
            "destroy_success",
            "before_matches",
            "after_matches",
            "after_all_zeros",
            "unique_bytes",
            "recoverable_bytes",
            "destroy_time_ms",
            "total_time_ms",
            "timestamp",
        ]

        try:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_results)

            print(f"\n✅ 结果已保存到: {output_file}")
            print(f"   共 {len(all_results)} 条记录")

        except Exception as e:
            print(f"❌ 保存失败: {e}")

    def print_summary(self, all_results: list[dict[str, Any]]):
        """
        打印实验总结

        Args:
            all_results: 所有实验结果
        """
        print("\n" + "=" * 70)
        print("实验总结")
        print("=" * 70)

        # 按方法分组
        by_method: dict[str, list[dict]] = {}
        for r in all_results:
            method = r.get("method", "unknown")
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(r)

        # 表头
        print(
            f"\n{'方法':<20} {'成功率':<10} {'平均可恢复':<12} {'最小':<6} {'最大':<6} {'标准差':<8}"
        )
        print("-" * 70)

        # 统计每种方法
        for method, results in sorted(by_method.items()):
            successful = [r for r in results if r.get("destroy_success", False)]
            success_rate = len(successful) / len(results) * 100 if results else 0

            if successful:
                recoverable_list = [r.get("recoverable_bytes", 0) for r in successful]
                avg = sum(recoverable_list) / len(recoverable_list)
                min_val = min(recoverable_list)
                max_val = max(recoverable_list)

                # 计算标准差
                if len(recoverable_list) > 1:
                    variance = sum((x - avg) ** 2 for x in recoverable_list) / (
                        len(recoverable_list) - 1
                    )
                    std_dev = variance**0.5
                else:
                    std_dev = 0.0

                print(
                    f"{method:<20} {success_rate:.1f}%     {avg:.2f}/32      {min_val:<6} {max_val:<6} {std_dev:.2f}"
                )
            else:
                print(
                    f"{method:<20} {success_rate:.1f}%     N/A          N/A    N/A    N/A"
                )

        # 关键发现
        print("\n📊 关键发现:")

        for method, results in sorted(by_method.items()):
            successful = [r for r in results if r.get("destroy_success", False)]
            if successful:
                avg_recoverable = sum(
                    r.get("recoverable_bytes", 0) for r in successful
                ) / len(successful)

                if avg_recoverable == 0:
                    print(f"   ✅ {method}: 完全安全（0字节可恢复）")
                elif avg_recoverable == 32:
                    print(f"   ❌ {method}: 完全不安全（32字节可恢复）")
                else:
                    print(
                        f"   ⚠️  {method}: 部分安全（平均{avg_recoverable:.1f}字节可恢复）"
                    )

    def run_all_experiments(self):
        """运行所有实验"""
        print("=" * 70)
        print("密钥销毁实验 - 规模化测试")
        print("=" * 70)

        print(f"\n📋 实验配置:")
        print(f"   销毁方法数: {len(self.methods)}")
        print(f"   每种方法重复次数: {self.num_trials}")
        print(f"   总实验次数: {len(self.methods) * self.num_trials}")
        print(f"   测试模式长度: {len(self.test_pattern)} 字节")

        all_results = []

        # 对每种方法运行实验
        for method in self.methods:
            results = self.run_method_experiments(method)
            all_results.extend(results)

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"experiment_results_{timestamp}.csv"
        self.save_results_to_csv(all_results, filename)

        # 打印总结
        self.print_summary(all_results)

        print("\n" + "=" * 70)
        print("✅ 实验完成！")
        print("=" * 70)

        print(f"\n📁 结果文件位置:")
        print(f"   {self.output_dir / filename}")

        print(f"\n💡 下一步:")
        print(f"   1. 使用 data_analyzer.py 分析数据")
        print(f"   2. 使用 report_generator.py 生成报告")

        return all_results


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="密钥销毁实验运行器")
    parser.add_argument(
        "--trials", type=int, default=30, help="每种方法的重复次数（默认30）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/key_destruction/results",
        help="结果输出目录",
    )

    args = parser.parse_args()

    # 创建运行器
    runner = ExperimentRunner(output_dir=args.output_dir)
    runner.num_trials = args.trials

    # 运行实验
    start_time = time.time()
    runner.run_all_experiments()
    elapsed = time.time() - start_time

    print(f"\n⏱️  总耗时: {elapsed:.2f} 秒")


if __name__ == "__main__":
    main()
