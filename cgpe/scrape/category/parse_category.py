# cgpe/scrape/set/parse_set.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


@dataclass
class CategoryPage:
    config: SourceConfig
    set_links: List[str]


def extract_set_links(soup: BeautifulSoup) -> List[str]:
    log.debug("Extracting set links from category HTML")

    links: List[str] = []

    box = soup.select_one("div.home-box.all")
    if box is None:
        log.warning("Could not find container div.home-box.all")
        return links

    ul = box.find("ul")
    if ul is None:
        log.warning("Could not find <ul> inside category container")
        return links

    a_tags = ul.find_all("a", href=True)
    log.debug("Found %d anchor tags", len(a_tags))

    for a in a_tags:
        links.append(a["href"])

    log.debug("Extracted %d raw set links", len(links))
    return links


def parse_category_page(
    html: str,
    source_config: SourceConfig,
) -> CategoryPage:
    log.info("Parsing category page")

    soup = BeautifulSoup(html, "html.parser")

    raw_links = extract_set_links(soup)

    set_links = [
        urljoin(source_config.base_url, link)
        for link in raw_links
    ]

    log.info("Parsed category page: %d set links", len(set_links))
    log.debug("Resolved base URL: %s", source_config.base_url)

    return CategoryPage(
        config=source_config,
        set_links=set_links,
    )
