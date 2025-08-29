import os
from dotenv import load_dotenv

# 新しい app_modules パッケージから Flask アプリケーションをインポート
# app_modules/app.py にある app オブジェクトをインポートする
from app_modules.app import app

load_dotenv()

# 'FLASK_APP' 環境変数を設定 (flask run コマンドが認識するため)
os.environ['FLASK_APP'] = 'main'

if __name__ == '__main__':
    # Flask アプリケーションを実行
    app.run(debug=True)