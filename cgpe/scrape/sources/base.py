# cgpe/scrape/sources/base.py

from dataclasses import dataclass
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

@dataclass
class SourceConfig:
    source: str
    category_link: str
    base_url: str