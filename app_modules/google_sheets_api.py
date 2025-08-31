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

    def create_spreadsheet(self, title, sheet_name='Sheet1'):
        """新しいGoogleスプレッドシートを作成し、そのIDと最初のシートのIDを返します。"""
        spreadsheet_body = {
            'properties': {
                'title': title
            },
            'sheets': [
                {
                    'properties': {
                        'title': sheet_name # 最初のシート名を明示的に'sheet_name'に設定
                    }
                }
            ]
        }
        spreadsheet = self.service.spreadsheets().create(
            body=spreadsheet_body, fields='spreadsheetId,sheets.properties.sheetId'
        ).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        sheet_id = None
        if spreadsheet.get('sheets') and len(spreadsheet['sheets']) > 0:
            sheet_id = spreadsheet['sheets'][0]['properties'].get('sheetId')

        print(f"スプレッドシートが作成されました: {spreadsheet_id} (シートID: {sheet_id})")
        
        return spreadsheet_id, sheet_id # スプレッドシートIDとシートIDの両方をタプルとして返しているか確認

    def create_new_sheet(self, spreadsheet_id, sheet_title):
        """既存のスプレッドシートに新しいシートを作成し、そのIDを返します。"""
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_title
                    }
                }
            }]
        }
        response = self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()

        new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        print(f"新しいシート '{sheet_title}' が作成されました。シートID: {new_sheet_id}")
        return new_sheet_id
    
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
    
    def write_analysis_to_sheet(self, spreadsheet_id, analysis_text, sheet_title, sheet_id):
        """
        指定されたスプレッドシートの新しいシートに分析結果を書き込みます。
        """
        # AIからの応答（Markdown形式）を行ごとに分割してリストに変換
        values = [[line] for line in analysis_text.split('\n')]
        body = {
            'values': values
        }
        
        # 最初のセルに書き込む
        range_name = f"'{sheet_title}'!A1"
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        # 書き込んだセルに書式設定（テキストの折り返し）を適用
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': self.get_sheet_id_by_title(spreadsheet_id, sheet_title),
                        'startRowIndex': 0,
                        'endRowIndex': len(values),
                        'startColumnIndex': 0,
                        'endColumnIndex': len(values[0])
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'wrapStrategy': 'WRAP'
                        }
                    },
                    'fields': 'userEnteredFormat.wrapStrategy'
                }
            }
        ]
        
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        print(f"分析結果がシートID {sheet_id} に書き込まれました。")
    
    def format_sheet(self, spreadsheet_id, header_row_values, sheet_id_to_format=0):
        """
        指定されたスプレッドシートのシートに対して、動画説明文の列にテキストラッピングと幅調整、
        そして全てのデータ行の高さを約40ピクセルに設定します。
        """
        description_col_index = -1
        try:
            description_col_index = header_row_values.index('動画説明文')
        except ValueError:
            print("警告: '動画説明文'カラムが見つかりませんでした。そのカラムのフォーマットは適用されません。")
            # カラムが見つからなくても、行の高さ調整は適用されるように、ここでreturnしない
            pass

        requests = []

        # 1. 全てのデータ行の高さ（ヘッダー行を除く）を約40ピクセルに設定するリクエスト
        # ヘッダー行 (RowIndex 0) は含まず、データがある行から適用します。
        # 'endIndex' は十分大きな値を設定し、未来のデータ追加にも対応できるようにします。
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id_to_format, # 通常、最初のシートはsheetId 0
                    'dimension': 'ROWS',
                    'startIndex': 1, # ヘッダー行（インデックス0）の次から適用
                    'endIndex': 2000, # 例: 2000行目まで適用（必要に応じて調整）
                },
                'properties': {
                    'pixelSize': 40 # 行の高さを40ピクセルに設定
                },
                'fields': 'pixelSize'
            }
        })

        if description_col_index != -1: # '動画説明文'カラムが見つかった場合のみ適用
            # 2. '動画説明文'カラムにテキストラッピングを設定するリクエスト
            # 固定された行の高さの中でテキストが可能な限り折り返されるようにします。
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id_to_format, # 通常、最初のシートはsheetId 0
                        'startRowIndex': 0, # ヘッダー行を含む全ての行に適用
                        'endRowIndex': 2000, # 例: 2000行目まで適用（必要に応じて調整）
                        'startColumnIndex': description_col_index,
                        'endColumnIndex': description_col_index + 1,
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'wrapStrategy': 'WRAP' # テキストの折り返しを有効にする
                        }
                    },
                    'fields': 'userEnteredFormat.wrapStrategy'
                }
            })

            # 3. '動画説明文'カラムの幅を設定するリクエスト（例: 400ピクセル）
            # これはテキストラッピングと組み合わせて表示を改善します。
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id_to_format,
                        'dimension': 'COLUMNS',
                        'startIndex': description_col_index,
                        'endIndex': description_col_index + 1,
                    },
                    'properties': {
                        'pixelSize': 400 # 例: 400ピクセルに設定 (適宜調整)
                    },
                    'fields': 'pixelSize'
                }
            })

        if not requests: # もし何もフォーマットリクエストが追加されなかった場合
            print("フォーマットリクエストは生成されませんでした。")
            return

        # バッチアップデートを実行
        try:
            body = {'requests': requests}
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            print("シートのフォーマットを適用しました。")
        except Exception as e:
            print(f"シートのフォーマット中にエラーが発生しました: {e}")