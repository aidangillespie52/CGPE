# cgpe/analysis/expected_value.py

from typing import Iterable, Sequence
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


def expected_value_from_population_and_prices(
    population: Sequence[float] | Iterable[float],
    prices: Sequence[float] | Iterable[float],
    require_same_length: bool = True,
    drop_nonpositive_population: bool = True,
) -> float:
    log.info("Starting expected value computation")

    # ---- length validation ----
    if (
        require_same_length
        and isinstance(population, Sequence)
        and isinstance(prices, Sequence)
    ):
        pop_len = len(population)
        price_len = len(prices)
        log.debug("Population length=%d, Prices length=%d", pop_len, price_len)

        if pop_len != price_len:
            log.error(
                "Length mismatch: population=%d prices=%d",
                pop_len,
                price_len,
            )
            raise ValueError(
                f"population and prices length mismatch: {pop_len} vs {price_len}"
            )

    weighted_sum = 0.0
    total_pop = 0.0
    skipped = 0
    processed = 0

    # ---- main accumulation ----
    for pop, price in zip(population, prices):
        pop_f = float(pop)

        if (drop_nonpositive_population and pop_f <= 0) or price is None:
            skipped += 1
            continue

        price_f = float(price)

        weighted_sum += pop_f * price_f
        total_pop += pop_f
        processed += 1

        log.debug(
            "Accumulated pop=%.4f price=%.4f weighted_sum=%.4f total_pop=%.4f",
            pop_f,
            price_f,
            weighted_sum,
            total_pop,
        )

    log.info(
        "Processed %d entries (skipped %d non-positive population values)",
        processed,
        skipped,
    )

    if total_pop <= 0:
        log.error("Total population is zero after filtering")
        return 0

    ev = weighted_sum / total_pop

    log.info("Expected value computed: %.4f", ev)
    log.debug(
        "Final weighted_sum=%.4f total_pop=%.4f",
        weighted_sum,
        total_pop,
    )

    return ev
