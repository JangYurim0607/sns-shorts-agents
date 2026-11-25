"""자동 답글 모드 오케스트레이터 (처음 버전 구조를 SNS 전체로 넓힌 것).

  ① 수집 ─▶ ② 분류 ─▶ ③ 답글 ⇄ ④ 검수 ─▶ ⑤ 게시 (유튜브 / 인스타 / 틱톡)
                                    └─▶ 사람 확인
댓글마다 ②→③→④ 파이프라인이 병렬로 돈다.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from ..base import ROOT, Bus
from .classifier import ClassifierAgent
from .moderator import ModeratorAgent
from .publisher import PublisherAgent
from .responder import ResponderAgent

MAX_REVISIONS = 1
STATE = ROOT / "runs" / "replied_ids.json"


def _load(source: str, csv_path: str | None):
    if source == "youtube":
        from sources import youtube
        return youtube.fetch_my_comments()
    if source == "instagram":
        from sources import instagram
        return instagram.fetch()
    if source == "csv":  # 틱톡 등
        from sources import csv_source
        return csv_source.fetch(csv_path)
    data = json.loads((ROOT / "data" / "my_comments.json").read_text(encoding="utf-8"))
    vids = {v["id"]: v for v in data["videos"]}
    return data["videos"], [{**c, "platform": vids[c["video_id"]]["platform"]} for c in data["comments"]]


class ReplyOrchestrator:
    def __init__(self, source="sample", csv_path=None, live_post=False, workers=4):
        self.bus = Bus()
        self.classifier = ClassifierAgent(self.bus)
        self.responder = ResponderAgent(self.bus)
        self.moderator = ModeratorAgent(self.bus)
        self.publisher = PublisherAgent(self.bus, live=live_post)
        self.source, self.csv_path, self.workers = source, csv_path, workers

    def _pipeline(self, c: dict) -> dict:
        c.setdefault("username", c.get("author", "user"))
        self.bus.post("orchestrator", "reply_classifier", "assign",
                      {"comment_id": c["id"], "platform": c["platform"], "text": c["text"]})
        cls = self.classifier.classify(c)
        draft = self.responder.draft(c, cls)
        review = self.moderator.review(c, cls, draft)
        n = 0
        while review["verdict"] == "revise" and n < MAX_REVISIONS:
            draft = self.responder.draft(c, cls, feedback=review["note"])
            review = self.moderator.review(c, cls, draft)
            n += 1
        if review["verdict"] == "revise":
            review["verdict"] = "escalate"
        res = {"comment": c, "class": cls, "draft": draft, "review": review}
        if review["verdict"] == "approve":
            res["publish"] = self.publisher.publish(c, draft)
        else:
            self.bus.post("orchestrator", "human", "escalate", {"comment_id": c["id"], "note": review["note"]})
            res["publish"] = {"status": "needs-human", "platform": c["platform"]}
        return res

    def run(self, reset=True) -> dict:
        self.bus.post("orchestrator", "collector", "start", {"source": self.source})
        videos, comments = _load(self.source, self.csv_path)
        if any(c["platform"] == "tiktok" for c in comments):
            from sources import tiktok
            tiktok.reset()
        done = set() if reset or not STATE.exists() else set(json.loads(STATE.read_text()))
        comments = [c for c in comments if c["id"] not in done]
        self.bus.post("collector", "orchestrator", "collected",
                      {"source": self.source, "videos": len(videos), "new": len(comments),
                       "platforms": sorted({c["platform"] for c in comments})})
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(self._pipeline, comments))
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(sorted(done | {r["comment"]["id"] for r in results
                                                   if r["publish"]["status"] != "needs-human"})))
        summary = {}
        for r in results:
            summary[r["publish"]["status"]] = summary.get(r["publish"]["status"], 0) + 1
        self.bus.post("orchestrator", "report", "summary", summary)
        modes = {a.name: ("LLM+SKILL.md" if a.use_llm else "rule-based")
                 for a in [self.classifier, self.responder, self.moderator]}
        report = {"summary": summary, "agent_modes": modes, "videos": videos,
                  "results": results, "events": self.bus.events}
        (ROOT / "runs" / "latest_reply.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (ROOT / "web" / "latest_reply.js").write_text("window.RUN = " + json.dumps(report, ensure_ascii=False) + ";",
                                                      encoding="utf-8")
        return report
