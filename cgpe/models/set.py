# cgpe/models/set.py

from dataclasses import dataclass
from cgpe.scrape.sources.base import SourceConfig
from typing import List

@dataclass
class SetPage:
    set_link: str
    detail_links: List[str]
    source_config: SourceConfig
