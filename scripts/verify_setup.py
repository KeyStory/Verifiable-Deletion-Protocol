"""
环境配置验证脚本
验证项目初始化的所有步骤是否正确完成
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(
            f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro} (需要 3.10+)"
        )
        return False


def check_virtual_env():
    """检查是否在虚拟环境中"""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print(f"✅ 虚拟环境: {sys.prefix}")
        return True
    else:
        print("❌ 未激活虚拟环境")
        return False


def check_dependencies():
    """检查关键依赖是否安装"""
    dependencies = {
        "web3": "web3",
        "flask": "Flask",
        "cryptography": "cryptography",
        "pytest": "pytest",
        "dotenv": "python-dotenv",
    }

    all_ok = True
    for import_name, package_name in dependencies.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} 未安装")
            all_ok = False

    return all_ok


def check_directory_structure():
    """检查目录结构"""
    required_dirs = [
        "src/kms",
        "src/blockchain",
        "src/crypto",
        "src/api",
        "src/utils",
        "docs/design",
        "docs/experiments",
        "contracts",
        "tests/unit",
        "tests/integration",
        "scripts",
        "experiments",
    ]

    all_ok = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ 不存在")
            all_ok = False

    return all_ok


def check_config_files():
    """检查配置文件"""
    required_files = [".gitignore", ".env.example", "requirements.txt", "README.md"]

    all_ok = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} 不存在")
            all_ok = False

    # 检查 .env 是否存在且不在Git中
    if Path(".env").exists():
        print("✅ .env 文件存在")
    else:
        print("⚠️  .env 文件不存在（请复制 .env.example）")
        all_ok = False

    return all_ok


def check_git_config():
    """检查Git配置"""
    if Path(".git").exists():
        print("✅ Git仓库已初始化")

        # 检查是否有提交
        import subprocess

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"✅ 最新提交: {result.stdout.strip()}")
            else:
                print("⚠️  尚未进行首次提交")
        except Exception:
            print("⚠️  无法检查Git提交历史")

        return True
    else:
        print("❌ Git仓库未初始化")
        return False


def check_vscode_config():
    """检查VS Code配置"""
    vscode_settings = Path(".vscode/settings.json")
    if vscode_settings.exists():
        print("✅ VS Code配置文件存在")
        return True
    else:
        print("⚠️  VS Code配置文件不存在（可选）")
        return True  # 不是必需的，所以返回True


def main():
    """主验证流程"""
    print("=" * 60)
    print("项目环境配置验证".center(60))
    print("=" * 60 + "\n")

    checks = [
        ("Python版本", check_python_version),
        ("虚拟环境", check_virtual_env),
        ("依赖包", check_dependencies),
        ("目录结构", check_directory_structure),
        ("配置文件", check_config_files),
        ("Git配置", check_git_config),
        ("VS Code配置", check_vscode_config),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{'='*60}")
        print(f"检查: {name}")
        print("-" * 60)
        results.append(check_func())

    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ 所有检查通过 ({passed}/{total})".center(60))
        print("\n🎉 环境配置完成！可以开始开发了。".center(60))
    else:
        print(f"⚠️  部分检查未通过 ({passed}/{total})".center(60))
        print("\n请根据上述提示修复问题。".center(60))

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
