"""
数据库模块 - MVP版本

使用SQLite实现简单的用户数据存储。
专注于演示加密删除协议，而非完整的业务系统。

表结构：
1. users - 用户基本信息
2. encrypted_data - 加密的用户数据
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class Database:
    """简化的数据库管理类"""

    def __init__(self, db_path: str = "data/app.db"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # 使用字典形式返回结果

        self._init_tables()

    def _init_tables(self):
        """创建表结构"""
        cursor = self.conn.cursor()

        # 1. 用户表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
        """
        )

        # 2. 加密数据表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS encrypted_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                ciphertext BLOB NOT NULL,
                encryption_metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # 3. 删除记录表（本地记录，补充区块链记录）
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deletion_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key_id TEXT NOT NULL,
                destruction_method TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                blockchain_tx TEXT,
                proof_hash TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        self.conn.commit()

    def create_user(
        self, user_id: str, username: str, email: str | None = None
    ) -> bool:
        """
        创建用户

        Args:
            user_id: 用户ID
            username: 用户名
            email: 邮箱

        Returns:
            bool: 是否成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, username, email, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, email, datetime.utcnow().isoformat()),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """获取用户信息"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def store_encrypted_data(
        self,
        user_id: str,
        data_type: str,
        ciphertext: bytes,
        metadata: dict[str, Any],
    ) -> int:
        """
        存储加密数据

        Args:
            user_id: 用户ID
            data_type: 数据类型（如"profile", "game_record"）
            ciphertext: 密文
            metadata: 加密元数据

        Returns:
            int: 记录ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO encrypted_data 
            (user_id, data_type, ciphertext, encryption_metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                data_type,
                ciphertext,
                json.dumps(metadata),
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()

        record_id = cursor.lastrowid
        if record_id is None:
            raise RuntimeError("Failed to get last inserted row ID")

        return record_id

    def get_encrypted_data(self, user_id: str) -> list[dict[str, Any]]:
        """获取用户的所有加密数据"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM encrypted_data WHERE user_id = ?", (user_id,))

        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data["encryption_metadata"] = json.loads(data["encryption_metadata"])
            results.append(data)

        return results

    def mark_user_deleted(
        self,
        user_id: str,
        key_id: str,
        destruction_method: str,
        blockchain_tx: str | None = None,
        proof_hash: str | None = None,
    ) -> bool:
        """
        标记用户为已删除，并记录删除信息

        Args:
            user_id: 用户ID
            key_id: 被销毁的密钥ID
            destruction_method: 销毁方法
            blockchain_tx: 区块链交易哈希
            proof_hash: 删除证明哈希

        Returns:
            bool: 是否成功
        """
        try:
            cursor = self.conn.cursor()

            # 1. 更新用户状态
            cursor.execute(
                """
                UPDATE users 
                SET deleted_at = ?, is_deleted = 1
                WHERE user_id = ?
                """,
                (datetime.utcnow().isoformat(), user_id),
            )

            # 2. 记录删除信息
            cursor.execute(
                """
                INSERT INTO deletion_records
                (user_id, key_id, destruction_method, deleted_at, blockchain_tx, proof_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    key_id,
                    destruction_method,
                    datetime.utcnow().isoformat(),
                    blockchain_tx,
                    proof_hash,
                ),
            )

            self.conn.commit()
            return True
        except Exception as e:
            print(f"标记用户删除失败: {e}")
            return False

    def get_deletion_record(self, user_id: str) -> dict[str, Any] | None:
        """获取用户的删除记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM deletion_records WHERE user_id = ? ORDER BY deleted_at DESC LIMIT 1",
            (user_id,),
        )

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_users(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        """列出所有用户"""
        cursor = self.conn.cursor()

        if include_deleted:
            cursor.execute("SELECT * FROM users")
        else:
            cursor.execute("SELECT * FROM users WHERE is_deleted = 0")

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        self.conn.close()

    def __enter__(self):
        """上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# ===== 测试 =====

if __name__ == "__main__":
    print("=" * 60)
    print("数据库模块测试")
    print("=" * 60)

    # 创建测试数据库
    db = Database("data/test.db")

    # 1. 创建用户
    print("\n1. 创建用户...")
    success = db.create_user("user_001", "alice", "alice@example.com")
    print(f"   ✓ 用户创建: {success}")

    # 2. 获取用户
    print("\n2. 获取用户信息...")
    user = db.get_user("user_001")
    if user:
        print(f"   ✓ 用户名: {user['username']}")
        print(f"   ✓ 邮箱: {user['email']}")
        print(f"   ✓ 创建时间: {user['created_at']}")

    # 3. 存储加密数据
    print("\n3. 存储加密数据...")
    metadata = {
        "key_id": "user_001_dek",
        "algorithm": "AES-256-GCM",
        "nonce": "abc123",
    }
    record_id = db.store_encrypted_data(
        "user_001", "profile", b"encrypted_data_here", metadata
    )
    print(f"   ✓ 记录ID: {record_id}")

    # 4. 获取加密数据
    print("\n4. 获取用户的加密数据...")
    data_list = db.get_encrypted_data("user_001")
    print(f"   ✓ 数据记录数: {len(data_list)}")

    # 5. 标记用户删除
    print("\n5. 标记用户为已删除...")
    success = db.mark_user_deleted(
        "user_001", "user_001_dek", "dod_overwrite", "0x123abc...", "proof_hash_123"
    )
    print(f"   ✓ 删除标记: {success}")

    # 6. 获取删除记录
    print("\n6. 获取删除记录...")
    deletion = db.get_deletion_record("user_001")
    if deletion:
        print(f"   ✓ 销毁方法: {deletion['destruction_method']}")
        print(f"   ✓ 区块链交易: {deletion['blockchain_tx']}")
        print(f"   ✓ 删除时间: {deletion['deleted_at']}")

    # 7. 列出用户
    print("\n7. 列出用户...")
    active_users = db.list_users(include_deleted=False)
    all_users = db.list_users(include_deleted=True)
    print(f"   ✓ 活跃用户: {len(active_users)}")
    print(f"   ✓ 总用户数: {len(all_users)}")

    db.close()

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
