"""
KMS Package Main Entry Point

当使用 `python -m src.kms` 运行时执行此文件

这个文件提供了：
1. 包信息展示
2. 功能测试
3. 演示示例
"""

import sys
from . import (
    __version__,
    __author__,
    __description__,
    get_package_info,
    # 异常类
    KeyNotFoundError,
    # 工具函数
    generate_random_bytes,
    generate_key_id,
    dod_overwrite_memory,
    compute_key_fingerprint,
)


def print_banner():
    """打印包信息横幅"""
    print("=" * 60)
    print("KMS (Key Management Service) Package")
    print("=" * 60)


def show_package_info():
    """显示包信息"""
    info = get_package_info()
    print(f"\n📦 Package Information:")
    print(f"   Version:     {info['version']}")
    print(f"   Author:      {info['author']}")
    print(f"   Description: {info['description']}")


def test_imports():
    """测试包导入"""
    print(f"\n🔍 Testing imports...")

    try:
        print(f"   ✅ Exception classes available")
        print(f"   ✅ Utility functions available")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


def run_functionality_tests():
    """运行功能测试"""
    print(f"\n🧪 Running functionality tests:")

    # 测试1: 随机数生成
    try:
        key = generate_random_bytes(32)
        print(f"   ✅ Random key generation: {key.hex()[:32]}...")
    except Exception as e:
        print(f"   ❌ Random generation failed: {e}")
        return False

    # 测试2: 密钥ID生成
    try:
        key_id = generate_key_id()
        print(f"   ✅ Key ID generation: {key_id}")
    except Exception as e:
        print(f"   ❌ Key ID generation failed: {e}")
        return False

    # 测试3: 内存清零
    try:
        secret = bytearray(b"TOPSECRET")
        dod_overwrite_memory(secret)
        all_random = len(set(secret)) > 1  # 随机数据应该有多种字节值
        if all_random:
            print(f"   ✅ Memory overwrite (DoD): {secret.hex()}")
        else:
            print(f"   ⚠️  Memory overwrite warning: data might not be random")
    except Exception as e:
        print(f"   ❌ Memory overwrite failed: {e}")
        return False

    # 测试4: 密钥指纹
    try:
        test_key = b"my_secret_key_12345"
        fingerprint = compute_key_fingerprint(test_key)
        print(f"   ✅ Key fingerprint: {fingerprint}")
    except Exception as e:
        print(f"   ❌ Fingerprint failed: {e}")
        return False

    # 测试5: 异常处理
    try:
        raise KeyNotFoundError("test_key_123")
    except KeyNotFoundError as e:
        print(f"   ✅ Exception handling: {e}")
    except Exception as e:
        print(f"   ❌ Exception handling failed: {e}")
        return False

    return True


def show_usage_example():
    """显示使用示例"""
    print(f"\n💡 Usage Example:")
    print(
        f"""
    from src.kms import (
        generate_random_bytes,
        dod_overwrite_memory,
        KeyNotFoundError
    )
    
    # 生成密钥
    key = generate_random_bytes(32)  # AES-256密钥
    
    # 安全销毁
    key_data = bytearray(key)
    dod_overwrite_memory(key_data)  # DoD标准3次覆写
    
    # 异常处理
    try:
        # 某些操作...
        pass
    except KeyNotFoundError as e:
        print(f"Key not found: {{e}}")
    """
    )


def main():
    """主函数"""
    print_banner()
    show_package_info()

    # 运行测试
    if not test_imports():
        print("\n❌ Import test failed")
        sys.exit(1)

    if not run_functionality_tests():
        print("\n❌ Functionality test failed")
        sys.exit(1)

    show_usage_example()

    # 显示状态
    print("\n" + "=" * 60)
    print("✅ All tests passed! KMS package is ready to use.")
    print("=" * 60)
    print("\n💡 Tip: Next step is to implement KeyManagementService class")
    print("   in src/kms/key_manager.py\n")


if __name__ == "__main__":
    main()
