"""⑤ 정리 에이전트: 승인된 아이디어를 숏츠 기획안(md)으로 저장한다."""
from __future__ import annotations

from datetime import date

from .base import ROOT, Agent
from .classifier import LABELS

PLAT = {"youtube": "유튜브 쇼츠", "instagram": "인스타 릴스", "tiktok": "틱톡"}
TYPE = {"scene": "터진 장면 재구성", "request": "요청 주제(아직 없는 영상)", "game_interest": "입문 가이드"}


class ReporterAgent(Agent):
    name = "reporter"

    def __init__(self, bus, **kw):
        super().__init__(bus, use_llm=False)

    def write(self, videos, comments, signals, ideas, keywords) -> str:
        byid = {c["id"]: c for c in comments}
        vmap = {v["id"]: v for v in videos}
        approved = sorted([i for i in ideas if i["status"] == "approve"],
                          key=lambda i: i["evidence_likes"], reverse=True)
        human = [i for i in ideas if i["status"] == "escalate"]
        counts = {}
        for s in signals:
            counts[s["cls"]["label"]] = counts.get(s["cls"]["label"], 0) + 1
        complaints = [s for s in signals if s["cls"]["label"] == "complaint"]

        L = [f"# 게임 숏츠 기획안 ({date.today():%Y-%m-%d})", ""]
        L += ["## Ⅰ. 수집 요약", ""]
        L += [f"1. 영상 {len(videos)}개, 분석한 댓글 {len(comments)}개",
              f"2. 플랫폼: " + ", ".join(sorted({PLAT.get(v['platform'], v['platform']) for v in videos})),
              "3. 반응 유형: " + ", ".join(f"{LABELS[k]} {n}" for k, n in sorted(counts.items(), key=lambda x: -x[1])), ""]
        L += ["## Ⅱ. 기획 아이디어 (근거 댓글 좋아요 순)", ""]
        for n, i in enumerate(approved, 1):
            L += [f"### {n}. {i['title']}", "",
                  f"- 게임: {i['game']}",
                  f"- 유형: {TYPE.get(i['type'], i['type'])}",
                  f"- 첫 3초 훅: {i['hook']}",
                  f"- 다르게 할 점: {i.get('angle', '')}",
                  f"- 근거 댓글 ({len(i['evidence'])}개, 좋아요 합계 {i['evidence_likes']:,}):"]
            L += [f"  - \"{byid[e]['text']}\" ({byid[e].get('likes', 0):,}♥)" for e in i["evidence"]]
            L += ["- 참고 영상: " + ", ".join(vmap[v]["url"] for v in i["source_videos"]), ""]
        L += ["## Ⅲ. 사람 확인 필요", ""]
        L += [f"{n}. {i['title']}: {i['note']}" for n, i in enumerate(human, 1)] or ["1. 없음"]
        L += ["", "## Ⅳ. 반복 키워드 (제목·자막 후보)", ""]
        L += [f"{n}. {w} ({c}개 댓글)" for n, (w, c) in enumerate(keywords, 1)] or ["1. 없음"]
        L += ["", "## Ⅴ. 피할 점 (불만 댓글)", ""]
        L += [f"{n}. \"{s['c']['text']}\" ({PLAT.get(s['c']['platform'], s['c']['platform'])})"
              for n, s in enumerate(complaints, 1)] or ["1. 없음"]

        md = "\n".join(L) + "\n"
        out = ROOT / "plans" / "shorts_plan.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(md, encoding="utf-8")
        self.send("orchestrator", "saved", {"file": "plans/shorts_plan.md",
                                            "ideas": len(approved), "needs_human": len(human)})
        return md
