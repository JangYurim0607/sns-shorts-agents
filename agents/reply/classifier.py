"""② 분류 에이전트: 댓글 유형·감정·우선순위를 판단한다."""
from __future__ import annotations

import re

from ..base import Agent

LABELS = ["question", "praise", "complaint", "collab", "spam", "other"]


class ClassifierAgent(Agent):
    name = "reply_classifier"

    def classify(self, c: dict) -> dict:
        if self.use_llm:
            out = self.ask_llm(
                f"댓글 작성자: @{c['username']}\n댓글: {c['text']}\n"
                f"가능한 label: {LABELS}. 키: label, sentiment, priority(1~3), reason"
            )
        else:
            out = self._rule_based(c["text"])
        out["comment_id"] = c["id"]
        self.send("orchestrator", "classified", out)
        return out

    # ---- 데모용 규칙 (SKILL.md 를 채우고 API 키를 넣으면 LLM 판단으로 대체됨) ----
    @staticmethod
    def _rule_based(text: str) -> dict:
        t = text.lower()
        if re.search(r"https?://|팔로우.*맞팔|선팔|부업|수익|dm주세요|💰|무료.*이벤트", t):
            return {"label": "spam", "sentiment": "neutral", "priority": 3, "reason": "링크/홍보성 문구"}
        if re.search(r"협업|제휴|광고 문의|콜라보|비즈니스", t):
            return {"label": "collab", "sentiment": "positive", "priority": 1, "reason": "협업 제안"}
        if re.search(r"별로|실망|안 돼|안돼|오류|버그|환불|느려|최악|불편", t):
            return {"label": "complaint", "sentiment": "negative", "priority": 1, "reason": "불만 표현"}
        if re.search(r"\?|어떻게|언제|어디|뭐예요|되나요|있나요|알려", t):
            return {"label": "question", "sentiment": "neutral", "priority": 2, "reason": "질문 형태"}
        if re.search(r"좋아|최고|대박|멋|예쁘|귀엽|감사|❤|😍|👍|ㅋㅋ", t):
            return {"label": "praise", "sentiment": "positive", "priority": 3, "reason": "긍정 반응"}
        return {"label": "other", "sentiment": "neutral", "priority": 3, "reason": "기타"}
