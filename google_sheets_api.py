# google_sheets_api.py

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# スプレッドシートのスコープを定義
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# 認証情報を保存するファイル名
TOKEN_PICKLE_FILE = 'token.pickle'

class GoogleSheetsAPI:
    def __init__(self):
        self.creds = None
        self._authenticate()
        # Sheets APIサービスを構築
        self.service = build('sheets', 'v4', credentials=self.creds)

    def _authenticate(self):
        """Google Sheets APIのための認証フローを処理します。"""
        # 既存の認証トークンがある場合は読み込む
        if os.path.exists(TOKEN_PICKLE_FILE):
            with open(TOKEN_PICKLE_FILE, 'rb') as token:
                self.creds = pickle.load(token)
        
        # 認証情報がない、または無効な場合は再認証する
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # トークンが期限切れの場合はリフレッシュする
                self.creds.refresh(Request())
            else:
                # 新しい認証フローを開始する
                # credentials.jsonファイルが必要です
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                # ローカルサーバーを起動し、ブラウザで認証を完了させる
                self.creds = flow.run_local_server(port=0)
            # 新しい認証情報をファイルに保存する
            with open(TOKEN_PICKLE_FILE, 'wb') as token:
                pickle.dump(self.creds, token)

    def create_spreadsheet(self, title):
        """新しいGoogleスプレッドシートを作成し、そのIDを返します。"""
        spreadsheet_body = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = self.service.spreadsheets().create(
            body=spreadsheet_body, fields='spreadsheetId'
        ).execute()
        print(f"スプレッドシートが作成されました: {spreadsheet.get('spreadsheetId')}")
        return spreadsheet.get('spreadsheetId')

    def write_data_to_sheet(self, spreadsheet_id, range_name, data_df):
        """指定されたスプレッドシートの範囲にDataFrameのデータを書き込みます。"""
        # DataFrameをヘッダー行を含むリストのリストに変換
        values = [data_df.columns.tolist()] + data_df.values.tolist()

        body = {
            'values': values
        }
        result = self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW', # RAWは入力された値をそのまま反映、USER_ENTEREDは書式などを解釈
            body=body
        ).execute()
        print(f"{result.get('updatedCells')} セルが更新されました。")
        return result