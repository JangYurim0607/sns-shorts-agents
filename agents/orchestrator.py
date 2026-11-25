"""오케스트레이터: 5개 에이전트에게 일을 나눠주고 결과를 모은다.

  ① Collector ─▶ ② Classifier ─▶ ③ Planner ⇄ ④ Reviewer ─▶ ⑤ Reporter
   (유튜브·인스타·CSV)   (댓글 수만큼 병렬)            └─▶ 사람 확인
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from .base import ROOT, Bus
from .classifier import ClassifierAgent
from .collector import CollectorAgent
from .planner import PlannerAgent
from .reporter import ReporterAgent
from .reviewer import ReviewerAgent

MAX_REVISIONS = 2


class Orchestrator:
    def __init__(self, source="sample", games=None, csv_path=None, days=7, workers=4):
        self.bus = Bus()
        self.collector = CollectorAgent(self.bus, source=source, games=games, csv_path=csv_path, days=days)
        self.classifier = ClassifierAgent(self.bus)
        self.planner = PlannerAgent(self.bus)
        self.reviewer = ReviewerAgent(self.bus)
        self.reporter = ReporterAgent(self.bus)
        self.source, self.workers = source, workers

    def _classify(self, c):
        self.bus.post("orchestrator", "classifier", "assign", {"comment_id": c["id"], "text": c["text"]})
        return {"c": c, "cls": self.classifier.classify(c)}

    def run(self) -> dict:
        self.bus.post("orchestrator", "collector", "start", {"source": self.source})
        video_list, comments = self.collector.run()
        videos = {v["id"]: v for v in video_list}

        with ThreadPoolExecutor(max_workers=self.workers) as pool:  # 댓글별 병렬 분류
            signals = [s for s in pool.map(self._classify, comments) if s["cls"]["label"] != "spam"]

        self.bus.post("orchestrator", "planner", "assign", {"signals": len(signals)})
        ideas = self.planner.plan(signals, videos)
        for idea in ideas:
            r = self.reviewer.review(idea, videos)
            n = 0
            while r["verdict"] == "revise" and n < MAX_REVISIONS:
                idea = self.planner.revise(idea, r["note"])
                r = self.reviewer.review(idea, videos)
                n += 1
            idea["status"] = "escalate" if r["verdict"] == "revise" else r["verdict"]
            idea["note"] = r["note"]
            if idea["status"] == "escalate":
                self.bus.post("orchestrator", "human", "escalate", {"idea_id": idea["id"], "note": r["note"]})

        keywords = self.planner.keywords(signals)
        self.bus.post("orchestrator", "reporter", "assign", {"ideas": len(ideas)})
        md = self.reporter.write(video_list, comments, signals, ideas, keywords)

        modes = {a.name: ("LLM+SKILL.md" if a.use_llm else "rule-based")
                 for a in [self.classifier, self.planner, self.reviewer]}
        report = {"videos": video_list, "comments": comments,
                  "signals": [{"comment_id": s["c"]["id"], **s["cls"]} for s in signals],
                  "ideas": ideas, "keywords": keywords, "agent_modes": modes,
                  "plan_md": md, "events": self.bus.events}
        (ROOT / "runs").mkdir(exist_ok=True)
        (ROOT / "runs" / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (ROOT / "web" / "latest.js").write_text("window.RUN = " + json.dumps(report, ensure_ascii=False) + ";",
                                                encoding="utf-8")
        return report
