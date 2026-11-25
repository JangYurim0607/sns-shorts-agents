"""⑤ 게시 에이전트: 승인된 답글을 플랫폼에 맞게 올린다.

  youtube   : 답글 게시 / 스팸은 '검토 대기'로 숨김 (채널 주인 OAuth 토큰 필요)
  instagram : 답글 게시 / 스팸 숨김 (Graph API 토큰 필요)
  tiktok    : 공개 API 가 없어서 plans/tiktok_replies.csv 에 저장 → 앱에서 직접 붙여넣기
  --post 없이 실행하면 youtube·instagram 도 실제로 올리지 않는다(dry-run).
"""
from __future__ import annotations

from ..base import Agent


class PublisherAgent(Agent):
    name = "publisher"

    def __init__(self, bus, live: bool = False, **kw):
        super().__init__(bus, use_llm=False)
        self.live = live

    def publish(self, c: dict, draft: dict) -> dict:
        platform, hide = c["platform"], draft["action"] == "hide"
        if platform == "tiktok":
            from sources import tiktok
            status = tiktok.queue_reply(c, draft.get("reply"), draft["action"])
        elif not self.live:
            status = "dry-run"
        else:
            if platform == "youtube":
                from sources import youtube as api
            else:
                from sources import instagram as api
            if hide:
                api.hide(c["id"])
            else:
                api.reply(c["id"], draft["reply"])
            status = "hidden" if hide else "posted"
        out = {"comment_id": c["id"], "platform": platform,
               "action": draft["action"], "status": status}
        self.send("orchestrator", "published", out)
        return out
