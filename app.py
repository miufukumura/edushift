# FlaskライブラリからFlaskという機能を取り込む
from flask import Flask

# Flaskアプリの本体を作成
app = Flask(__name__)

# ルートURL ("/") にアクセスがあった場合の処理を定義
@app.route('/')
def hello_world():
    return 'Hello, World!'