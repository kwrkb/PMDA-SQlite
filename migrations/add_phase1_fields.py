#!/usr/bin/env python3
"""
フェーズ1フィールドのマイグレーション

既存のpmda.sqliteデータベースに以下のカラムを追加:
- regulatory_classification (規制区分)
- composition (組成・性状)
- overdosage (過量投与)
"""

import sqlite3
import os
import sys

DB_NAME = 'pmda.sqlite'

def check_column_exists(cursor, table_name, column_name):
    """
    カラムが既に存在するかチェック

    Args:
        cursor: SQLiteカーソル
        table_name: テーブル名
        column_name: カラム名

    Returns:
        True if exists, False otherwise
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    """
    マイグレーションを実行
    """
    # データベースファイルの存在確認
    if not os.path.exists(DB_NAME):
        print(f"エラー: データベースファイル '{DB_NAME}' が見つかりません。")
        print("先にデータベースを作成してください:")
        print("  python3 src/db_setup.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # フェーズ1フィールドのリスト
    phase1_fields = [
        ('regulatory_classification', 'TEXT', '規制区分'),
        ('composition', 'TEXT', '組成・性状'),
        ('overdosage', 'TEXT', '過量投与'),
    ]

    print(f"マイグレーション開始: {DB_NAME}")
    print("-" * 60)

    # トランザクション開始
    try:
        for column_name, column_type, description in phase1_fields:
            # カラムが既に存在するかチェック
            if check_column_exists(cur, 'medicines', column_name):
                print(f"⏭️  スキップ: {column_name} ({description}) は既に存在します")
            else:
                # カラムを追加
                cur.execute(f"ALTER TABLE medicines ADD COLUMN {column_name} {column_type}")
                print(f"✅ 追加: {column_name} ({description})")

        # コミット
        conn.commit()
        print("-" * 60)
        print("マイグレーション完了")

        # 現在のスキーマを表示
        print("\n現在のスキーマ (medicines テーブル):")
        cur.execute("PRAGMA table_info(medicines)")
        for row in cur.fetchall():
            col_id, col_name, col_type, not_null, default_val, pk = row
            print(f"  {col_id}: {col_name} ({col_type})")

    except Exception as e:
        conn.rollback()
        print(f"エラー: マイグレーションに失敗しました - {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
