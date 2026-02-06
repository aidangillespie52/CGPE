# cgpe/scrape/detail/parse_detail.py

from dataclasses import dataclass
from typing import Optional, Dict, List
import json
import re
from pprint import pformat
from bs4 import BeautifulSoup

from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

VGPC_POP_RE = re.compile(r"VGPC\.pop_data\s*=\s*(\{.*?\})\s*;", re.DOTALL)


@dataclass
class Detail:
    card_link: str
    card_name: str
    card_num: str
    source_config: SourceConfig
    pop: Optional[dict]
    graded_prices_by_grade: Dict[str, Optional[float]]
    grades_1_to_10: List[Optional[float]]
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
            ")"
        )


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
    log.debug("Extracting graded prices table")

    container = soup.find("div", id="full-prices")
    if not container:
        log.error("Missing prices container: div#full-prices")
        raise ValueError("Could not find prices container: div#full-prices")

    table = container.find("table")
    if not table:
        log.error("Missing prices table inside div#full-prices")
        raise ValueError("Could not find prices table inside div#full-prices")

    out: Dict[str, Optional[float]] = {}

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        grade = clean_grade_text(tds[0].get_text(" ", strip=True))
        price = parse_price(tds[-1].get_text(" ", strip=True))
        out[grade] = price

    log.info("Extracted %d graded price entries", len(out))
    return out


def extract_pop_data(html: str) -> Optional[dict]:
    log.debug("Extracting population data")

    m = VGPC_POP_RE.search(html)
    if not m:
        log.info("No population data found on page")
        return None

    try:
        pop = json.loads(m.group(1))
        log.info("Population data extracted (%d keys)", len(pop))
        return pop
    except json.JSONDecodeError:
        log.warning("Failed to decode population JSON")
        return None


def extract_card_name(soup: BeautifulSoup) -> str:
    div = soup.find("div", id="full_details")
    if not div:
        log.error("Missing div#full_details for card name")
        raise ValueError("Could not find card name: div#full_details")

    h2 = div.find("h2")
    if not h2:
        log.error("Missing h2 inside div#full_details")
        raise ValueError("Could not find card name inside div#full_details h2")

    name = clean_name(h2.text)
    log.debug("Extracted card name: %s", name)
    return name


def extract_card_num(soup: BeautifulSoup) -> str:
    td = soup.find("td", itemprop="model-number")
    if not td:
        log.warning("Card number not found (td[itemprop=model-number])")
        return ""

    num = clean_card_num(td.text)
    log.debug("Extracted card number: %s", num)
    return num


# -----------------------------
# Composition
# -----------------------------

def map_prices_to_1_to_10(
    prices: Dict[str, Optional[float]]
) -> List[Optional[float]]:
    log.debug("Mapping prices to grade 1–10 vector")

    out: List[Optional[float]] = []
    for i in range(1, 10):
        out.append(prices.get(f"grade {i}"))

    out.append(prices.get("psa 10") or prices.get("grade 10"))
    return out


def parse_detail_page(
    *,
    html: str,
    card_link: str,
    source_config: SourceConfig,
) -> Detail:
    log.info("Parsing detail page: %s", card_link)

    soup = BeautifulSoup(html, "html.parser")

    pop = extract_pop_data(html)
    graded_prices_by_grade = extract_prices_table(soup)
    grades_1_to_10 = map_prices_to_1_to_10(graded_prices_by_grade)

    detail = Detail(
        ungraded_price=graded_prices_by_grade.get("ungraded"),
        card_link=card_link,
        card_name=extract_card_name(soup),
        card_num=extract_card_num(soup),
        source_config=source_config,
        pop=pop,
        graded_prices_by_grade=graded_prices_by_grade,
        grades_1_to_10=grades_1_to_10,
    )

    log.info(
        "Parsed detail page successfully: %s (grades=%d, pop=%s)",
        detail.card_name,
        len(detail.graded_prices_by_grade),
        "yes" if pop else "no",
    )

    return detail
