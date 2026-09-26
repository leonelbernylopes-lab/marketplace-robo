import asyncio
import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
RESALE = json.loads((BASE / "resale_prices.json").read_text(encoding="utf-8"))

PROFILE = BASE / "browser_profile"
OUT_CSV = BASE / "opportunities.csv"
OUT_JSON = BASE / "opportunities.json"


def brl_to_float(s):
    if not s:
        return None
    s = s.replace("R$", "").replace("\xa0", " ").strip()
    m = re.search(r"(\d[\d.]*(?:,\d{1,2})?)", s)
    if not m:
        return None
    n = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(n)
    except ValueError:
        return None


def normalize(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def reference_resale(title):
    t = normalize(title)
    candidates = []
    for name, item in RESALE.items():
        if name == "default":
            continue
        keys = item.get("keywords", [])
        hits = sum(1 for k in keys if normalize(k) in t)
        if hits:
            candidates.append((hits, item.get("resale_price", 0), name))
    if not candidates:
        return 0, "sem referência"
    candidates.sort(reverse=True)
    return candidates[0][1], candidates[0][2]


def score(buy, resale, title):
    if not buy or not resale or buy <= 0:
        return 0
    profit = resale - buy
    margin = profit / buy
    s = 0
    s += min(50, max(0, margin * 100))
    s += min(40, max(0, profit / 5))
    if any(x in normalize(title) for x in ["novo", "nov"]):
        s += 5
    if any(x in normalize(title) for x in ["defeito", "quebrado", "peças", "pecas"]):
        s -= 30
    return round(max(0, min(100, s)))


async def extract_cards(page):
    # Marketplace muda seletores com frequência. Começamos por links que apontam
    # para /marketplace/item/ e subimos para o container do card.
    data = await page.evaluate("""
    () => {
      const links = [...document.querySelectorAll('a[href*="/marketplace/item/"]')];
      const seen = new Set();
      const out = [];
      for (const a of links) {
        const href = a.href;
        if (!href || seen.has(href)) continue;
        seen.add(href);
        let el = a;
        for (let i=0; i<5 && el; i++, el=el.parentElement) {
          const txt = (el.innerText || '').trim();
          if (txt.length >= 20 && txt.length < 2000) {
            const money = txt.match(/R\\$\\s?[0-9][0-9.]*([,][0-9]{1,2})?/i);
            if (money) {
              out.push({
                title: txt.split('\\n')[0] || a.innerText || '',
                text: txt,
                priceText: money[0],
                href
              });
              break;
            }
          }
        }
      }
      return out;
    }
    """)
    return data


async def search(page, term):
    url = "https://www.facebook.com/marketplace/search/?query=" + quote(term)
    print(f"\n🔎 Buscando: {term}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(4000)

    for _ in range(CONFIG["scrolls_per_search"]):
        await page.mouse.wheel(0, 2500)
        await page.wait_for_timeout(int(CONFIG["delay_seconds"] * 1000))

    return await extract_cards(page)


async def main():
    all_items = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=CONFIG.get("headless", False),
            viewport={"width": 1400, "height": 900},
            locale="pt-BR"
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        print("Abra o Facebook Marketplace.")
        await page.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded", timeout=60000)
        print("Se precisar, faça login MANUALMENTE na janela aberta.")
        input("Quando o Marketplace estiver acessível, pressione ENTER aqui... ")

        for term in CONFIG["search_terms"]:
            try:
                cards = await search(page, term)
                for c in cards:
                    price = brl_to_float(c.get("priceText"))
                    if price is None or price > CONFIG["max_buy_price"]:
                        continue

                    resale, ref = reference_resale(c.get("title", "") + " " + c.get("text", ""))
                    profit = round(resale - price, 2) if resale else None
                    margin = round(profit / price, 4) if resale and price else None
                    sc = score(price, resale, c.get("title", ""))

                    if resale and profit < CONFIG["min_profit"]:
                        continue
                    if resale and margin < CONFIG["min_margin"]:
                        continue

                    key = c["href"].split("?")[0]
                    all_items[key] = {
                        "title": c.get("title", "").strip(),
                        "price": price,
                        "resale_reference": resale,
                        "profit_estimate": profit,
                        "margin_estimate": margin,
                        "score": sc,
                        "reference": ref,
                        "text": c.get("text", "")[:1000],
                        "url": key,
                        "searched_term": term,
                        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
            except Exception as e:
                print(f"⚠️ Erro na busca '{term}': {e}")

        await browser.close()

    results = sorted(all_items.values(), key=lambda x: x["score"], reverse=True)

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["score", "title", "price", "resale_reference", "profit_estimate",
              "margin_estimate", "reference", "searched_term", "url", "collected_at"]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fields})

    print(f"\n✅ {len(results)} oportunidades encontradas.")
    print(f"📄 {OUT_CSV}")
    print("\nTOP 20:")
    for i, r in enumerate(results[:20], 1):
        margin = f"{r['margin_estimate']*100:.0f}%" if r["margin_estimate"] is not None else "-"
        print(f"{i:02d}. [{r['score']:>3}] R$ {r['price']:.0f} -> R$ {r['resale_reference']:.0f} | lucro R$ {r['profit_estimate'] or 0:.0f} | {margin} | {r['title'][:70]}")
        print(f"    {r['url']}")


if __name__ == "__main__":
    asyncio.run(main())
