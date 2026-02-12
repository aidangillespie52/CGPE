# cgpe/scrape/detail/parse_detail.py

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Any
import json
import re
from pprint import pformat

from bs4 import BeautifulSoup, SoupStrainer  # <-- SoupStrainer added

from cgpe.scrape.sources.base import SourceConfig
from cgpe.utils.time import utc_now_iso
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

VGPC_POP_RE = re.compile(r"VGPC\.pop_data\s*=\s*(\{.*?\})\s*;", re.DOTALL)

# Only parse the parts of the DOM we actually use:
# - div#full-prices (graded/ungraded prices table)
# - div#price_comparison (ebay completed auctions tables)
# - div#full_details (card name)
# - td[itemprop=model-number] (card number)

_PARSE_ONLY = SoupStrainer(
    name="div",
    id=["full-prices", "price_comparison", "full_details"]
)



@dataclass
class Detail:
    card_link: str
    card_name: str
    card_num: str
    source_config: SourceConfig
    pop: Optional[dict]
    graded_prices_by_grade: Dict[str, Optional[float]]
    grades_1_to_10: List[Optional[float]]
    grade7_dist: Tuple[float, float]
    grade8_dist: Tuple[float, float]
    grade9_dist: Tuple[float, float]
    grade10_dist: Tuple[float, float]
    ungraded_price: Optional[float] = None

    def __repr__(self) -> str:
        src = getattr(self.source_config, "source", None)

        pop_s = pformat(self.pop, width=88, compact=False)
        prices_s = pformat(self.graded_prices_by_grade, width=88, compact=False)
        g10_s = pformat(self.grades_1_to_10, width=88, compact=False)

        return (
            "Detail(\n"
            f"  card_link={self.card_link!r},\n"
            f"  card_name={self.card_name!r},\n"
            f"  card_num={self.card_num!r},\n"
            f"  source={src!r},\n"
            f"  ungraded_price={self.ungraded_price!r},\n"
            f"  pop={pop_s},\n"
            f"  graded_prices_by_grade={prices_s},\n"
            f"  grades_1_to_10={g10_s},\n"
            f"  grade7_dist=(mean={self.grade7_dist[0]},stddev={self.grade7_dist[1]})\n"
            f"  grade8_dist=(mean={self.grade8_dist[0]},stddev={self.grade8_dist[1]})\n"
            f"  grade9_dist=(mean={self.grade9_dist[0]},stddev={self.grade9_dist[1]})\n"
            f"  grade10_dist=(mean={self.grade10_dist[0]},stddev={self.grade10_dist[1]}\n)"
            ")"
        )

    def to_db_row(self) -> Dict[str, Any]:
        source = getattr(self.source_config, "source", None)

        return {
            "card_link": self.card_link,
            "card_name": self.card_name,
            "card_num": self.card_num,
            "source": source,
            "ungraded_price": self.ungraded_price,
            "grade7_mean": self.grade7_dist[0],
            "grade7_std": self.grade7_dist[1],
            "grade8_mean": self.grade8_dist[0],
            "grade8_std": self.grade8_dist[1],
            "grade9_mean": self.grade9_dist[0],
            "grade9_std": self.grade9_dist[1],
            "grade10_mean": self.grade10_dist[0],
            "grade10_std": self.grade10_dist[1],
            "pop_json": json.dumps(self.pop) if self.pop is not None else None,
            "graded_prices_json": json.dumps(self.graded_prices_by_grade),
            "grades_1_to_10_json": json.dumps(self.grades_1_to_10),
            "scraped_at": utc_now_iso(),
        }


# -----------------------------
# Normalization helpers
# -----------------------------

def clean_price_text(text: str) -> str:
    return text.lower().strip().replace("$", "").replace(",", "")

def clean_grade_text(text: str) -> str:
    return text.lower().strip()

def clean_name(name: str) -> str:
    return name.lower().strip().replace(" details", "")

def clean_card_num(text: str) -> str:
    return text.strip()

def parse_price(text: str) -> Optional[float]:
    t = clean_price_text(text)
    if not t or "-" in t:
        return None
    try:
        return float(t)
    except ValueError:
        log.debug("Failed to parse price text: %r", text)
        return None


# -----------------------------
# Extractors
# -----------------------------

def extract_prices_table(soup: BeautifulSoup) -> Dict[str, Optional[float]]:
    container = soup.find("div", id="full-prices")
    if not container:
        raise ValueError("Could not find prices container: div#full-prices")

    table = container.find("table")
    if not table:
        raise ValueError("Could not find prices table inside div#full-prices")

    out: Dict[str, Optional[float]] = {}

    # minor speed: avoid deep recursion when possible
    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False) or tr.find_all("td")
        if len(tds) < 2:
            continue

        grade = clean_grade_text(tds[0].get_text(" ", strip=True))
        price = parse_price(tds[-1].get_text(" ", strip=True))
        out[grade] = price

    return out

def extract_ebay_tables(soup: BeautifulSoup):
    def extract(div):
        if not div:
            return (None, None)

        table = div.find("table")
        if not table:
            return (None, None)

        trs = table.find_all("tr")
        prices = []

        for tr in trs[1:]:  # skip headers
            tds = tr.find_all("td", recursive=False)
            if len(tds) <= 3:
                continue

            price_span = tds[3].find("span")
            if not price_span:
                continue

            price = clean_price_text(price_span.get_text(strip=True))
            try:
                prices.append(float(price))
            except ValueError:
                continue

        if len(prices) < 2:
            return (None, None)

        mean = sum(prices) / len(prices)
        stddev = (sum((x - mean) ** 2 for x in prices) / (len(prices) - 1)) ** 0.5
        return (mean, stddev)

    res_dict = {}

    pc = soup.find("div", id="price_comparison")
    if not pc:
        # if the ebay section is missing, return Nones rather than crash
        return {"7": (None, None), "8": (None, None), "9": (None, None), "10": (None, None)}

    frame = pc.find("div", class_="tab-frame")
    if not frame:
        return {"7": (None, None), "8": (None, None), "9": (None, None), "10": (None, None)}

    grade7_div = frame.find("div", class_="completed-auctions-cib")
    grade8_div = frame.find("div", class_="completed-auctions-new")
    grade9_div = frame.find("div", class_="completed-auctions-graded")
    grade10_div = frame.find("div", class_="completed-auctions-manual-only")

    res_dict["7"] = extract(grade7_div)
    res_dict["8"] = extract(grade8_div)
    res_dict["9"] = extract(grade9_div)
    res_dict["10"] = extract(grade10_div)

    return res_dict

def extract_pop_data(html: str) -> Optional[dict]:
    m = VGPC_POP_RE.search(html)
    if not m:
        return None

    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        log.warning("Failed to decode population JSON")
        return None

def extract_card_name(soup: BeautifulSoup) -> str:
    div = soup.find("div", id="full_details")
    if not div:
        raise ValueError("Could not find card name: div#full_details")

    h2 = div.find("h2")
    if not h2:
        raise ValueError("Could not find card name inside div#full_details h2")

    return clean_name(h2.get_text(strip=True))

def extract_card_num(soup: BeautifulSoup) -> str:
    td = soup.find("td", attrs={"itemprop": "model-number"})
    if not td:
        return ""
    return clean_card_num(td.get_text(strip=True))


# -----------------------------
# Composition
# -----------------------------

def map_prices_to_1_to_10(prices: Dict[str, Optional[float]]) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(1, 10):
        out.append(prices.get(f"grade {i}"))
    out.append(prices.get("psa 10") or prices.get("grade 10"))
    return out


def parse_detail_page(
    html: str,
    card_link: str,
    source_config: SourceConfig,
) -> Detail:
    
    log.info("Starting parsing detail for link: %s", card_link)

    # Pop is regex-based and doesn't need DOM
    pop = extract_pop_data(html)

    # SoupStrainer: parse only needed nodes; use lxml for speed
    soup = BeautifulSoup(html, "lxml", parse_only=_PARSE_ONLY)

    graded_prices_by_grade = extract_prices_table(soup)
    grades_1_to_10 = map_prices_to_1_to_10(graded_prices_by_grade)
    grade_ebay_tables = extract_ebay_tables(soup)

    detail = Detail(
        ungraded_price=graded_prices_by_grade.get("ungraded"),
        card_link=card_link,
        card_name=extract_card_name(soup),
        card_num=extract_card_num(soup),
        source_config=source_config,
        pop=pop,
        graded_prices_by_grade=graded_prices_by_grade,
        grades_1_to_10=grades_1_to_10,
        grade7_dist=grade_ebay_tables["7"],
        grade8_dist=grade_ebay_tables["8"],
        grade9_dist=grade_ebay_tables["9"],
        grade10_dist=grade_ebay_tables["10"],
    )

    log.info("Parsed detail for card %r (link: %s)", detail.card_name, detail.card_link)

    return detail

async def example():
    import aiohttp

    link = "https://www.pricecharting.com/game/pokemon-evolving-skies/rayquaza-vmax-218                                                                                                     "
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as resp:
            html = await resp.text()
    
    from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING

    d = parse_detail_page(html, link, POKEMON_PRICECHARTING)
    print(repr(d))

if __name__ == '__main__':
    import asyncio
    asyncio.run(example())