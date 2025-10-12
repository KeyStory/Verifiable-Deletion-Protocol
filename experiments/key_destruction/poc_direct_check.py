"""
密钥残留检测 - 改进版 PoC（直接内存检查）

这个版本不依赖外部工具，直接检查Python对象的内存状态。

验证方法：
1. 创建密钥，记录原始数据
2. 执行销毁操作
3. 直接检查bytearray的内容
4. 对比销毁前后的差异

使用方法：
    python -m experiments.key_destruction.poc_direct_check
"""

import os
import sys
import gc
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kms import (
    KeyManagementService,
    DestructionMethod,
)


class DirectMemoryTest:
    """直接内存检查测试类"""

    def __init__(self):
        self.test_pattern = b"SECRET_KEY_ABCD_1234567890123456"  # 32字节
        assert len(self.test_pattern) == 32, f"Pattern must be 32 bytes"

    def check_bytearray_content(self, data: bytearray, pattern: bytes) -> dict:
        """
        检查bytearray内容

        Args:
            data: 要检查的bytearray
            pattern: 原始模式

        Returns:
            检查结果字典
        """
        result = {
            "length": len(data),
            "matches_pattern": bytes(data) == pattern,
            "all_zeros": all(b == 0 for b in data),
            "is_random": False,
            "unique_bytes": len(set(data)),
            "sample": data[:16].hex() if len(data) >= 16 else data.hex(),
        }

        # 判断是否为随机数据
        if result["unique_bytes"] > 8 and not result["matches_pattern"]:
            result["is_random"] = True

        return result

    def run_single_test(self, method: DestructionMethod) -> dict:
        """
        运行单次测试

        Args:
            method: 销毁方法

        Returns:
            测试结果
        """
        print(f"\n{'='*70}")
        print(f"测试方法: {method.value}")
        print(f"{'='*70}")

        kms = KeyManagementService()

        # 1. 生成密钥
        print("\n📝 步骤1: 生成密钥")
        key_id = kms.generate_key(
            key_size=32, algorithm="AES-256-GCM", purpose="memory_test"
        )
        print(f"   ✅ 密钥ID: {key_id}")

        # 2. 获取密钥对象并替换为测试模式
        key = kms.get_key(key_id)
        key._key_data = bytearray(self.test_pattern)
        print(f"   ✅ 测试模式: {self.test_pattern.decode()}")
        print(f"   ✅ 模式长度: {len(self.test_pattern)} 字节")

        # 3. 销毁前检查
        print("\n🔍 步骤2: 销毁前检查")
        before = self.check_bytearray_content(key._key_data, self.test_pattern)
        print(f"   数据长度: {before['length']} 字节")
        print(f"   匹配原模式: {'✅ 是' if before['matches_pattern'] else '❌ 否'}")
        print(f"   数据样本: {before['sample']}")

        # 4. 执行销毁
        print(f"\n🗑️  步骤3: 执行销毁 ({method.value})")

        # 保存销毁前的引用（用于后续检查）
        data_ref = key._key_data

        success = kms.destroy_key(key_id, method)
        print(f"   销毁状态: {'✅ 成功' if success else '❌ 失败'}")

        # 强制垃圾回收
        gc.collect()

        # 5. 销毁后检查
        print("\n🔍 步骤4: 销毁后检查")

        # 检查原始引用的数据
        after = self.check_bytearray_content(data_ref, self.test_pattern)
        print(f"   数据长度: {after['length']} 字节")
        print(
            f"   匹配原模式: {'❌ 是（未销毁）' if after['matches_pattern'] else '✅ 否（已改变）'}"
        )
        print(f"   全部为0: {'✅ 是' if after['all_zeros'] else '❌ 否'}")
        print(f"   疑似随机数据: {'✅ 是' if after['is_random'] else '❌ 否'}")
        print(f"   唯一字节数: {after['unique_bytes']}")
        print(f"   数据样本: {after['sample']}")

        # 6. 安全性分析
        print("\n📊 步骤5: 安全性分析")

        if after["matches_pattern"]:
            security_level = "❌ 不安全"
            reason = "数据完全可恢复"
            recoverable_bytes = 32
        elif after["all_zeros"]:
            security_level = "✅ 安全"
            reason = "数据已清零"
            recoverable_bytes = 0
        elif after["is_random"]:
            security_level = "✅ 安全"
            reason = "数据已随机覆写"
            recoverable_bytes = 0
        else:
            security_level = "⚠️  部分安全"
            reason = "数据部分改变"
            # 计算有多少字节与原模式相同
            recoverable_bytes = sum(
                1 for i in range(len(data_ref)) if data_ref[i] == self.test_pattern[i]
            )

        print(f"   安全等级: {security_level}")
        print(f"   原因: {reason}")
        print(f"   可恢复字节数: {recoverable_bytes} / 32")

        return {
            "method": method.value,
            "destroy_success": success,
            "before_matches": before["matches_pattern"],
            "after_matches": after["matches_pattern"],
            "after_all_zeros": after["all_zeros"],
            "after_is_random": after["is_random"],
            "unique_bytes": after["unique_bytes"],
            "recoverable_bytes": recoverable_bytes,
            "security_level": security_level.replace("❌ ", "")
            .replace("✅ ", "")
            .replace("⚠️  ", ""),
        }

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("密钥残留检测 - 改进版 PoC")
        print("=" * 70)

        print("\n💡 测试说明:")
        print("   - 直接检查Python bytearray对象的内存内容")
        print("   - 不依赖外部内存dump工具")
        print("   - 验证4种销毁方法的实际效果")

        methods = [
            DestructionMethod.SIMPLE_DEL,
            DestructionMethod.SINGLE_OVERWRITE,
            DestructionMethod.DOD_OVERWRITE,
            DestructionMethod.CTYPES_SECURE,
        ]

        results = []
        for method in methods:
            try:
                result = self.run_single_test(method)
                results.append(result)
            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                import traceback

                traceback.print_exc()

        # 生成对比表
        self.print_comparison_table(results)

        return results

    def print_comparison_table(self, results: list):
        """打印对比表"""
        print("\n" + "=" * 70)
        print("测试总结 - 方法对比")
        print("=" * 70)

        if not results:
            print("⚠️  没有成功的测试结果")
            return

        # 表头
        print(
            f"\n{'方法':<20} {'销毁':<6} {'全零':<6} {'随机':<6} {'可恢复':<10} {'安全性'}"
        )
        print("-" * 70)

        # 数据行
        for r in results:
            destroy_icon = "✅" if r["destroy_success"] else "❌"
            zeros_icon = "✅" if r["after_all_zeros"] else "❌"
            random_icon = "✅" if r["after_is_random"] else "❌"
            recoverable = f"{r['recoverable_bytes']}/32"

            # 安全性着色
            if r["security_level"] == "不安全":
                security = "❌ 不安全"
            elif r["security_level"] == "安全":
                security = "✅ 安全"
            else:
                security = "⚠️  部分安全"

            print(
                f"{r['method']:<20} {destroy_icon:<6} {zeros_icon:<6} {random_icon:<6} {recoverable:<10} {security}"
            )

        # 关键发现
        print("\n📌 关键发现:")

        unsafe_methods = [r for r in results if r["recoverable_bytes"] > 0]
        safe_methods = [r for r in results if r["recoverable_bytes"] == 0]

        if unsafe_methods:
            print(f"   ❌ 不安全方法 ({len(unsafe_methods)}个):")
            for r in unsafe_methods:
                print(f"      - {r['method']}: 可恢复 {r['recoverable_bytes']} 字节")

        if safe_methods:
            print(f"   ✅ 安全方法 ({len(safe_methods)}个):")
            for r in safe_methods:
                mechanism = "数据清零" if r["after_all_zeros"] else "随机覆写"
                print(f"      - {r['method']}: {mechanism}")

        # 推荐
        print("\n💡 推荐:")
        if safe_methods:
            best_method = safe_methods[0]["method"]
            print(f"   生产环境推荐使用: {best_method}")
        else:
            print("   ⚠️  所有方法都存在安全问题，需要进一步调查")


def main():
    """主函数"""
    test = DirectMemoryTest()
    test.run_all_tests()

    print("\n" + "=" * 70)
    print("✅ PoC 完成！")
    print("=" * 70)

    print("\n📝 下一步建议:")
    print("   1. 如果看到明显差异 → 继续开发完整实验框架")
    print("   2. 如果需要更真实的验证 → 安装ProcDump做内存取证")
    print("   3. 分析结果，撰写实验报告")


if __name__ == "__main__":
    main()
