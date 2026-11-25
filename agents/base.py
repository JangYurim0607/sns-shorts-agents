"""모든 에이전트의 공통 부모 클래스.

각 에이전트는
  1) skills/<name>/SKILL.md 를 읽어서 '지시사항(system prompt)'으로 사용하고
  2) ANTHROPIC_API_KEY 가 있으면 Claude 에게 판단을 맡기고,
  3) 키가 없거나 SKILL.md 가 아직 비어 있으면 rule-based 데모 로직(fallback)으로 동작한다.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")


def load_skill(name: str) -> str:
    """skills/<name>/SKILL.md 본문(frontmatter 제외)을 읽는다."""
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    return body.strip()


def skill_is_filled(body: str) -> bool:
    """TODO 만 있는 빈 틀이면 False."""
    lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
    real = [l for l in lines if "TODO" not in l and "<!--" not in l]
    return len(real) >= 3


class Bus:
    """에이전트끼리 주고받는 메시지를 기록하는 공용 게시판(blackboard).
    실행 로그는 runs/latest.json 으로 저장되고, web/index.html 뷰어가 이를 재생한다."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.t0 = time.time()
        self.lock = threading.Lock()

    def post(self, sender: str, receiver: str, kind: str, payload: dict) -> None:
        with self.lock:
            self._post(sender, receiver, kind, payload)

    def _post(self, sender, receiver, kind, payload) -> None:
        evt = {
            "t": round(time.time() - self.t0, 3),
            "from": sender,
            "to": receiver,
            "kind": kind,
            "payload": payload,
        }
        self.events.append(evt)
        print(f"[{evt['t']:6.2f}s] {sender:>10} → {receiver:<10} {kind}: "
              f"{json.dumps(payload, ensure_ascii=False)[:90]}")


class Agent:
    name = "agent"

    def __init__(self, bus: Bus, use_llm: bool | None = None) -> None:
        self.bus = bus
        self.skill = load_skill(self.name)
        has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        if use_llm is None:
            use_llm = has_key and skill_is_filled(self.skill)
        self.use_llm = use_llm
        self._client = None

    # ---- LLM 호출 (SKILL.md = system prompt) ----
    def ask_llm(self, user_content: str) -> dict:
        if self._client is None:
            import anthropic  # 선택 의존성

            self._client = anthropic.Anthropic()
        msg = self._client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=self.skill + "\n\n반드시 JSON 한 개만 출력하세요.",
            messages=[{"role": "user", "content": user_content}],
        )
        text = msg.content[0].text
        match = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(match.group(0)) if match else {}

    def send(self, to: str, kind: str, payload: dict) -> None:
        self.bus.post(self.name, to, kind, payload)
