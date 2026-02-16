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