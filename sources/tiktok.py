"""틱톡: 일반 개발자용 공개 API 로는 댓글을 읽거나 답글을 달 수 없다.

그래서 댓글은 CSV(sources/csv_source.py)로 넣고,
답글은 plans/tiktok_replies.csv 로 저장해서 앱에서 직접 붙여넣는다.
"""
from __future__ import annotations

import csv

from agents.base import ROOT

OUT = ROOT / "plans" / "tiktok_replies.csv"


HEADER = ["video_id", "comment_id", "author", "comment", "action", "reply"]


def reset() -> None:
    """실행할 때마다 새 목록으로 시작한다."""
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(HEADER)


def queue_reply(comment: dict, text: str | None, action: str) -> str:
    if not OUT.exists():
        reset()
    with OUT.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([comment.get("video_id"), comment["id"], comment.get("author"),
                    comment["text"], action, text or ""])
    return "manual"
