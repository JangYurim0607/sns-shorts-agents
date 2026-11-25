"""YouTube Data API v3 로 '요즘 인기 있는 게임 쇼츠'와 그 댓글을 가져온다.

공개 영상의 댓글은 API 키만 있으면 읽을 수 있다. (.env 의 YOUTUBE_API_KEY)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

BASE = "https://www.googleapis.com/youtube/v3"


def _get(path: str, **params) -> dict:
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    r = requests.get(f"{BASE}/{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch(games: list[str], days: int = 7, videos_per_game: int = 3,
          comments_per_video: int = 50) -> tuple[list[dict], list[dict]]:
    """게임 이름마다 최근 N일 인기 쇼츠를 찾고 댓글을 모은다."""
    if not os.getenv("YOUTUBE_API_KEY"):
        raise SystemExit("YOUTUBE_API_KEY 가 .env 에 없습니다. --source sample 로 실행하세요.")
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    videos, comments = [], []
    for game in games:
        found = _get("search", part="snippet", q=f"{game} shorts", type="video",
                     videoDuration="short", order="viewCount", publishedAfter=after,
                     regionCode="KR", relevanceLanguage="ko", maxResults=videos_per_game)
        ids = [it["id"]["videoId"] for it in found.get("items", [])]
        if not ids:
            continue
        stats = _get("videos", part="snippet,statistics", id=",".join(ids))
        for v in stats.get("items", []):
            vid = v["id"]
            videos.append({
                "id": vid, "platform": "youtube", "game": game,
                "title": v["snippet"]["title"],
                "url": f"https://www.youtube.com/shorts/{vid}",
                "views": int(v["statistics"].get("viewCount", 0)),
                "likes": int(v["statistics"].get("likeCount", 0)),
            })
            try:
                th = _get("commentThreads", part="snippet", videoId=vid, order="relevance",
                          maxResults=min(comments_per_video, 100), textFormat="plainText")
            except requests.HTTPError:  # 댓글 막힌 영상
                continue
            for t in th.get("items", []):
                s = t["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "id": t["id"], "platform": "youtube", "video_id": vid, "game": game,
                    "author": s.get("authorDisplayName", ""), "text": s.get("textDisplay", ""),
                    "likes": int(s.get("likeCount", 0)),
                })
    return videos, comments


# ---------- 자동 답글 모드: 내 채널 ----------
def fetch_my_comments(channel_id: str | None = None, limit: int = 50) -> tuple[list[dict], list[dict]]:
    """내 채널 영상에 달린 최근 댓글. 읽기는 API 키로 된다."""
    channel_id = channel_id or os.environ["YOUTUBE_CHANNEL_ID"]
    th = _get("commentThreads", part="snippet", allThreadsRelatedToChannelId=channel_id,
              order="time", maxResults=min(limit, 100), textFormat="plainText")
    videos, comments = {}, []
    for t in th.get("items", []):
        s = t["snippet"]["topLevelComment"]["snippet"]
        vid = t["snippet"].get("videoId", "")
        videos.setdefault(vid, {"id": vid, "platform": "youtube", "title": vid,
                                "url": f"https://www.youtube.com/shorts/{vid}"})
        comments.append({"id": t["id"], "platform": "youtube", "video_id": vid,
                         "author": s.get("authorDisplayName", ""), "text": s.get("textDisplay", ""),
                         "likes": int(s.get("likeCount", 0))})
    return list(videos.values()), comments


def _oauth_headers() -> dict:
    """답글 달기·숨기기는 API 키로 안 되고, 채널 주인의 OAuth 토큰(youtube.force-ssl)이 필요하다."""
    token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    if not token:
        raise SystemExit("YOUTUBE_OAUTH_TOKEN 이 없습니다. 유튜브 답글 게시는 dry-run 으로만 됩니다.")
    return {"Authorization": f"Bearer {token}"}


def reply(parent_id: str, text: str) -> dict:
    r = requests.post(f"{BASE}/comments", params={"part": "snippet"}, headers=_oauth_headers(),
                      json={"snippet": {"parentId": parent_id, "textOriginal": text}}, timeout=15)
    r.raise_for_status()
    return r.json()


def hide(comment_id: str) -> None:
    """스팸은 '검토 대기'로 돌려서 공개 화면에서 숨긴다."""
    r = requests.post(f"{BASE}/comments/setModerationStatus", headers=_oauth_headers(),
                      params={"id": comment_id, "moderationStatus": "heldForReview"}, timeout=15)
    r.raise_for_status()
