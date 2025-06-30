# app.py

import os
from flask import Flask, send_file, request, render_template
from dotenv import load_dotenv
import pandas as pd
import io

# 自分で作成するAPI連携モジュールをインポート
from youtube_api import YouTubeAPI
from google_sheets_api import GoogleSheetsAPI

# .envファイルから環境変数を読み込む
load_dotenv()

# YouTube Data APIキーを環境変数から取得
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Flaskアプリケーションの初期化
app = Flask(__name__)

# YouTube APIクライアントの初期化 (YouTubeAPIクラスのインスタンスを生成)
youtube_client = YouTubeAPI(api_key=YOUTUBE_API_KEY)
# Google Sheets APIクライアントの初期化
google_sheets_client = GoogleSheetsAPI()


# -----------------------------------------------------------
# FlaskのルーティングとWebインターフェース
# -----------------------------------------------------------

# 検索フォームを表示するルート
@app.route('/', methods=['GET'])
def index():
    # templates/index.html をレンダリング
    return render_template('index.html')

# 検索リクエストを処理し、CSVを返すルートからスプレッドシートに書き出すように変更
@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    video_type = request.form.get('video_type', 'any')
    order = request.form.get('order', 'relevance')
    published_after = request.form.get('published_after') # 空の場合もあるのでデフォルト値は設定しない
    published_before = request.form.get('published_before')
    max_results = int(request.form.get('max_results', 20))

    if not query:
        return render_template('index.html', message="検索キーワードを入力してください。", message_type="error")

    # youtube_api.py で定義した search_videos_data メソッドを呼び出し
    videos = youtube_client.search_videos_data(
        query=query, 
        video_type=video_type, 
        order=order,
        published_after=published_after,
        published_before=published_before,
        max_results=max_results
    )

    if not videos:
        return render_template('index.html', message="検索結果が見つかりませんでした。", message_type="error")

    # Pandas DataFrameに変換
    df = pd.DataFrame(videos)

    # ★Google スプレッドシートへのエクスポート処理★
    try:
        spreadsheet_title = f"Youtube_Results_{query}_{video_type}"
        # スプレッドシートを新規作成し、IDを取得
        spreadsheet_id = google_sheets_client.create_spreadsheet(spreadsheet_title)
        
        # データをスプレッドシートに書き込む ('Sheet1!A1' は最初のシートのA1セルから書き込む)
        google_sheets_client.write_data_to_sheet(spreadsheet_id, 'Sheet1!A1', df)
        
        # スプレッドシートのURLを生成し、メッセージとしてユーザーに表示
        sheets_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        message = f"検索結果をGoogleスプレッドシートにエクスポートしました: <a href='{sheets_url}' target='_blank'>{sheets_url}</a>"
        message_type = "success"

    except Exception as e:
        print(f"Google スプレッドシートへのエクスポート中にエラーが発生しました: {e}")
        message = f"Google スプレッドシートへのエクスポートに失敗しました: {e}"
        message_type = "error"
    
    # CSVダウンロード処理は削除し、スプレッドシートへのエクスポート結果をメッセージとして返す
    return render_template('index.html', message=message, message_type=message_type)

# アプリケーションを実行
if __name__ == '__main__':
    app.run(debug=True) # debug=True は開発中に便利（コード変更で自動再起動など）