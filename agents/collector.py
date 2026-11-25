"""① 수집 에이전트: 인기 게임 숏츠와 댓글을 SNS 에서 모은다."""
from __future__ import annotations

import json

from .base import ROOT, Agent

MIN_LEN = 3  # 이보다 짧은 댓글은 개수만 센다


class CollectorAgent(Agent):
    name = "collector"

    def __init__(self, bus, source="sample", games=None, csv_path=None, days=7, **kw):
        super().__init__(bus, use_llm=False)
        self.source, self.games, self.csv_path, self.days = source, games or [], csv_path, days

    def _fetch(self):
        if self.source == "youtube":
            from sources import youtube
            return youtube.fetch(self.games, days=self.days)
        if self.source == "instagram":
            from sources import instagram
            return instagram.fetch()
        if self.source == "csv":
            from sources import csv_source
            return csv_source.fetch(self.csv_path)
        data = json.loads((ROOT / "data" / "sample_comments.json").read_text(encoding="utf-8"))
        vids = {v["id"]: v for v in data["videos"]}
        comments = [{**c, "platform": vids[c["video_id"]]["platform"],
                     "game": vids[c["video_id"]]["game"]} for c in data["comments"]]
        return data["videos"], comments

    def run(self):
        videos, comments = self._fetch()
        short = [c for c in comments if len(c["text"].strip()) < MIN_LEN]
        usable = [c for c in comments if len(c["text"].strip()) >= MIN_LEN]
        usable.sort(key=lambda c: c.get("likes") or 0, reverse=True)  # 좋아요 많은 순
        self.send("orchestrator", "collected", {
            "source": self.source, "videos": len(videos),
            "platforms": sorted({v["platform"] for v in videos}),
            "comments": len(comments), "too_short": len(short)})
        return videos, usable
