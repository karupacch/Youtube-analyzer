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