"""③ 기획 에이전트: 같은 종류의 반응을 묶어 숏츠 기획 아이디어로 만든다."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from .base import Agent

MIN_EVIDENCE = 2  # 근거 댓글이 이만큼 모여야 아이디어로 만든다
STOP = {"진짜", "너무", "해주세요", "알려주세요", "이거", "영상", "마지막", "다음엔", "어떻게",
        "있나요", "있어요", "무슨", "게임", "하는", "거예요", "같은", "버전도"}
# 제목이 길 때 쓸 한국어 줄임말 (.env 로 바꾸지 않고 여기서 추가)
NICK = {"Grow a Garden": "그로우 어 가든", "99 Nights in the Forest": "99일 밤 숲", "Minecraft": "마크"}


class PlannerAgent(Agent):
    name = "planner"

    def plan(self, signals: list[dict], videos: dict) -> list[dict]:
        groups = defaultdict(list)
        for s in signals:
            if s["cls"]["label"] in ("scene", "request", "game_interest"):
                groups[(s["c"]["game"], s["cls"]["label"])].append(s)

        ideas = []
        for (game, label), items in groups.items():
            if len(items) < MIN_EVIDENCE:
                continue
            items.sort(key=lambda s: s["c"].get("likes") or 0, reverse=True)
            idea = self._llm_idea(game, label, items) if self.use_llm else self._rule_idea(game, label, items)
            idea.update({
                "id": f"idea{len(ideas)+1}", "game": game, "type": label,
                "evidence": [s["c"]["id"] for s in items],
                "evidence_likes": sum(s["c"].get("likes") or 0 for s in items),
                "source_videos": sorted({s["c"]["video_id"] for s in items}),
                "revision": 1,
            })
            ideas.append(idea)
            self.send("reviewer", "idea", {k: idea[k] for k in ("id", "game", "type", "title", "hook")})
        return ideas

    def revise(self, idea: dict, note: str) -> dict:
        if self.use_llm:
            out = self.ask_llm(f"아이디어: {json.dumps(idea, ensure_ascii=False)}\n검수 피드백: {note}\n"
                               "고친 title, hook 을 JSON 으로")
            idea.update({k: out[k] for k in ("title", "hook") if k in out})
        elif "길" in note:
            game, nick = idea["game"], NICK.get(idea["game"], "")
            if game in idea["title"] and nick:          # 1차: 한국어 줄임말로
                idea["title"] = idea["title"].replace(game, nick)
            else:                                       # 2차: 게임 이름 빼기
                idea["title"] = idea["title"].replace(game, "").replace(nick, "").strip()
        elif "비슷" in note:
            idea["title"] = idea["title"] + " (내 방식 버전)"
        idea["revision"] += 1
        self.send("reviewer", "idea", {k: idea[k] for k in ("id", "title", "revision")})
        return idea

    def _llm_idea(self, game, label, items):
        lines = "\n".join(f"- ({s['c'].get('likes')}♥) {s['c']['text']}" for s in items)
        return self.ask_llm(f"게임: {game}\n반응 유형: {label}\n근거 댓글:\n{lines}\n"
                            "키: title(숏츠 제목), hook(첫 3초), angle(무엇을 다르게 할지)")

    @staticmethod
    def _rule_idea(game, label, items):
        top = items[0]["c"]["text"]
        cut = lambda t, n=20: t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
        kw = [k for k in items[0]["cls"].get("keywords", []) if not re.match(r"\d+:\d+", k)]
        key = kw[0] if kw else "그 장면"
        if label == "scene":
            return {"title": f"{game} {key} 나오는 순간만 모아봄",
                    "hook": f"댓글 반응 1위 장면부터 바로 보여주기 (\"{cut(top)}\")",
                    "angle": "타임스탬프로 언급된 장면을 첫 3초에 배치"}
        if label == "request":
            want = re.sub(r"\s*(다음엔|해주세요|해줘요|도|2편|!+|ㅋ+)\s*", " ", top).strip()
            return {"title": f"{want} 해봤습니다",
                    "hook": "\"댓글에서 해달라고 해서 진짜 해봄\" 자막으로 시작",
                    "angle": "아직 올라오지 않은 요청 주제", "is_new": True}
        return {"title": f"{game} 30초 입문 가이드",
                "hook": f"\"{cut(top)}\" 질문 화면에 띄우고 답하기",
                "angle": "질문이 반복된 방법·조작법을 짧게 설명"}

    @staticmethod
    def keywords(signals: list[dict]) -> list[tuple[str, int]]:
        """여러 댓글에 반복해서 나온 단어 (제목·자막 후보)."""
        cnt = Counter()
        for s in signals:
            words = {w for w in re.findall(r"[가-힣]{2,}", s["c"]["text"]) if w not in STOP}
            cnt.update(words)
        return [(w, n) for w, n in cnt.most_common(8) if n >= 2]
