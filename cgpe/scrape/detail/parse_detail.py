# cgpe/scrape/detail/parse_detail.py

from typing import Optional, Dict, List, Tuple
import json
import re
from bs4 import BeautifulSoup, SoupStrainer

from cgpe.scrape.sources.base import SourceConfig
from cgpe.models.detail import Detail

from cgpe.analysis.expected_value import expected_value_from_population_and_prices
from cgpe.analysis.profit_analysis import calculate_profit

from cgpe.logging.logger import setup_logger
log = setup_logger(__name__)

VGPC_POP_RE = re.compile(r"VGPC\.pop_data\s*=\s*(\{.*?\})\s*;", re.DOTALL)

_PARSE_ONLY = SoupStrainer(
    name="div",
    id=["full-prices", "price_comparison", "full_details", "product_details"]
)

# -----------------------------
# Enrichment (EV + Profit)
# -----------------------------

def enrich_detail(
    pop: Optional[dict],
    graded_prices_by_grade: Dict[str, Optional[float]],
    ungraded_price: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:

    log.debug(f"pop data: {pop}")
    
    if not pop or not isinstance(pop, dict):
        log.debug("No population data or invalid type: %r", type(pop))
        return (None, None)

    psa_pop = pop.get("psa")

    if not psa_pop:
        log.debug("Population missing 'psa' key: %s", pop.keys())
        return (None, None)

    prices = graded_prices_by_grade or {}
    prices_list = [prices.get(f"grade {i}") for i in range(1, 10)] + [
        prices.get("psa 10") or prices.get("grade 10")
    ]

    log.debug("PSA population: %s", psa_pop)
    log.debug("Prices list: %s", prices_list)
    log.debug("Ungraded price: %s", ungraded_price)

    try:
        ev = expected_value_from_population_and_prices(psa_pop, prices_list, require_price_if_population=False)
        profit = calculate_profit(
            ungraded_price=ungraded_price or 0,
            expected_value=ev,
        )
        log.debug("Computed EV=%.4f profit=%.4f", ev, profit)
        return (ev, profit)

    except Exception as e:
        log.exception("Failed to compute EV/profit: %s", e)
        return (None, None)


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
        for tr in trs[1:]:
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

    pc = soup.find("div", id="price_comparison")
    if not pc:
        return {"7": (None, None), "8": (None, None), "9": (None, None), "10": (None, None)}

    frame = pc.find("div", class_="tab-frame")
    if not frame:
        return {"7": (None, None), "8": (None, None), "9": (None, None), "10": (None, None)}

    return {
        "7": extract(frame.find("div", class_="completed-auctions-cib")),
        "8": extract(frame.find("div", class_="completed-auctions-new")),
        "9": extract(frame.find("div", class_="completed-auctions-graded")),
        "10": extract(frame.find("div", class_="completed-auctions-manual-only")),
    }

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
    return clean_card_num(td.get_text(strip=True)) if td else ""

def extract_img_link(soup: BeautifulSoup) -> str:
    div = soup.find("div", id="product_details")
    img = div.find("div", recursive=False).find("img") if div else None
    if not img:
        raise ValueError("Could not find image inside div#product_details")
    return img["src"]

# -----------------------------
# Composition
# -----------------------------

def map_prices_to_1_to_10(prices: Dict[str, Optional[float]]) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(1, 10):
        out.append(prices.get(f"grade {i}"))
    out.append(prices.get("psa 10") or prices.get("grade 10"))
    return out


def parse_detail_page(html: str, card_link: str, source_config: SourceConfig) -> Detail:
    log.info("Starting parsing detail for link: %s", card_link)

    pop = extract_pop_data(html)
    soup = BeautifulSoup(html, "lxml", parse_only=_PARSE_ONLY)

    graded_prices_by_grade = extract_prices_table(soup)
    grades_1_to_10 = map_prices_to_1_to_10(graded_prices_by_grade)
    grade_ebay_tables = extract_ebay_tables(soup)
    card_img_link = extract_img_link(soup)
    ungraded_price = graded_prices_by_grade.get("ungraded")
    ev, profit = enrich_detail(pop, graded_prices_by_grade, ungraded_price)

    detail = Detail(
        card_link=card_link,
        card_name=extract_card_name(soup),
        card_num=extract_card_num(soup),
        source=getattr(source_config, "source", None),
        pop=pop,
        graded_prices_by_grade=graded_prices_by_grade,
        grades_1_to_10=grades_1_to_10,
        grade7_dist=grade_ebay_tables["7"],
        grade8_dist=grade_ebay_tables["8"],
        grade9_dist=grade_ebay_tables["9"],
        grade10_dist=grade_ebay_tables["10"],
        ungraded_price=ungraded_price,
        card_img_link=card_img_link,
        expected_value=ev,
        expected_profit=profit,
    )

    log.info("Parsed detail for card %r (link: %s)", detail.card_name, detail.card_link)
    return detail
