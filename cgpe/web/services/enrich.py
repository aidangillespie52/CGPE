# cgpe/web/services/enrich.py

import json, ast

from cgpe.analysis.expected_value import expected_value_from_population_and_prices
from cgpe.analysis.profit_analysis import calculate_profit

from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

def coerce_strings_to_dicts(d: dict) -> dict:
    for k, v in d.items():
        if isinstance(v, str):
            try:
                d[k] = json.loads(v)
            except Exception:
                try:
                    d[k] = ast.literal_eval(v)
                except Exception:
                    pass
    return d

# TODO: move this logic out of the app.py file
def enrich_detail(detail: dict) -> dict:
    log.debug("enrich_detail start: card_link=%r", detail.get("card_link"))

    # 1) coerce
    try:
        detail = coerce_strings_to_dicts(detail)
        log.debug("after coerce: pop_json type=%s, graded_prices_json type=%s",
                  type(detail.get("pop_json")).__name__,
                  type(detail.get("graded_prices_json")).__name__)
    except Exception as e:
        log.exception("coerce_strings_to_dicts failed: %s", e)
        return detail

    # defaults
    detail.setdefault("expected_value", None)
    detail.setdefault("expected_profit", None)

    # 2) pop
    pop_json = detail.get("pop_json") or {}
    log.debug("pop_json raw type=%s value=%r", type(pop_json).__name__, pop_json)

    # NOTE: you probably meant dict, not list
    psa_pop = pop_json.get("psa") if isinstance(pop_json, dict) else None
    log.debug("psa_pop type=%s value=%r", type(psa_pop).__name__, psa_pop)

    if not psa_pop:
        log.debug("missing/empty psa_pop -> returning early")
        return detail

    # 3) prices
    raw_prices = detail.get("graded_prices_json")
    log.debug("graded_prices_json raw type=%s value=%r", type(raw_prices).__name__, raw_prices)

    if isinstance(raw_prices, str):
        try:
            prices_json = json.loads(raw_prices)
            log.debug("json.loads(prices) ok -> type=%s keys=%r",
                      type(prices_json).__name__,
                      list(prices_json.keys()) if isinstance(prices_json, dict) else None)
        except Exception as e:
            log.exception("json.loads(prices) failed: %s", e)
            return detail
    elif isinstance(raw_prices, dict):
        prices_json = raw_prices
        log.debug("prices already dict -> keys=%r", list(prices_json.keys()))
    else:
        prices_json = {}
        log.debug("prices not str/dict -> treating as empty dict")

    if not isinstance(prices_json, dict) or not prices_json:
        log.debug("prices_json empty/non-dict -> returning early")
        return detail

    prices_list = [prices_json.get(f"grade {i}") for i in range(1, 10)] + [prices_json.get("psa 10")]
    log.debug("prices_list=%r", prices_list)

    # 4) compute
    try:
        ev = expected_value_from_population_and_prices(psa_pop, prices_list)
        profit = calculate_profit(
            ungraded_price=detail.get("ungraded_price") or 0,
            expected_value=ev,
        )
        log.debug("computed ev=%r profit=%r", ev, profit)
    except Exception as e:
        log.exception("EV/profit computation failed: %s", e)
        return detail

    detail["expected_value"] = ev
    detail["expected_profit"] = profit

    log.debug("enrich_detail success: card_link=%r", detail.get("card_link"))
    return detail