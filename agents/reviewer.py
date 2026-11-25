"""④ 검수 에이전트: 기획 아이디어를 승인 / 수정 요청 / 사람 확인으로 나눈다."""
from __future__ import annotations

import os
from difflib import SequenceMatcher

from .base import Agent

MAX_TITLE = 22  # 숏츠 제목 글자 수 상한
SIMILAR = 0.6   # 원본 영상 제목과 이 이상 비슷하면 베끼기로 본다


def my_games() -> list[str]:
    """내가 직접 플레이·녹화할 수 있는 게임 (.env 의 MY_GAMES, 쉼표 구분)."""
    raw = os.getenv("MY_GAMES", "Grow a Garden,99 Nights in the Forest")
    return [g.strip() for g in raw.split(",") if g.strip()]


class ReviewerAgent(Agent):
    name = "reviewer"

    def review(self, idea: dict, videos: dict) -> dict:
        if self.use_llm:
            src = [videos[v]["title"] for v in idea["source_videos"]]
            out = self.ask_llm(f"아이디어: {idea}\n원본 영상 제목: {src}\n내가 할 수 있는 게임: {my_games()}\n"
                               "키: verdict('approve'|'revise'|'escalate'), note")
        else:
            out = self._rule_based(idea, videos)
        out["idea_id"] = idea["id"]
        self.send("planner" if out["verdict"] == "revise" else "orchestrator", "review", out)
        return out

    @staticmethod
    def _rule_based(idea, videos):
        if idea["game"] not in my_games():
            return {"verdict": "escalate", "note": f"{idea['game']} 은(는) 내 플레이 목록에 없음, 직접 확인"}
        if len(idea["evidence"]) < 2:
            return {"verdict": "revise", "note": "근거 댓글이 1개뿐"}
        for v in idea["source_videos"]:
            if SequenceMatcher(None, idea["title"], videos[v]["title"]).ratio() >= SIMILAR:
                return {"verdict": "revise", "note": "원본 영상 제목과 너무 비슷함"}
        if len(idea["title"]) > MAX_TITLE:
            return {"verdict": "revise", "note": f"제목 {len(idea['title'])}자, {MAX_TITLE}자 이하로 길이 줄이기"}
        return {"verdict": "approve", "note": "근거·제목 OK"}
