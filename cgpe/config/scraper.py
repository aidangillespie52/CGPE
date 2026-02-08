from dataclasses import dataclass

@dataclass
class ScraperConfig:
    concurrency: int = 4
    timeout_seconds: int = 30
    max_retries: int = 3
    header_pool_size: int = 6
    max_cursor: int = 1000