from browserforge.headers import HeaderGenerator
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

_gen = HeaderGenerator()


def build_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = _gen.generate()

    headers["Accept-Encoding"] = "gzip, deflate"
    headers["Accept-Language"] = "en-US,en;q=0.9"

    if extra:
        headers.update(extra)

    log.debug(
        "Headers built: UA=%s | Accept-Encoding=%s",
        headers.get("User-Agent"),
        headers.get("Accept-Encoding"),
    )

    return headers
