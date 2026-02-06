# cgpe/pipeline/set_pipeline.py

from cgpe.scrape.sources.base import SourceConfig
from cgpe.http.client import fetch_html
from cgpe.scrape.set.parse_set import SetPage, parse_set_page
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


async def run_set_pipeline(
    session,
    set_url: str,
    source_config: SourceConfig,
    headers: dict,
) -> SetPage:
    log.info("Starting set pipeline")

    log.debug("Fetching set page: %s", set_url)

    try:
        html = await fetch_html(
            session,
            url=set_url,
            headers=headers,
        )

        log.debug(
            "Fetched set HTML (%d characters) for %s",
            len(html),
            set_url,
        )

        set_page = parse_set_page(
            html=html,
            set_link=set_url,
            source_config=source_config,
        )

        log.info(
            "Parsed set page successfully: %s (%d detail links)",
            set_url,
            len(set_page.detail_links),
        )

        return set_page

    except Exception:
        log.exception("Set pipeline failed for %s", set_url)
        raise
