# cgpe/analysis/profit_analysis.py

from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


def calculate_profit(
    ungraded_price: float,
    expected_value: float,
    commission_rate: float = 0.15,
    purchase_tax: float = 0.1,
    grading_cost: float = 40,
) -> float:
    log.info("Starting profit calculation")

    log.debug(
        "Inputs: ungraded_price=%.2f expected_value=%.2f "
        "commission_rate=%.3f purchase_tax=%.3f grading_cost=%.2f",
        ungraded_price,
        expected_value,
        commission_rate,
        purchase_tax,
        grading_cost,
    )

    cost = ungraded_price * (1 + purchase_tax) + grading_cost
    rev = expected_value * (1 - commission_rate)
    profit = rev - cost

    log.debug(
        "Computed cost=%.2f revenue=%.2f profit=%.2f",
        cost,
        rev,
        profit,
    )

    log.info("Profit calculated: %.2f", profit)

    return profit