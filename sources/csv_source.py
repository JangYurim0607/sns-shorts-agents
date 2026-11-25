"""CSV 로 어떤 SNS 든 댓글을 넣는다. (인스타 남의 릴스, 틱톡 등 API 로 못 가져오는 것)

열: platform, video_title, video_url, game, author, text, likes
data/comments_template.csv 를 복사해서 채우면 된다.
"""
from __future__ import annotations

import csv
import hashlib


def fetch(path: str) -> tuple[list[dict], list[dict]]:
    videos: dict[str, dict] = {}
    comments = []
    with open(path, encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            url = row.get("video_url", "").strip() or row.get("video_title", "")
            vid = "v" + hashlib.md5(url.encode()).hexdigest()[:8]
            videos.setdefault(vid, {
                "id": vid, "platform": row.get("platform", "etc"), "game": row.get("game", ""),
                "title": row.get("video_title", ""), "url": row.get("video_url", ""),
                "views": None, "likes": None,
            })
            comments.append({
                "id": f"csv{i:04d}", "platform": row.get("platform", "etc"), "video_id": vid,
                "game": row.get("game", ""), "author": row.get("author", ""),
                "text": row.get("text", ""), "likes": int(row.get("likes") or 0),
            })
    return list(videos.values()), comments
