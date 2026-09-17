"""
AI 播報稿生成
鏈：Gemini Flash（免費）→ Groq Llama3（免費）→ DeepSeek V3（極低價）
"""
import json, logging, os, re, time
import requests

log = logging.getLogger(__name__)

# ── Prompt ───────────────────────────────────────────────────────────
SYSTEM = """你是一位專業的台灣財經播客主持人，聲音沉穩、邏輯清晰。
請把提供的新聞素材整理成一段完整的廣播播報稿。

格式規定：
1. 開場白：「各位聽眾朋友好，歡迎收聽美股科技晨報，今天是 {date}，我是您的主持人。」
2. 用自然口語過渡每則新聞，禁止使用「第一則」「第二則」等數字列表
   常用過渡語：「首先來看」「接下來」「另一個值得關注的消息是」「在科技板塊方面」
   「我們再來看宏觀面」「說到能源與儲能」「值得投資人注意的是」
3. 每則新聞簡述事實 + 一句對投資者的影響分析
4. 結尾：風險提醒（市場波動來自技術面、消息面、機構資金等多重因素，
   請勿單憑新聞買賣股票，投資需謹慎）
5. 最後祝福：「祝各位身體健康、投資順利，闔家平安，神愛世人，耶穌愛您，我們明天見！」
6. 全程繁體中文口語，不用 Markdown 符號，不用括號，字數 1500–2000 字"""

def _build_prompt(items: list[dict], date: str) -> str:
    system = SYSTEM.replace("{date}", date)
    # 按 source 分組
    groups: dict[str, list] = {}
    for it in items:
        groups.setdefault(it["source"], []).append(it)

    lines = [f"以下是今天（{date}）的新聞素材，請整理成播報稿：\n"]
    for src, its in groups.items():
        lines.append(f"\n【{src}】")
        for it in its[:5]:
            lines.append(f"- {it['title']}")
            if it.get("summary"):
                lines.append(f"  {it['summary'][:200]}")
    return system + "\n\n" + "\n".join(lines)

# ── 各 AI 呼叫 ───────────────────────────────────────────────────────
def _gemini(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    url = (f"https://generativelanguage.googleapis.com/v1beta/"
           f"models/gemini-2.0-flash:generateContent?key={key}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 3000},
    }
    r = requests.post(url, json=body, timeout=90)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def _groq(prompt: str) -> str:
    key = os.environ["GROQ_API_KEY"]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "llama3-70b-8192",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.4, "max_tokens": 3000},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _deepseek(prompt: str) -> str:
    key = os.environ["DEEPSEEK_API_KEY"]
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "deepseek-chat",
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.4, "max_tokens": 3000},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

PROVIDERS = [
    ("Gemini Flash", _gemini,   "GEMINI_API_KEY"),
    ("Groq Llama3",  _groq,     "GROQ_API_KEY"),
    ("DeepSeek V3",  _deepseek, "DEEPSEEK_API_KEY"),
]

def build_script(items: list[dict], date: str) -> str:
    prompt = _build_prompt(items, date)
    for name, fn, env_key in PROVIDERS:
        if not os.environ.get(env_key):
            continue
        try:
            log.info(f"   嘗試 {name}...")
            text = fn(prompt)
            # 清理可能殘留的 Markdown
            text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
            text = re.sub(r"#{1,4}\s*", "", text)
            log.info(f"   ✓ {name} 完成，{len(text)} 字")
            return text
        except Exception as ex:
            log.warning(f"   {name} 失敗: {ex}")
            time.sleep(2)

    raise RuntimeError("所有 AI 提供商均失敗")
