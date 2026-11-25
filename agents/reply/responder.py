"""③ 답글 작성 에이전트: 분류 결과에 맞춰 답글 초안을 쓴다."""
from __future__ import annotations

import re

from ..base import Agent

TEMPLATES = {
    "question": "@{u} 질문 감사해요! {hint} 더 궁금한 점은 DM으로 편하게 물어봐 주세요 🙌",
    "praise": "@{u} 좋게 봐주셔서 정말 감사해요 😊 다음 콘텐츠도 기대해 주세요!",
    "complaint": "@{u} 불편을 드려 죄송해요. 상황을 자세히 확인하고 싶어서 DM 한 번 부탁드려도 될까요?",
    "collab": "@{u} 제안 감사합니다! 프로필의 이메일로 내용 보내주시면 확인 후 연락드릴게요.",
    "other": "@{u} 댓글 남겨주셔서 감사해요!",
}


class ResponderAgent(Agent):
    name = "responder"

    def draft(self, c: dict, cls: dict, feedback: str | None = None) -> dict:
        label = cls["label"]
        if label == "spam":
            out = {"reply": None, "action": "hide"}
        elif self.use_llm:
            out = self.ask_llm(
                f"댓글: {c['text']} (작성자 @{c['username']})\n분류: {cls}\n"
                + (f"검수 피드백: {feedback}\n" if feedback else "")
                + "키: reply, action('reply')"
            )
        else:
            place = {"youtube": "설명란", "instagram": "캡션", "tiktok": "고정 댓글"}.get(c.get("platform"), "게시물 본문")
            if label != "question":
                hint = ""
            elif "언제" in c["text"]:
                hint = "다음 영상은 지금 준비하고 있어요."
            else:
                hint = f"{place}에 자세히 적어두었어요."
            reply = TEMPLATES.get(label, TEMPLATES["other"]).format(u=c["username"], hint=hint)
            if feedback and "길이" in feedback:
                # 마지막 문장을 빼서 짧게 고쳐 쓴다
                parts = re.split(r"(?<=[.!?])\s+", reply)
                reply = " ".join(parts[:-1]) + " 🙌"
            out = {"reply": reply, "action": "reply"}
        out["comment_id"] = c["id"]
        out["revision"] = 1 if feedback is None else 2
        self.send("moderator", "draft", out)
        return out
