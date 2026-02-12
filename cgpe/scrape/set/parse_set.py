# cgpe/scrape/set/parse_set.py

from dataclasses import dataclass
from typing import List
from pprint import pformat
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


@dataclass
class SetPage:
    set_link: str
    detail_links: List[str]
    source_config: SourceConfig


# -----------------------------
# Normalization helpers
# -----------------------------

def clean_set_name(text: str) -> str:
    return text.strip()


def parse_detail_row(row) -> str:
    a_tag = row.find("a", href=True)
    if a_tag:
        href = a_tag["href"]
        log.debug("Parsed detail row href=%s", href)
        return href
    log.debug("No link found in detail row")
    return ""


# -----------------------------
# Extractors (raw -> structured)
# -----------------------------

def extract_set_name(soup: BeautifulSoup) -> str:
    log.debug("Extracting set name")

    div = soup.find("div", id="console-header")
    if not div:
        log.warning("Could not find set header container: div#console-header")
        return "Unknown Set"

    h1 = div.find("h1")
    if h1:
        name = clean_set_name(h1.get_text())
        log.debug("Extracted set name: %s", name)
        return name

    log.warning("Could not find set name inside div#console-header h1")
    return "Unknown Set"


def extract_detail_links(soup: BeautifulSoup) -> List[str]:
    log.debug("Extracting detail links from set page")

    links: List[str] = []

    table = soup.find("table", id="games_table")
    if not table:
        log.warning("Could not find games table: table#games_table")
        return links

    trs = table.find_all("tr")
    log.debug("Found %d rows in games_table", len(trs))

    # Skip header row
    for tr in trs[1:]:
        href = parse_detail_row(tr)
        if href:
            links.append(href)

    log.info("Extracted %d detail links from set page", len(links))
    return links


# -----------------------------
# Composition / "public API"
# -----------------------------

def parse_set_data(
    data: List[List[dict]],
    set_link: str,
    source_config: SourceConfig,
) -> SetPage:
    log.info("Parsing set page: %s", set_link)
    log.debug("Set JSON size: %d records", len(data))

    detail_links: List[str] = []
    for obj in data:
        detail_link = urljoin(set_link + "/", obj.get("productUri", ""))
        if detail_link == set_link:
            log.debug("Skipping record with empty productUri")
            continue
        
        detail_link = detail_link.replace("/console/", "/game/")
        detail_links.append(detail_link)

    log.info("Parsed %d detail links from %s", len(detail_links), set_link)
    return SetPage(
        set_link=set_link,
        detail_links=detail_links,
        source_config=source_config,
    )