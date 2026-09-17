# scripts/main.py （針對你現有 repo 的版本）
import asyncio, json, os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from fetcher  import fetch_all
from analyzer import build_script
from tts      import to_mp3
from r2       import upload_file, upload_text, download_text
# 複用你原有的 publish.py 的 RSS 更新邏輯
from publish  import update_rss_feed, load_queue, save_queue

async def main():
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # ① 抓取
    items = fetch_all()
    
    # ② 生成播報稿
    from analyzer import build_script
    disp = datetime.now().strftime("%Y年%-m月%-d日")
    script = build_script(items, disp)
    
    # ③ TTS
    mp3_path = f"/tmp/ep_{date_str}.mp3"
    duration = await to_mp3(script, mp3_path)
    
    # ④ 上傳 R2
    mp3_key  = f"ep_{date_str}.mp3"
    base_url = os.environ["R2_PUBLIC_URL"].rstrip("/")
    upload_file(mp3_path, mp3_key, "audio/mpeg")
    
    # ⑤ 組成 episode dict（符合你現有 publish.py 的格式）
    episode = {
        "title":        f"{disp} 美股科技晨報",
        "url":          f"{base_url}/{mp3_key}",
        "size":         Path(mp3_path).stat().st_size,
        "content_type": "audio/mpeg",
        "pubDate":      format_datetime(datetime.now(timezone.utc)),
        "description":  script[:300],
        "guid":         f"ep_{date_str}",
    }
    
    # ⑥ 寫入 feed.xml（複用你原有邏輯）
    update_rss_feed(episode)
    
    # ⑦ 上傳更新後的 feed.xml 到 R2
    with open("feed.xml", "r", encoding="utf-8") as f:
        xml = f.read()
    upload_text(xml, "feed.xml", "application/rss+xml; charset=utf-8")
    
    # ⑧ 更新 queue（保留你原有的歷史紀錄）
    queue = load_queue()
    queue.setdefault("published", []).append(episode)
    save_queue(queue)
    
    print(f"✅ 完成！RSS: {base_url}/feed.xml")

if __name__ == "__main__":
    asyncio.run(main())