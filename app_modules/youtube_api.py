# youtube_api.py

import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import unquote
import re
from datetime import datetime

class YouTubeAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def get_channel_id_from_url(self, channel_url):
        """
        YouTubeチャンネルのURLからチャンネルIDを取得する
        """
        try:
            # URLからチャンネルハンドルを抽出 (例: @handle)
            match = re.search(r'@([^/]+)', channel_url)
            if not match:
                return None
            
            handle = unquote(match.group(1))

            # ハンドルを使ってチャンネル情報を取得
            response = self.youtube.channels().list(
                part='id',
                forHandle=handle
            ).execute()

            if 'items' in response and len(response['items']) > 0:
                return response['items'][0]['id']
            else:
                return None
        except Exception as e:
            print(f"URLからのチャンネルID取得中にエラーが発生しました: {e}")
            return None
        
    def search_videos_by_channel(self, channel_url, order, max_results):
        """
        指定されたチャンネルURLの動画を検索する
        """
        channel_id = self.get_channel_id_from_url(channel_url)
        if not channel_id:
            return None

        try:
            # チャンネルのアップロード再生リストIDを取得
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()

            if not channel_response['items']:
                return None

            playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # 再生リストから動画を取得
            playlist_items_response = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=max_results,
            ).execute()

            video_ids = [item['contentDetails']['videoId'] for item in playlist_items_response['items']]

            if not video_ids:
                return []

            # 動画の詳細情報を取得
            videos_response = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()

            # データを整形
            videos_data = self._parse_videos_data(videos_response['items'])

            # 再生回数順、新着順でソート
            if order == 'viewCount':
                videos_data = sorted(videos_data, key=lambda x: int(x.get('再生回数', 0)), reverse=True)
            elif order == 'date':
                 videos_data = sorted(videos_data, key=lambda x: x.get('公開日', ''), reverse=True)


            return videos_data

        except Exception as e:
            print(f"チャンネル動画の検索中にエラーが発生しました: {e}")
            return None

    def _parse_videos_data(self, items):
        """
        APIレスポンスから動画データを抽出し、整形する
        """
        videos_data = []
        for item in items:
            video_id = item['id']
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            # 日付形式を変換
            published_at_str = snippet.get('publishedAt')
            published_at_dt = datetime.strptime(published_at_str, '%Y-%m-%dT%H:%M:%SZ')
            formatted_date = published_at_dt.strftime('%Y/%m/%d')

            video_data = {
                '動画タイトル': snippet.get('title'),
                '動画ID': video_id,
                'チャンネル名': snippet.get('channelTitle'),
                'チャンネルID': snippet.get('channelId'),
                '公開日': formatted_date,
                '再生回数': statistics.get('viewCount'),
                '高評価数': statistics.get('likeCount'),
                'コメント数': statistics.get('commentCount'),
                '動画説明文': snippet.get('description'),
                'サムネイルURL': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                '動画の長さ': content_details.get('duration'),
                '動画リンク': f"https://www.youtube.com/watch?v={video_id}",
                'チャンネルリンク': f"https://www.youtube.com/channel/{snippet.get('channelId')}"
            }
            videos_data.append(video_data)
        return videos_data

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