# cgpe/analysis/expected_value.py

import logging
from typing import Iterable, Sequence
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


def expected_value_from_population_and_prices(
    population: Sequence[float] | Iterable[float],
    prices: Sequence[float] | Iterable[float],
    *,
    require_same_length: bool = True,
    drop_nonpositive_population: bool = True,
    min_population: float = 0.0,
    require_price_if_population: bool = True,
) -> float:
    """
    Compute expected value using only grades with meaningful population support.

    - Grades with population <= min_population are ignored
    - Prices are only used where population exists
    """

    # ---- length validation ----
    if (
        require_same_length
        and isinstance(population, Sequence)
        and isinstance(prices, Sequence)
    ):
        if len(population) != len(prices):
            raise ValueError(
                f"population and prices length mismatch: {len(population)} vs {len(prices)}"
            )

    weighted_sum = 0.0
    total_pop = 0.0

    skipped_low_pop = 0
    skipped_no_price = 0
    processed = 0

    # ---- main accumulation ----
    for pop, price in zip(population, prices):
        pop_f = float(pop)
        price_f = float(price) if price is not None else None

        if not price_f:
            log.debug("Grade with population %.4f has no price, treating as None", pop_f)
            return 0.0
        
        # ---- population filters ----
        if drop_nonpositive_population and pop_f <= 0:
            skipped_low_pop += 1
            continue

        if pop_f < min_population:
            skipped_low_pop += 1
            continue

        # ---- price filter ----
        if require_price_if_population and price_f is None:
            skipped_no_price += 1
            continue
        
        weighted_sum += pop_f * price_f
        total_pop += pop_f
        processed += 1

        log.debug(
            "Included grade: pop=%.4f price=%.4f weighted_sum=%.4f total_pop=%.4f",
            pop_f,
            price_f,
            weighted_sum,
            total_pop,
        )

    if total_pop <= 0:
        log.warning(
            "EV undefined: no population mass after filtering "
            "(min_population=%.2f)",
            min_population,
        )
        return 0.0

    ev = weighted_sum / total_pop

    return ev
