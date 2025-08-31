# app.py

import os
from flask import Flask, send_file, request, render_template
from dotenv import load_dotenv
import pandas as pd
import io
import zipfile

# 自分で作成するAPI連携モジュールをインポート
from .youtube_api import YouTubeAPI
from .google_sheets_api import GoogleSheetsAPI
from .ai_api import GeminiAPI

# .envファイルから環境変数を読み込む
load_dotenv()

# YouTube Data APIキーを環境変数から取得
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Flaskアプリケーションの初期化
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static'))

# APIクライアントの初期化
youtube_client = YouTubeAPI(api_key=YOUTUBE_API_KEY)
google_sheets_client = GoogleSheetsAPI()
gemini_client = GeminiAPI()


# -----------------------------------------------------------
# FlaskのルーティングとWebインターフェース
# -----------------------------------------------------------

# 検索フォームを表示するルート
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# 検索リクエストを処理し、CSVやスプレッドシートを返すルート
@app.route('/search', methods=['POST'])
def search():
    genre = request.form.get('genre')
    query = request.form.get('query')
    video_type = request.form.get('video_type', 'any')
    order = request.form.get('order', 'relevance')
    published_after = request.form.get('published_after') # 空の場合もあるのでデフォルト値は設定しない
    published_before = request.form.get('published_before')
    max_results = int(request.form.get('max_results', 20))
    use_sheets_integration = request.form.get('use_sheets_integration') # チェックボックスの状態を取得

    # ジャンルと検索キーワードの両方が空の場合にエラー
    if not genre and not query:
        return render_template('index.html', message="ジャンルまたは検索キーワードを入力してください。", message_type="error")

    # AIで生成された複数のキーワードを扱う
    search_queries = []
    if genre:
        # AIでキーワードを生成
        keywords = gemini_client.generate_keywords(genre)
        if not keywords:
            return render_template('index.html', message="AIが検索キーワードを生成できませんでした。", message_type="error")
        search_queries = keywords
    else:
        # 従来の検索キーワードを使用
        search_queries = [query]

    # 複数の検索結果を格納するリスト
    all_videos_data = []
    
    for q in search_queries:
        videos = youtube_client.search_videos_data(
            query=q, 
            video_type=video_type, 
            order=order,
            published_after=published_after,
            published_before=published_before,
            max_results=max_results
        )
        if videos:
            all_videos_data.append({'query': q, 'videos': videos})

    if not all_videos_data:
        return render_template('index.html', message="検索結果が見つかりませんでした。", message_type="error")

    # 全ての動画データを一つのDataFrameに結合する
    combined_df = pd.concat([pd.DataFrame(item['videos']) for item in all_videos_data], ignore_index=True)

    # 結合したDataFrameをAI分析に渡す
    analysis_result = gemini_client.analyze_video_data(combined_df)

    # 出力形式による分岐
    if use_sheets_integration == 'on':
        try:
            # スプレッドシート出力の場合
            spreadsheet_title = f"Youtube_Results_by_AI_genre_{genre}" if genre else f"Youtube_Results_{query}_{video_type}"
            spreadsheet_id, sheet_id = google_sheets_client.create_spreadsheet(spreadsheet_title, sheet_name=search_queries[0])

            for item in all_videos_data:
                df = pd.DataFrame(item['videos'])
                if '動画説明文' in df.columns:
                    df = df.drop(columns=['動画説明文'])
                if order == 'viewCount':
                    df['再生回数'] = pd.to_numeric(df['再生回数'], errors='coerce').fillna(0)
                    df = df.sort_values(by='再生回数', ascending=False)
                
                # 最初のシートには既に書き込んでいるので、2つ目以降のシートを作成
                if item['query'] != search_queries[0]:
                    sheet_id = google_sheets_client.create_new_sheet(spreadsheet_id, item['query'])

                google_sheets_client.write_data_to_sheet(spreadsheet_id, f"'{item['query']}'!A1", df)

                if sheet_id is not None:
                    google_sheets_client.format_sheet(spreadsheet_id, df.columns.tolist(), sheet_id)

        # 分析結果を新しいシートに書き込む
            analysis_sheet_id = google_sheets_client.create_new_sheet(spreadsheet_id, '分析結果')
            google_sheets_client.write_analysis_to_sheet(spreadsheet_id, analysis_result, analysis_sheet_id)

            sheets_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            message = f"検索結果をGoogleスプレッドシートにエクスポートしました: <a href='{sheets_url}' target='_blank' class='button-link'>スプレッドシートを開く</a>"
            message_type = "success"

        except Exception as e:
            print(f"Google スプレッドシートへのエクスポート中にエラーが発生しました: {e}")
            message = f"Google スプレッドシートへのエクスポートに失敗しました: {e}"
            message_type = "error"
        
        return render_template('index.html', message=message, message_type=message_type)
        
    else:
        # CSV出力の場合
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for item in all_videos_data:
                df = pd.DataFrame(item['videos'])
                if '動画説明文' in df.columns:
                    df = df.drop(columns=['動画説明文'])
                if order == 'viewCount':
                    df['再生回数'] = pd.to_numeric(df['再生回数'], errors='coerce').fillna(0)
                    df = df.sort_values(by='再生回数', ascending=False)

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_buffer.seek(0)
                zip_file.writestr(f"{item['query']}.csv", csv_buffer.getvalue())

        zip_buffer.seek(0)
        
        # CSVダウンロードボタンの代わりに、分析結果を表示して、別途ダウンロードボタンを設置することも可能
        # 今回は、ダウンロードと分析結果表示を同時に行い、分析結果をテンプレートに渡す
        return render_template('index.html', analysis_result=analysis_result)

# アプリケーションを実行
if __name__ == '__main__':
    app.run(debug=True) # debug=True は開発中に便利（コード変更で自動再起動など）