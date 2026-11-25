"""④ 검수 에이전트: 답글 초안을 검사해 승인 / 수정 요청 / 사람에게 넘김을 결정한다."""
from __future__ import annotations

import re

from ..base import Agent

BANNED = ["무조건", "100%", "환불해 드릴게요", "보장"]
MAX_LEN = 60


class ModeratorAgent(Agent):
    name = "moderator"

    def review(self, c: dict, cls: dict, draft: dict) -> dict:
        if draft["action"] == "hide":
            verdict = {"verdict": "approve", "note": "스팸 → 숨김 처리"}
        elif self.use_llm:
            verdict = self.ask_llm(
                f"원댓글: {c['text']}\n분류: {cls}\n답글 초안: {draft['reply']}\n"
                "키: verdict('approve'|'revise'|'escalate'), note"
            )
        else:
            verdict = self._rule_based(cls, draft["reply"] or "", draft["revision"])
        verdict["comment_id"] = c["id"]
        to = "responder" if verdict["verdict"] == "revise" else "orchestrator"
        self.send(to, "review", verdict)
        return verdict

    @staticmethod
    def _rule_based(cls: dict, reply: str, revision: int) -> dict:
        if any(b in reply for b in BANNED):
            return {"verdict": "escalate", "note": "약속성 표현 포함 → 사람 확인 필요"}
        if cls["label"] == "complaint" and cls.get("priority") == 1 and re.search(r"환불|법적|신고", reply):
            return {"verdict": "escalate", "note": "민감한 불만"}
        if len(reply) > MAX_LEN and revision == 1:
            return {"verdict": "revise", "note": f"길이 {len(reply)}자 > {MAX_LEN}자, 줄여주세요"}
        if cls["label"] == "collab":
            return {"verdict": "escalate", "note": "협업 제안은 계정 주인이 직접 확인"}
        return {"verdict": "approve", "note": "톤·길이 OK"}
