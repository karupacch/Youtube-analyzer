# app.py

import os
from flask import Flask, send_file, request, render_template # render_template_string から render_template に変更
from dotenv import load_dotenv
import pandas as pd
import io

# 自分で作成するAPI連携モジュールをインポート
from youtube_api import YouTubeAPI # youtube_api.py から YouTubeAPI クラスをインポート

# .envファイルから環境変数を読み込む
load_dotenv()

# YouTube Data APIキーを環境変数から取得
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Flaskアプリケーションの初期化
app = Flask(__name__)

# YouTube APIクライアントの初期化 (YouTubeAPIクラスのインスタンスを生成)
youtube_client = YouTubeAPI(api_key=YOUTUBE_API_KEY)


# -----------------------------------------------------------
# FlaskのルーティングとWebインターフェース
# -----------------------------------------------------------

# 検索フォームを表示するルート
@app.route('/', methods=['GET'])
def index():
    # templates/index.html をレンダリング
    return render_template('index.html')

# 検索リクエストを処理し、CSVを返すルート
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

    # CSVをメモリに書き込む
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig') # Excelで開けるように utf-8-sig
    output.seek(0) # ストリームの先頭に戻る

    # CSVファイルをダウンロードとして送信
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')), # バイトデータとして送信
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'youtube_videos_{query}_{video_type}.csv'
    )

# アプリケーションを実行
if __name__ == '__main__':
    app.run(debug=True) # debug=True は開発中に便利（コード変更で自動再起動など）