"""Instagram Graph API 로 '내 계정' 게시물(릴스)의 댓글을 가져온다.

인스타그램 공식 API 는 다른 사람 게시물의 댓글을 주지 않는다.
다른 사람 릴스 반응은 CSV(sources/csv_source.py)로 넣는다.
필요: 비즈니스/크리에이터 계정, IG_ACCESS_TOKEN, IG_USER_ID (권한 instagram_basic,
instagram_manage_comments, pages_show_list, pages_read_engagement)
"""
from __future__ import annotations

import os

import requests

BASE = "https://graph.facebook.com/v21.0"


def _get(path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{BASE}/{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch(game: str = "내 릴스", media_limit: int = 5) -> tuple[list[dict], list[dict]]:
    if not (os.getenv("IG_ACCESS_TOKEN") and os.getenv("IG_USER_ID")):
        raise SystemExit("IG_ACCESS_TOKEN / IG_USER_ID 가 .env 에 없습니다.")
    media = _get(f"{os.environ['IG_USER_ID']}/media",
                 fields="id,caption,permalink,like_count,comments_count", limit=media_limit)
    videos, comments = [], []
    for m in media.get("data", []):
        videos.append({"id": m["id"], "platform": "instagram", "game": game,
                       "title": (m.get("caption") or "")[:60], "url": m.get("permalink", ""),
                       "views": None, "likes": m.get("like_count", 0)})
        data = _get(f"{m['id']}/comments", fields="id,text,username,like_count", limit=50)
        for c in data.get("data", []):
            comments.append({"id": c["id"], "platform": "instagram", "video_id": m["id"],
                             "game": game, "author": c.get("username", ""),
                             "text": c.get("text", ""), "likes": c.get("like_count", 0)})
    return videos, comments


# ---------- 자동 답글 모드 ----------
def _post(path: str, **data) -> dict:
    data["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{BASE}/{path}", data=data, timeout=15)
    r.raise_for_status()
    return r.json()


def reply(comment_id: str, text: str) -> dict:
    return _post(f"{comment_id}/replies", message=text)


def hide(comment_id: str) -> dict:
    return _post(comment_id, hide="true")
