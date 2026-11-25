"""② 분류 에이전트: 댓글이 숏츠 기획에 어떤 신호인지 나눈다."""
from __future__ import annotations

import re

from .base import Agent

LABELS = {
    "scene": "터진 장면",
    "game_interest": "게임 관심",
    "request": "요청",
    "complaint": "불만",
    "praise": "단순 반응",
    "spam": "스팸",
}
HOT_LIKES = 1000  # 좋아요가 이 이상이면 우선순위를 올린다


class ClassifierAgent(Agent):
    name = "classifier"

    def classify(self, c: dict) -> dict:
        if self.use_llm:
            out = self.ask_llm(
                f"게임: {c['game']} / 플랫폼: {c['platform']} / 좋아요: {c.get('likes')}\n"
                f"댓글: {c['text']}\n가능한 label: {list(LABELS)}. "
                "키: label, priority(1~3), keywords(list), reason")
        else:
            out = self._rule_based(c)
        out["comment_id"] = c["id"]
        self.send("orchestrator", "classified", out)
        return out

    # ---- 데모용 규칙. SKILL.md 를 채우고 API 키를 넣으면 LLM 판단으로 바뀐다 ----
    @staticmethod
    def _rule_based(c: dict) -> dict:
        t, likes = c["text"], c.get("likes") or 0
        stamp = re.findall(r"\d{1,2}:\d{2}", t)

        def res(label, prio, reason):
            kw = stamp + [w for w in re.findall(r"[가-힣A-Za-z]{2,}", t)
                          if w not in {"진짜", "너무", "해주세요", "알려주세요", "이거"}][:3]
            if label in ("scene", "request", "game_interest") and likes >= HOT_LIKES:
                prio = 1
            return {"label": label, "priority": prio, "keywords": kw, "reason": reason}

        if re.search(r"https?://|맞팔|선팔|부업|무료로 받는|DM주세요|💰", t):
            return res("spam", 3, "홍보·링크")
        if re.search(r"해주세요|해줘요|해주라|버전도|다음엔|2편|편도", t):
            return res("request", 2, "다음 영상 요청")
        if re.search(r"길어|늘어짐|자막.*(작|안 보)|낚시|소리.*커|별로", t):
            return res("complaint", 2, "영상 형식 불만")
        if re.search(r"\?|어떻게|무슨 게임|게임 이름|무슨 모드|할 수 있|방법", t):
            return res("game_interest", 2, "게임·방법 질문")
        if stamp or re.search(r"순간|장면|반전|나올 때|마지막|표정|미쳤다", t):
            return res("scene", 2, "특정 장면 언급")
        return res("praise", 3, "구체적 내용 없는 반응")
