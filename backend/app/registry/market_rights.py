"""Availability policy for market feeds used by the research APIs."""

from backend.app.registry.markets import MarketSpec

MARKET_RIGHTS_MESSAGE = "Market observations are withheld pending source rights review."
MARKET_RIGHTS_CODE = "market_source_rights_pending"


def market_observations_withheld(spec: MarketSpec | None) -> bool:
    # The existing Treasury yield path uses Federal Reserve data. Other market
    # feeds have no recorded grant here and require an explicit review.
    return spec is not None and spec.provider != "fred"
