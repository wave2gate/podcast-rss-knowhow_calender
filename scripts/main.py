# scripts/main.py
import asyncio, os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from fetcher  import fetch_all
from analyzer import build_script
from tts      import to_mp3
from r2       import upload_file, upload_text

# publish.py 在同一個 scripts/ 目錄，直接 import
from publish  import update_rss_feed, load_queue, save_queue

# ── 路徑：scripts/ 內執行，feed.xml 在上一層根目錄 ──────────────────
ROOT      = Path(__file__).parent.parent   # repo 根目錄
FEED_PATH = ROOT / "feed.xml"
QUEUE_PATH = ROOT / "episodes_queue.json"

# publish.py 裡的 FEED_PATH / QUEUE_PATH 是字串常數，需要覆蓋
import publish as _pub
_pub.FEED_PATH  = str(FEED_PATH)
_pub.QUEUE_PATH = str(QUEUE_PATH)


async def main():
    # 日期
    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    disp     = now.strftime("%Y年%-m月%-d日")

    print(f"=== {disp} 晨報開始 ===")

    # ① 抓取 RSS
    print("① 抓取中...")
    items = fetch_all()
    print(f"   共 {len(items)} 則原始條目")

    # ② AI 生成播報稿
    print("② 生成播報稿...")
    script = build_script(items, disp)
    print(f"   {len(script)} 字")

    # ③ TTS → MP3（存到 /tmp 避免汙染 repo）
    print("③ TTS 生成音頻...")
    mp3_path = f"/tmp/ep_{date_str}.mp3"
    duration = await to_mp3(script, mp3_path)

    # ④ 上傳 MP3 到 R2
    print("④ 上傳 R2...")
    mp3_key  = f"ep_{date_str}.mp3"
    base_url = os.environ["R2_PUBLIC_URL"].rstrip("/")
    upload_file(mp3_path, mp3_key, "audio/mpeg")

    # ⑤ 組成 episode dict（符合 publish.py 的格式）
    episode = {
        "title":        f"{disp} 美股科技晨報",
        "url":          f"{base_url}/{mp3_key}",
        "size":         Path(mp3_path).stat().st_size,
        "content_type": "audio/mpeg",
        "pubDate":      format_datetime(now),
        "description":  script[:300],
        "guid":         f"ep_{date_str}",
    }

    # ⑥ 寫入本地 feed.xml（複用原有 publish.py 邏輯）
    print("⑤ 更新 feed.xml...")
    update_rss_feed(episode)

    # ⑦ 上傳 feed.xml 到 R2（讓播客平台能讀到最新 RSS）
    with open(FEED_PATH, "r", encoding="utf-8") as f:
        xml = f.read()
    upload_text(xml, "feed.xml", "application/rss+xml; charset=utf-8")
    print(f"   RSS 已上傳：{base_url}/feed.xml")

    # ⑧ 更新 episodes_queue.json 歷史紀錄
    queue = load_queue()
    queue.setdefault("published", []).append(episode)
    save_queue(queue)

    print(f"\n✅ 完成！")
    print(f"   MP3 : {base_url}/{mp3_key}")
    print(f"   RSS : {base_url}/feed.xml")


if __name__ == "__main__":
    asyncio.run(main())
