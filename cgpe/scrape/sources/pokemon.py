# cgpe/scrape/sources/pokemon.py

from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

POKEMON_PRICECHARTING = SourceConfig(
    source="Pokemon PriceCharting",
    category_link="https://www.pricecharting.com/category/pokemon-cards",
    base_url="https://www.pricecharting.com"
)