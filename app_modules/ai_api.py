import os
import google.generativeai as genai

class GeminiAPI:
    def __init__(self):
        # 環境変数からAPIキーを取得
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-pro')

    def generate_keywords(self, genre):
        """
        AIモデルにジャンルに関連する検索キーワードを生成させる。
        """
        prompt = f"「{genre}」というジャンルに関連する、YouTubeで人気のある動画を検索するためのキーワードを5つ、カンマ区切りで生成してください。回答はキーワードのみにしてください。不必要な前置きや説明は含めないでください。"
        
        try:
            response = self.model.generate_content(prompt)
            keywords_text = response.text.strip()
            # AIの応答をカンマで分割してリストに変換
            return [k.strip() for k in keywords_text.split(',')]
        except Exception as e:
            print(f"AIキーワード生成中にエラーが発生しました: {e}")
            return []
        
    def analyze_video_data(self, df):
        # """
        # DataFrameの統計情報をAIモデルで分析する。
        # """
        # # DataFrameの統計情報を要約する
        # stats = df.describe(include='all').to_markdown()
        # # DataFrameをMarkdown形式の文字列に変換
        # df_markdown = df.to_markdown(index=False)
        
        # # DataFrameの先頭5行と末尾5行を文字列に変換してプロンプトに含める
        # df_head = df.head().to_markdown(index=False)
        # df_tail = df.tail().to_markdown(index=False)
        
        # prompt = f"""
        #     以下のYouTube動画のデータ分析を依頼します。
        #     ---
        #     データ:
        #     {df_markdown}
        #     ---
        #     このデータから読み取れる傾向や特徴、動画の成功要因、視聴者の関心事など、多角的な分析結果を日本語で簡潔に、Markdown形式でまとめてください。特に、再生回数、高評価数、コメント数の関係性や、動画タイプ（Short/Long）の傾向について言及してください。
        #     """
        
        # try:
        #     response = self.model.generate_content(prompt)
        #     analysis_text = response.text.strip()
        #     return analysis_text
        # except Exception as e:
        #     print(f"AIデータ分析中にエラーが発生しました: {e}")
        #     return "分析結果の生成中にエラーが発生しました。"
        print("開発モード: AIによるデータ分析はスキップされました。")
        return "これは開発モードで生成されたモックの分析結果です。AIを利用するには、有料プランにアップグレードするか、日次クォータのリセットをお待ちください。"