import os; os.makedirs("video/build", exist_ok=True)
import json, html, asyncio
from playwright.async_api import async_playwright
CSS = """body{margin:0;width:1920px;height:1080px;background:#0f1115;color:#e8eaf0;font-family:'Noto Sans CJK KR',sans-serif;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden}
.g{background:linear-gradient(90deg,#ffb020,#ff4f8b,#8b5cf6);-webkit-background-clip:text;color:transparent}"""
thumb = f"""<style>{CSS}
.blob{{position:absolute;border-radius:50%;filter:blur(80px);opacity:.55}}
.tag{{font-size:34px;padding:10px 26px;border:2px solid #ff4f8b;border-radius:999px;color:#ff4f8b;margin-bottom:34px;font-weight:700}}
h1{{font-size:118px;margin:0;font-weight:900;letter-spacing:-3px;text-align:center;line-height:1.1}}
p{{font-size:44px;color:#c9cede;margin-top:34px}}
.row{{display:flex;gap:18px;margin-top:50px}}.chip{{font-size:30px;background:#1d212b;border:1px solid #333a48;border-radius:14px;padding:14px 24px}}
</style>
<div class=blob style="width:700px;height:700px;background:#ff4f8b;left:-200px;top:-250px"></div>
<div class=blob style="width:700px;height:700px;background:#8b5cf6;right:-200px;bottom:-300px"></div>
<div class=tag>SNS 자동화 · 멀티에이전트</div>
<h1>터진 숏츠 댓글로<br><span class=g>다음 숏츠</span>를 기획한다</h1>
<p>유튜브 · 인스타 · 틱톡 반응으로 기획안 + 내 댓글엔 자동 답글</p>
<div class=row><span class=chip>① Collector</span><span class=chip>② Classifier</span><span class=chip>③ Planner</span><span class=chip>④ Reviewer</span><span class=chip>⑤ Reporter</span></div>"""
arch = f"""<style>{CSS}
h2{{font-size:64px;margin:0 0 60px}}
.flow{{display:flex;align-items:center;gap:22px}}
.n{{width:250px;padding:28px 10px;border-radius:20px;background:#1d212b;border:2px solid #333a48;text-align:center}}
.n b{{font-size:36px;display:block}}.n s{{text-decoration:none;font-size:24px;color:#8b93a7}}
.ar{{font-size:48px;color:#ff4f8b}}
.note{{margin-top:60px;font-size:34px;color:#c9cede;text-align:center;line-height:1.6}}
</style>
<h2>모드 1 · 기획: 인기 숏츠 반응 → 기획안</h2>
<div class=flow>
<div class=n><b>① 수집</b><s>인기 숏츠 댓글</s></div><span class=ar>→</span>
<div class=n><b>② 분류</b><s>장면·요청·질문·불만</s></div><span class=ar>→</span>
<div class=n><b>③ 기획</b><s>제목·첫 3초 훅</s></div><span class=ar>⇄</span>
<div class=n style="border-color:#ff4f8b"><b>④ 검수</b><s>승인·수정·사람</s></div><span class=ar>→</span>
<div class=n><b>⑤ 정리</b><s>기획안 md</s></div></div>
<div class=note>각 에이전트의 지시사항은 <span class=g style="font-weight:800">skills/*/SKILL.md</span><br>내가 못 찍는 게임이나 근거가 약한 아이디어는 <b>사람 확인</b>으로 넘김</div>"""
arch2 = f"""<style>{CSS}
h2{{font-size:60px;margin:0 0 60px}}
.flow{{display:flex;align-items:center;gap:22px}}
.n{{width:250px;padding:28px 10px;border-radius:20px;background:#1d212b;border:2px solid #333a48;text-align:center}}
.n b{{font-size:36px;display:block}}.n s{{text-decoration:none;font-size:24px;color:#8b93a7}}
.ar{{font-size:48px;color:#ff4f8b}}
.pl{{display:flex;gap:30px;margin-top:60px}} .p{{font-size:28px;background:#1d212b;border-radius:14px;padding:18px 26px;line-height:1.5;text-align:center}}
.p b{{display:block;font-size:30px}}
</style>
<h2>모드 2 · 답글: 내 계정 댓글 → 자동 답글</h2>
<div class=flow>
<div class=n><b>① 수집</b><s>내 숏츠 새 댓글</s></div><span class=ar>→</span>
<div class=n><b>② 분류</b><s>질문·칭찬·불만·스팸</s></div><span class=ar>→</span>
<div class=n><b>③ 답글</b><s>플랫폼 말투</s></div><span class=ar>⇄</span>
<div class=n style="border-color:#ff4f8b"><b>④ 검수</b><s>승인·수정·사람</s></div><span class=ar>→</span>
<div class=n><b>⑤ 게시</b><s>플랫폼별</s></div></div>
<div class=pl><div class=p><b style="color:#ff5470">YouTube</b>답글 게시 · 스팸 검토 대기</div><div class=p><b style="color:#ec4899">Instagram</b>답글 게시 · 스팸 숨김</div><div class=p><b>TikTok</b>API 없음 → 답글 CSV 저장</div></div>"""
lines = open("video/build/cli.txt",encoding="utf-8").read().splitlines()
term_lines = json.dumps(lines, ensure_ascii=False)
term = f"""<meta charset="utf-8"><style>{CSS}
body{{justify-content:flex-start;align-items:stretch;padding:60px 80px;box-sizing:border-box}}
.win{{background:#0b0d10;border:1px solid #2a2f3a;border-radius:16px;flex:1;display:flex;flex-direction:column;overflow:hidden}}
.bar{{height:46px;background:#1b1f27;display:flex;align-items:center;gap:10px;padding:0 18px}}.d{{width:14px;height:14px;border-radius:50%}}
pre{{margin:0;padding:24px 30px;font:22px/1.55 'DejaVu Sans Mono','Noto Sans Mono CJK KR',monospace;color:#cfd5e2;white-space:pre-wrap;overflow:hidden;flex:1;display:flex;flex-direction:column;justify-content:flex-end}} #o{{white-space:pre-wrap}}
.p{{color:#22c55e}}.k{{color:#ffb020}}
</style>
<div class=win><div class=bar><span class=d style=background:#ff5f57></span><span class=d style=background:#febc2e></span><span class=d style=background:#28c840></span><span style="margin-left:14px;color:#8b93a7;font-size:20px">sns-shorts-agents — zsh</span></div>
<pre><div id=o></div></pre></div>
<script>
const L={term_lines};const o=document.getElementById('o');
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
o.innerHTML='<span class=p>$</span> python main.py\\n';let i=0;
setTimeout(function t(){{if(i<L.length){{let s=esc(L[i++]).replace(/(\\w+ +→ +\\w+)/,'<span class=k>$1</span>');o.innerHTML+=s+'\\n';setTimeout(t,i<L.length-4?105:450);}}}},900);
</script>"""
outro = f"""<style>{CSS}
h2{{font-size:76px;margin:0}} ul{{font-size:38px;line-height:1.9;color:#c9cede;margin-top:40px}}
code{{background:#1d212b;padding:4px 14px;border-radius:8px;color:#ffb020}}
</style>
<h2 class=g>GitHub · sns-shorts-agents</h2>
<ul><li><code>python main.py plan</code> 인기 숏츠 반응 → 기획안</li>
<li><code>--source youtube</code> 인기 쇼츠 댓글 자동 수집</li>
<li><code>--source csv</code> 인스타 릴스 · 틱톡 댓글 넣기</li>
<li><code>python main.py reply</code> 내 계정 댓글 자동 답글</li>
<li><code>skills/*/SKILL.md</code> 에이전트별 지시사항</li></ul>"""
open("video/build/term.html","w",encoding="utf-8").write(term)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1920,"height":1080})
        for name,h in [("thumbnail",thumb),("arch",arch),("arch2",arch2),("outro",outro)]:
            await pg.set_content(h); await pg.wait_for_timeout(300)
            await pg.screenshot(path=f"video/build/{name}.png")
        await b.close()
asyncio.run(main())

# 기획안(md) 화면
import markdown as _md
_plan = _md.markdown(open("plans/shorts_plan.md", encoding="utf-8").read())
plan = f"""<meta charset="utf-8"><style>{CSS}
body{{justify-content:flex-start;align-items:stretch;padding:50px 120px;box-sizing:border-box;display:block}}
.doc{{background:#f7f7f5;color:#1f2328;border-radius:16px;padding:40px 60px;height:980px;overflow:hidden;columns:2;column-gap:60px;font-size:19px;line-height:1.5}}
h1{{font-size:34px;column-span:all;margin:0 0 10px}} h2{{font-size:24px;margin:18px 0 8px;color:#b4235a}} h3{{font-size:20px;margin:14px 0 4px}}
ul,ol{{margin:4px 0;padding-left:22px}} li{{margin:2px 0}} p{{margin:4px 0}}
</style><div class=doc>{_plan}</div>"""
async def _plan_shot():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1920,"height":1080})
        await pg.set_content(plan); await pg.wait_for_timeout(300)
        await pg.screenshot(path="video/build/plan.png"); await b.close()
asyncio.run(_plan_shot())
