import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import os # OSモジュールをインポート

# --- 1. アプリケーション設定 ---
app = Flask(__name__)
# 実際はより複雑でセキュアなSECRET_KEYを設定してください
app.config['SECRET_KEY'] = 'your_super_secret_key_12345' 
DATABASE = 'edushift.db'


# --- 2. データベース接続ヘルパー ---
def get_db():
    """データベース接続を取得し、辞書形式で結果を返すように設定する"""
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.exists(DATABASE):
             # DBファイルがない場合、エラーを明確に出す
             raise RuntimeError(f"Database file '{DATABASE}' not found. Please run 'python init_db.py'.")

        try:
            db = g._database = sqlite3.connect(DATABASE)
            # 結果を辞書形式で取得するための設定
            db.row_factory = sqlite3.Row 
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise RuntimeError(f"Database connection failed: {e}")
    return db

@app.teardown_appcontext
def close_connection(exception):
    """リクエスト終了時にデータベース接続を閉じる"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# --- 3. 共通・認証機能 ---
@app.route('/', methods=['GET'])
def index():
    """ルートアクセス時の処理。ログイン状態に応じてリダイレクトする"""
    if 'user_role' in session: 
        if session['user_role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_shift'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログインフォームと認証処理"""
    if 'user_role' in session: 
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            # パスワードのハッシュ値を照合 (check_password_hashを使用)
            if user and check_password_hash(user['password'], password):
                # 認証成功
                session['user_id'] = user['id']
                session['user_role'] = user['role']
                session['user_name'] = user['name']

                return redirect(url_for('index'))
            else:
                error = 'メールアドレスまたはパスワードが違います'
        except RuntimeError as e:
            # DB接続エラーの場合はログイン画面にメッセージを表示
            error = str(e)
        except Exception as e:
            print(f"Login error: {e}")
            error = 'サーバー側で予期せぬエラーが発生しました。'
            

    return render_template('login.html', error=error)

# 修正された新規登録ルーティング
@app.route('/register', methods=['GET', 'POST'])
def register():
    """新規ユーザー登録処理（デフォルトは講師として登録）"""
    if 'user_id' in session:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # 簡易バリデーション
        if len(password) < 6:
            error = 'パスワードは6文字以上で設定してください。'
            return render_template('register.html', error=error)
        
        try:
            db = get_db()
            
            # メールアドレス重複チェック
            if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                error = 'このメールアドレスは既に使用されています。'
            else:
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                # 新規登録は講師(teacher)として登録
                db.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                           (name, email, hashed_password, 'teacher'))
                db.commit()
                # 登録成功後、ログイン画面へリダイレクト
                return redirect(url_for('login'))
        except sqlite3.OperationalError:
            error = 'データベーステーブルが見つかりません。`python init_db.py`を実行してください。'
        except RuntimeError as e:
            error = str(e) # get_db()で発生したDB接続エラー
        except Exception as e:
            print(f"Register error: {e}")
            error = 'サーバー側で予期せぬエラーが発生しました。'

    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """ログアウト処理。セッションをクリアする"""
    session.clear()
    return redirect(url_for('login'))


# --- 4. 講師関連機能 ---
@app.route('/teacher/shift', methods=['GET', 'POST'])
def teacher_shift():
    """講師のシフト登録・確認画面"""
    # 権限チェック
    if session.get('user_role') not in ['teacher', 'admin']:
         return redirect(url_for('login')) 
    
    user_id = session['user_id']
    db = get_db()
    error = None

    if request.method == 'POST':
        # シフト登録処理
        date = request.form['date']
        start = request.form['start_time']
        end = request.form['end_time']
        
        try:
            db.execute("INSERT INTO shifts (user_id, date, start_time, end_time) VALUES (?, ?, ?, ?)",
                       (user_id, date, start, end))
            db.commit()
            return redirect(url_for('teacher_shift'))
        except sqlite3.Error as e:
            print(f"シフト登録エラー: {e}")
            error = "シフトの登録中にエラーが発生しました。"

    # シフト情報取得
    shifts = db.execute("SELECT * FROM shifts WHERE user_id = ? ORDER BY date", 
                        (user_id,)).fetchall()
    
    return render_template('teacher_shift.html', shifts=shifts, error=error)


@app.route('/teacher/shift/delete/<int:shift_id>', methods=['POST'])
def delete_shift(shift_id):
    """シフトの削除処理"""
    if session.get('user_role') not in ['teacher', 'admin']:
        return redirect(url_for('login'))
        
    db = get_db()
    
    # 講師は自分のシフトのみ削除可能
    if session['user_role'] == 'teacher':
        db.execute("DELETE FROM shifts WHERE id = ? AND user_id = ?", (shift_id, session['user_id']))
    else: # adminは全て削除可能
        db.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        
    db.commit()
    return redirect(url_for('teacher_shift'))


# --- 5. 生徒授業管理機能 (講師/管理者 共通) ---
@app.route('/lesson/manage', methods=['GET', 'POST'])
def lesson_manage():
    """授業の登録、欠席・振替の管理画面"""
    if 'user_id' not in session:
         return redirect(url_for('login')) 
         
    db = get_db()
    error = None

    if request.method == 'POST':
        # 授業登録処理
        student_id = request.form['student_id']
        teacher_id = request.form['teacher_id']
        date = request.form['date']
        status = request.form['status']
        notes = request.form.get('notes', '')

        try:
            db.execute("INSERT INTO lessons (student_id, teacher_id, date, status, notes) VALUES (?, ?, ?, ?, ?)",
                       (student_id, teacher_id, date, status, notes))
            db.commit()
            return redirect(url_for('lesson_manage'))
        except sqlite3.Error as e:
            print(f"授業登録エラー: {e}")
            error = "授業登録中にエラーが発生しました。"
    
    # GET (表示) 処理
    students = db.execute("SELECT id, name FROM students ORDER BY name").fetchall()
    teachers = db.execute("SELECT id, name FROM users WHERE role = 'teacher' ORDER BY name").fetchall()
    
    # 授業履歴取得（生徒名と講師名を結合して表示）
    lessons = db.execute("""
        SELECT 
            l.*, 
            s.name AS student_name, 
            u.name AS teacher_name
        FROM lessons l 
        JOIN students s ON l.student_id = s.id 
        JOIN users u ON l.teacher_id = u.id 
        ORDER BY l.date DESC 
        LIMIT 50
    """).fetchall()

    return render_template('lesson_manage.html', students=students, teachers=teachers, lessons=lessons, error=error)


# --- 6. 管理者機能 ---
@app.route('/admin/dashboard')
def admin_dashboard():
    """管理者ダッシュボード: 全体スケジュールと変更履歴の確認"""
    if session.get('user_role') != 'admin':
         return redirect(url_for('login')) 

    db = get_db()
    
    # 全講師のシフト（直近50件）
    all_shifts = db.execute("""
        SELECT s.date, s.start_time, s.end_time, u.name AS teacher_name 
        FROM shifts s JOIN users u ON s.user_id = u.id 
        ORDER BY s.date, s.start_time
        LIMIT 50
    """).fetchall()

    # 欠席・振替の最新履歴（最新30件）
    recent_changes = db.execute("""
        SELECT 
            l.date, 
            l.status, 
            s.name AS student_name, 
            u.name AS teacher_name
        FROM lessons l
        JOIN students s ON l.student_id = s.id
        JOIN users u ON l.teacher_id = u.id
        WHERE l.status IN ('欠席', '振替')
        ORDER BY l.date DESC
        LIMIT 30
    """).fetchall()

    return render_template('admin_dashboard.html', all_shifts=all_shifts, recent_changes=recent_changes)


@app.route('/manage/users', methods=['GET', 'POST'])
def manage_users():
    """講師・生徒のアカウント管理（追加・削除）"""
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
        
    db = get_db()
    error = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'add_user':
                name = request.form['name']
                email = request.form['email']
                password = request.form['password']
                role = request.form['role']

                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                db.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                            (name, email, hashed_password, role))
                db.commit()
                
            elif action == 'add_student':
                name = request.form['name']
                grade = request.form.get('grade', '')

                db.execute("INSERT INTO students (name, grade) VALUES (?, ?)",
                        (name, grade))
                db.commit()

            elif action == 'delete_user':
                user_id = request.form['id']
                db.execute("DELETE FROM shifts WHERE user_id = ?", (user_id,))
                db.execute("DELETE FROM users WHERE id = ?", (user_id,))
                db.commit()

            elif action == 'delete_student':
                student_id = request.form['id']
                db.execute("DELETE FROM lessons WHERE student_id = ?", (student_id,))
                db.execute("DELETE FROM students WHERE id = ?", (student_id,))
                db.commit()
        except sqlite3.IntegrityError:
            error = "データの重複エラーが発生しました。"
        except Exception as e:
            print(f"User management error: {e}")
            error = f"処理中にエラーが発生しました: {e}"

        return redirect(url_for('manage_users', error=error))

    users = db.execute("SELECT id, name, email, role FROM users ORDER BY role DESC, name").fetchall()
    students = db.execute("SELECT id, name, grade FROM students ORDER BY name").fetchall()
    
    return render_template('manage_users.html', users=users, students=students, error=error)


# --- 7. アプリケーションのエントリーポイント ---
if __name__ == '__main__':
    # 💡 確実にデバッグモードを有効にし、エラーがブラウザに表示されるようにする
    app.debug = True 
    app.run()
