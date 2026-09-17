"""
數據抓取：官方 RSS 優先，nitter 補充 Twitter 帳號
核心10個帳號：科技財經主力 + 能源儲能
"""
import time, logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser, requests

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PodcastBot/1.0)"}
CUTOFF  = datetime.now(timezone.utc) - timedelta(hours=28)
MAX_PER = 8   # 每帳號最多送給 AI 幾則

# ── 帳號清單 ─────────────────────────────────────────────────────────
# (顯示名稱, 官方RSS或None, Twitter handle或None)
SOURCES = [
    ("WSJ Markets",     "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",          None),
    ("CNBC",            "https://www.cnbc.com/id/100003114/device/rss/rss.html",   None),
    ("Bloomberg Mkts",  "https://feeds.bloomberg.com/markets/news.rss",            None),
    ("SeekingAlpha",    "https://seekingalpha.com/feed.xml",                        None),
    ("TechCrunch",      "https://techcrunch.com/feed/",                             None),
    ("MarketWatch",     "https://feeds.content.dowjones.io/public/rss/mw_topstories", None),
    ("Investing.com",   "https://www.investing.com/rss/news.rss",                   None),
    ("BloombergNEF",    "https://about.bnef.com/feed/",                             None),
    ("EnergyStorage",   "https://www.energy-storage.news/feed/",                    None),
    ("Yahoo Finance",   "https://finance.yahoo.com/rss/topstories",                 None),
]

# nitter 公共實例列表（自動選可用的）
NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
    "nitter.foss.wtf",
]

def _probe_nitter() -> Optional[str]:
    """找第一個能用的 nitter 實例"""
    for host in NITTER_INSTANCES:
        try:
            r = requests.get(f"https://{host}/WSJmarkets/rss",
                             headers=HEADERS, timeout=8)
            if r.status_code == 200:
                log.info(f"   nitter 使用: {host}")
                return host
        except Exception:
            pass
    log.warning("   所有 nitter 實例不可用")
    return None

def _parse_feed(url: str, label: str) -> list[dict]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        out  = []
        for e in feed.entries[:MAX_PER]:
            # 解析時間
            for attr in ("published_parsed", "updated_parsed"):
                t = getattr(e, attr, None)
                if t:
                    pub = datetime(*t[:6], tzinfo=timezone.utc)
                    break
            else:
                pub = datetime.now(timezone.utc)

            if pub < CUTOFF:
                continue

            out.append({
                "source":  label,
                "title":   getattr(e, "title",   "").strip(),
                "summary": getattr(e, "summary", "")[:400].strip(),
                "url":     getattr(e, "link",    ""),
            })
        return out
    except Exception as ex:
        log.warning(f"   {label} 失敗: {ex}")
        return []

def fetch_all() -> list[dict]:
    nitter = _probe_nitter()
    results = []

    for label, rss_url, handle in SOURCES:
        items = []

        # 1. 官方 RSS
        if rss_url:
            items = _parse_feed(rss_url, label)

        # 2. nitter 補充（若官方 RSS 條目不足）
        if len(items) < 3 and handle and nitter:
            nit_url = f"https://{nitter}/{handle}/rss"
            items   = _parse_feed(nit_url, f"{label}(tw)")

        results.extend(items)
        log.info(f"   {label}: {len(items)} 則")
        time.sleep(1.2)   # 避免過快

    return results
