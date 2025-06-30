# youtube_api.py

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class YouTubeAPI:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key, credentials=None)

    def _parse_iso8601_duration(self, duration_iso):
        duration_seconds = 0
        if 'PT' not in duration_iso:
            return 0
        temp_duration = duration_iso.replace('PT', '')
        if 'H' in temp_duration:
            parts = temp_duration.split('H')
            try:
                duration_seconds += int(parts[0]) * 3600
            except ValueError: pass
            temp_duration = parts[1] if len(parts) > 1 else ''
        if 'M' in temp_duration:
            parts = temp_duration.split('M')
            try:
                duration_seconds += int(parts[0]) * 60
            except ValueError: pass
            temp_duration = parts[1] if len(parts) > 1 else ''
        if 'S' in temp_duration:
            parts = temp_duration.split('S')
            try:
                duration_seconds += int(parts[0])
            except ValueError: pass
        return duration_seconds

    # メソッドの定義に新しい引数を追加
    def search_videos_data(self, query, video_type='any', max_results=20, order='relevance', published_after=None, published_before=None):
        video_data = []
        next_page_token = None
        
        # 取得したい件数に達するまでループ
        while len(video_data) < max_results:
            # 1回のリクエストで取得する件数を計算 (API上限は50)
            num_to_fetch = min(max_results - len(video_data), 50)

            try:
                # APIに渡すパラメータを辞書として定義
                search_params = {
                    'q': query,
                    'type': 'video',
                    'part': 'id,snippet',
                    'maxResults': num_to_fetch,
                    'order': order,
                    'pageToken': next_page_token
                }

                # 期間指定があれば、パラメータに追加（RFC 3339形式に変換）
                if published_after and published_after.strip():
                    search_params['publishedAfter'] = f"{published_after.strip()}T00:00:00Z"
                if published_before and published_before.strip():
                    search_params['publishedBefore'] = f"{published_before.strip()}T23:59:59Z"

                # APIを呼び出し
                search_response = self.youtube.search().list(**search_params).execute()

                video_ids = [item['id']['videoId'] for item in search_response.get('items', []) if item['id']['kind'] == 'youtube#video']

                if not video_ids:
                    break

                videos_response = self.youtube.videos().list(
                    id=','.join(video_ids),
                    part='snippet,contentDetails,statistics'
                ).execute()

                for video_item in videos_response.get('items', []):
                    duration_iso = video_item['contentDetails'].get('duration', 'PT0S')
                    duration_seconds = self._parse_iso8601_duration(duration_iso)
                    is_short = "Short" if duration_seconds <= 60 else "Long"

                    # フィルタリング条件
                    if video_type == 'any' or \
                       (video_type == 'short' and is_short == "Short") or \
                       (video_type == 'long' and is_short == "Long"):
                        
                        video_data.append({
                            'タイトル': video_item['snippet']['title'],
                            'URL': f"https://www.youtube.com/watch?v={video_item['id']}",
                            'チャンネル名': video_item['snippet']['channelTitle'],
                            '公開日時': video_item['snippet']['publishedAt'],
                            '再生回数': video_item['statistics'].get('viewCount', 'N/A'),
                            '高評価数': video_item['statistics'].get('likeCount', 'N/A'),
                            'コメント数': video_item['statistics'].get('commentCount', 'N/A'),
                            '動画説明文': video_item['snippet'].get('description', 'N/A'),
                            'サムネイルURL': video_item['snippet']['thumbnails'].get('high', {}).get('url', 'N/A'),
                            '動画タイプ': is_short
                        })

                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break # 次のページがなければ終了

            except HttpError as e:
                print(f"APIエラーが発生しました: {e}")
                break
            except Exception as e:
                print(f"予期せぬエラーが発生しました: {e}")
                break

        return video_data[:max_results]