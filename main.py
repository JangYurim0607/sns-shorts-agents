"""SNS 게임 숏츠 멀티에이전트. 모드 두 개.

[기획 모드] 인기 게임 숏츠 반응 → 숏츠 기획안
  python main.py plan                                   # 샘플 데이터
  python main.py plan --source youtube --games "Grow a Garden" "99 Nights in the Forest"
  python main.py plan --source csv --csv data/my_comments.csv

[답글 모드] 내 계정 댓글 → 분류 → 답글 → 검수 → 게시
  python main.py reply                                  # 샘플 데이터, dry-run
  python main.py reply --source youtube                 # 내 유튜브 채널 댓글
  python main.py reply --source instagram --post        # 승인된 답글을 실제로 게시
  python main.py reply --source csv --csv tiktok.csv    # 틱톡 (답글은 CSV 로 저장)
"""
import argparse

from dotenv import load_dotenv


def main():
    load_dotenv()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode")

    pl = sub.add_parser("plan", help="인기 숏츠 반응 → 기획안")
    pl.add_argument("--source", choices=["sample", "youtube", "instagram", "csv"], default="sample")
    pl.add_argument("--games", nargs="*", default=["Grow a Garden", "99 Nights in the Forest"])
    pl.add_argument("--days", type=int, default=7)
    pl.add_argument("--csv")

    rp = sub.add_parser("reply", help="내 계정 댓글 자동 답글")
    rp.add_argument("--source", choices=["sample", "youtube", "instagram", "csv"], default="sample")
    rp.add_argument("--csv")
    rp.add_argument("--post", action="store_true", help="승인된 답글을 실제로 게시 (유튜브·인스타)")
    rp.add_argument("--keep", action="store_true", help="이미 처리한 댓글은 건너뛰기")

    a = p.parse_args()
    if a.mode == "reply":
        from agents.reply import ReplyOrchestrator
        r = ReplyOrchestrator(source=a.source, csv_path=a.csv,
                              live_post=a.post and a.source != "sample").run(reset=not a.keep)
        print("\n== 답글 결과 ==", r["summary"])
        print("== 에이전트 모드 ==", r["agent_modes"])
        print("뷰어: web/reply.html / 틱톡 답글: plans/tiktok_replies.csv")
        return

    from agents import Orchestrator
    a.source = getattr(a, "source", "sample")
    r = Orchestrator(source=a.source, games=getattr(a, "games", None) or ["Grow a Garden", "99 Nights in the Forest"],
                     csv_path=getattr(a, "csv", None), days=getattr(a, "days", 7)).run()
    ok = [i for i in r["ideas"] if i["status"] == "approve"]
    print(f"\n== 기획 아이디어 {len(ok)}개 승인, 사람 확인 {len(r['ideas']) - len(ok)}개 ==")
    for i in ok:
        print(f" - {i['title']}  [{i['game']}]")
    print("== 에이전트 모드 ==", r["agent_modes"])
    print("기획안: plans/shorts_plan.md / 뷰어: web/index.html")


if __name__ == "__main__":
    main()
