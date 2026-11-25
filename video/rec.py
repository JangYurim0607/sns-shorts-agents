import asyncio, shutil
from playwright.async_api import async_playwright
async def rec(p, url, secs, out):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={"width":1920,"height":1080}, record_video_dir="video/build/raw", record_video_size={"width":1920,"height":1080})
    pg = await ctx.new_page(); await pg.goto(url); await pg.wait_for_timeout(secs*1000)
    path = await pg.video.path(); await ctx.close(); await b.close()
    shutil.move(path, out)
async def main():
    async with async_playwright() as p:
        await rec(p, "file:///home/claude/sns-shorts-agents/video/build/term.html", 13, "video/build/term.webm")
        await rec(p, "file:///home/claude/sns-shorts-agents/web/index.html?autoplay=1", 32, "video/build/viewer.webm")
        await rec(p, "file:///home/claude/sns-shorts-agents/web/reply.html?autoplay=2", 25, "video/build/reply.webm")
asyncio.run(main())
