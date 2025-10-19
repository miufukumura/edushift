import sqlite3
# 🚨 これを追加: パスワードハッシュ化のためのインポート
from werkzeug.security import generate_password_hash 

# データベースファイルのパス
DATABASE = 'edushift.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. users テーブル (講師/管理者)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL -- 'teacher' or 'admin'
        );
    """)

    # 2. students テーブル (生徒情報)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT
        );
    """)

    # 3. shifts テーブル (講師シフト希望・確定)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    # 4. lessons テーブル (授業情報)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT NOT NULL, -- '通常' / '欠席' / '振替'
            notes TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        );
    """)

    # 初期管理者アカウントの作成 (開発用)
    try:
        # パスワード 'adminpass' をハッシュ化して保存
        hashed_password = generate_password_hash('adminpass', method='pbkdf2:sha256') 
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                       ('管理者', 'admin@example.com', hashed_password, 'admin'))
    except sqlite3.IntegrityError:
        # 既に存在する場合は無視
        pass

    conn.commit()
    conn.close()

if __name__ == '__main__':
    # 既存のDBファイルを削除してから実行すると確実にリセットされます (オプション)
    # import os; if os.path.exists(DATABASE): os.remove(DATABASE)
    init_db()
    print(f"Database {DATABASE} initialized.")
