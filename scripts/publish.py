import json
import os

QUEUE_PATH = "episodes_queue.json"
FEED_PATH = "feed.xml"


def load_queue():
    if not os.path.exists(QUEUE_PATH):
        return {"pending": [], "published": []}
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def update_rss_feed(episode):
    if not os.path.exists(FEED_PATH):
        print(f"❌ 找不到 {FEED_PATH}")
        return False

    with open(FEED_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_item = f"""
    <item>
      <title>{episode['title']}</title>
      <description>{episode.get('description', '本集講解：' + episode['title'])}</description>
      <pubDate>{episode['pubDate']}</pubDate>
      <guid>{episode['url']}</guid>
      <enclosure url="{episode['url']}" length="{episode['size']}" type="{episode['content_type']}"/>
      <itunes:explicit>no</itunes:explicit>
    </item>
    """

    idx = content.find("<item>")
    insert_at = idx if idx != -1 else content.find("</channel>")
    if insert_at == -1:
        print("❌ feed.xml 格式異常，缺少 <item> 或 </channel>")
        return False

    new_content = (
        content[:insert_at] + new_item + "\n" + content[insert_at:]
    )
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    queue = load_queue()
    pending = queue.get("pending", [])

    if not pending:
        print("ℹ️  佇列裡沒有待發布的集數，結束")
        return

    print(f"📁 發現 {len(pending)} 集待發布")
    still_pending = []

    for episode in pending:
        print(f"\n🎵 處理: {episode['title']}")
        if update_rss_feed(episode):
            queue.setdefault("published", []).append(episode)
            print(f"✅ {episode['title']} 已寫入 feed.xml")
        else:
            still_pending.append(episode)

    queue["pending"] = still_pending
    save_queue(queue)
    print("\n✅ 全部處理完成")


if __name__ == "__main__":
    main()
