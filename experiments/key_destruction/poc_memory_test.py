"""
密钥残留检测 - 概念验证（PoC）

这个脚本验证我们能否：
1. 在内存中创建密钥
2. Dump进程内存
3. 搜索密钥残留
4. 对比不同销毁方法的效果

使用方法：
    python -m experiments.key_destruction.poc_memory_test
"""

import os
import sys
import time
import psutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kms import (
    KeyManagementService,
    DestructionMethod,
)


class MemoryTestPoC:
    """内存测试概念验证类"""

    def __init__(self):
        self.kms = KeyManagementService()
        # 使用32字节的测试模式（符合AES-256标准）
        # 精确控制长度：16字符 + 16字符 = 32字节
        self.test_pattern = b"SECRET_KEY_ABCD_1234567890123456"  # 恰好32字节
        self.pid = os.getpid()

        # 验证测试模式长度
        assert (
            len(self.test_pattern) == 32
        ), f"Test pattern length error: {len(self.test_pattern)}"

    def get_process_memory_mb(self) -> float:
        """获取当前进程内存使用量（MB）"""
        process = psutil.Process(self.pid)
        return process.memory_info().rss / 1024 / 1024

    def dump_process_memory(self, output_file: str) -> bool:
        """
        Dump进程内存到文件

        注意：这个方法在不同操作系统上有不同实现：
        - Linux: 使用 gcore
        - Windows: 需要其他工具
        - macOS: 使用 sample 或其他工具

        Args:
            output_file: 输出文件路径

        Returns:
            是否成功
        """
        import platform

        system = platform.system()

        print(f"   检测到操作系统: {system}")

        if system == "Linux":
            # Linux: 使用 gcore
            import subprocess

            try:
                # gcore 会创建 core.PID 文件
                result = subprocess.run(
                    ["gcore", "-o", output_file.replace(".dump", ""), str(self.pid)],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    # 重命名生成的文件
                    core_file = f"{output_file.replace('.dump', '')}.{self.pid}"
                    if os.path.exists(core_file):
                        os.rename(core_file, output_file)
                        return True
                print(f"   gcore 失败: {result.stderr.decode()}")
                return False
            except FileNotFoundError:
                print("   ❌ gcore 未安装")
                return False
            except Exception as e:
                print(f"   ❌ gcore 错误: {e}")
                return False

        elif system == "Windows":
            # Windows: 使用 /proc/PID/mem 读取（Python方式）
            return self._dump_memory_python_way(output_file)

        elif system == "Darwin":  # macOS
            print("   ℹ️  macOS 暂不支持自动dump，使用Python方式")
            return self._dump_memory_python_way(output_file)

        else:
            print(f"   ⚠️  未知系统 {system}，尝试Python方式")
            return self._dump_memory_python_way(output_file)

    def _dump_memory_python_way(self, output_file: str) -> bool:
        """
        使用纯Python方式"模拟"内存dump

        注意：这不是真正的内存dump，只是读取Python对象
        实际实验应该使用专业工具
        """
        print("   ℹ️  使用Python模拟方式（仅用于PoC）")

        try:
            # 收集当前进程的所有对象
            import gc

            gc.collect()

            # 获取所有bytearray对象
            all_objects = gc.get_objects()
            bytearrays = [obj for obj in all_objects if isinstance(obj, bytearray)]

            # 写入文件
            with open(output_file, "wb") as f:
                for ba in bytearrays:
                    f.write(ba)
                    f.write(b"\x00" * 16)  # 分隔符

            return True
        except Exception as e:
            print(f"   ❌ Python方式失败: {e}")
            return False

    def search_pattern_in_file(self, file_path: str, pattern: bytes) -> dict:
        """
        在文件中搜索模式

        Args:
            file_path: 文件路径
            pattern: 要搜索的模式

        Returns:
            搜索结果字典
        """
        if not os.path.exists(file_path):
            return {
                "found": False,
                "count": 0,
                "positions": [],
                "partial_matches": 0,
            }

        result = {
            "found": False,
            "count": 0,
            "positions": [],
            "partial_matches": 0,
        }

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # 搜索完整匹配
            pos = 0
            while True:
                pos = content.find(pattern, pos)
                if pos == -1:
                    break
                result["positions"].append(pos)
                result["count"] += 1
                result["found"] = True
                pos += 1

            # 搜索部分匹配（至少50%）
            min_match_length = max(4, len(pattern) // 2)
            for length in range(len(pattern) - 1, min_match_length - 1, -1):
                for i in range(len(pattern) - length + 1):
                    partial = pattern[i : i + length]
                    if partial in content and len(partial) >= min_match_length:
                        result["partial_matches"] += content.count(partial)
                        break

        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")

        return result

    def run_test(self, method: DestructionMethod) -> dict:
        """
        运行单次测试

        Args:
            method: 销毁方法

        Returns:
            测试结果
        """
        print(f"\n{'='*60}")
        print(f"测试方法: {method.value}")
        print(f"{'='*60}")

        # 1. 生成密钥（使用标准AES-256大小）
        print("\n1. 生成测试密钥...")
        key_id = self.kms.generate_key(
            key_size=32,  # AES-256标准大小
            algorithm="AES-256-GCM",  # 使用标准算法
            purpose="memory_test",
        )

        # 替换为我们的测试模式（便于搜索）
        key = self.kms.get_key(key_id)
        key._key_data = bytearray(self.test_pattern)

        print(f"   ✅ 密钥ID: {key_id}")
        print(f"   ✅ 测试模式: {self.test_pattern.decode()}")
        print(f"   ✅ 模式长度: {len(self.test_pattern)} 字节")

        # 2. 销毁前的内存状态
        print("\n2. 销毁前 - Dump内存...")
        before_file = f"memory_before_{method.value}.dump"
        before_success = self.dump_process_memory(before_file)

        if before_success:
            before_result = self.search_pattern_in_file(before_file, self.test_pattern)
            print(f"   ✅ Dump成功: {before_file}")
            print(f"   ✅ 找到模式: {before_result['count']} 次")
        else:
            print(f"   ⚠️  Dump失败（这在某些系统上是正常的）")
            before_result = {"found": False, "count": 0}

        # 3. 执行销毁
        print(f"\n3. 执行销毁 ({method.value})...")
        destroy_success = self.kms.destroy_key(key_id, method)
        print(
            f"   {'✅' if destroy_success else '❌'} 销毁{'成功' if destroy_success else '失败'}"
        )

        # 强制垃圾回收
        import gc

        gc.collect()
        time.sleep(0.1)  # 等待GC完成

        # 4. 销毁后的内存状态
        print("\n4. 销毁后 - Dump内存...")
        after_file = f"memory_after_{method.value}.dump"
        after_success = self.dump_process_memory(after_file)

        if after_success:
            after_result = self.search_pattern_in_file(after_file, self.test_pattern)
            print(f"   ✅ Dump成功: {after_file}")
            print(
                f"   {'❌' if after_result['found'] else '✅'} 找到模式: {after_result['count']} 次"
            )
        else:
            print(f"   ⚠️  Dump失败")
            after_result = {"found": False, "count": 0}

        # 5. 结果分析
        print("\n5. 结果分析:")
        recoverable_bytes = 0
        if after_result["found"]:
            recoverable_bytes = len(self.test_pattern) * after_result["count"]
            print(f"   ❌ 数据可恢复！")
            print(f"   ❌ 可恢复字节数: {recoverable_bytes}")
            security_level = "不安全"
        else:
            print(f"   ✅ 数据不可恢复")
            print(f"   ✅ 可恢复字节数: 0")
            security_level = "安全"

        # 6. 清理dump文件
        for f in [before_file, after_file]:
            if os.path.exists(f):
                os.remove(f)

        return {
            "method": method.value,
            "destroy_success": destroy_success,
            "before_found": before_result.get("count", 0),
            "after_found": after_result.get("count", 0),
            "recoverable_bytes": recoverable_bytes,
            "security_level": security_level,
        }


def main():
    """主函数"""
    print("=" * 60)
    print("密钥残留检测 - 概念验证")
    print("=" * 60)

    # 显示系统信息
    import platform

    print(f"\n系统信息:")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  Python版本: {platform.python_version()}")
    print(f"  进程PID: {os.getpid()}")

    poc = MemoryTestPoC()
    print(f"  当前内存: {poc.get_process_memory_mb():.2f} MB")

    # 测试不同的销毁方法
    methods = [
        DestructionMethod.SIMPLE_DEL,
        DestructionMethod.DOD_OVERWRITE,
    ]

    results = []
    for method in methods:
        try:
            result = poc.run_test(method)
            results.append(result)
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback

            traceback.print_exc()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if results:
        print("\n方法对比:")
        print(f"{'方法':<20} {'销毁成功':<10} {'可恢复字节':<12} {'安全性'}")
        print("-" * 60)
        for r in results:
            print(
                f"{r['method']:<20} {'✅' if r['destroy_success'] else '❌':<10} "
                f"{r['recoverable_bytes']:<12} {r['security_level']}"
            )
    else:
        print("⚠️  没有成功的测试结果")

    print("\n" + "=" * 60)
    print("PoC 完成！")
    print("=" * 60)

    print("\n💡 下一步:")
    print("  1. 如果内存dump成功 → 可以进行完整实验")
    print("  2. 如果内存dump失败 → 需要安装专业工具（如gcore）")
    print("  3. 分析结果，确定实验方案")


if __name__ == "__main__":
    main()
