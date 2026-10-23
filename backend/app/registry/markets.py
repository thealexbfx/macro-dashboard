from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSpec:
    key: str
    name: str
    provider: str
    provider_id: str
    kind: str  # price | yield
    aliases: tuple[str, ...]
    unit: str = ""
    representation: str = ""
    can_be_nonpositive: bool = False

    @property
    def research_metadata(self):
        from macro_engine.research.analytics import SeriesMetadata
        return SeriesMetadata(category="market", units=self.unit or ("%" if self.kind == "yield" else "unspecified"),
                              frequency="daily", representation=self.representation or self.kind,
                              can_be_nonpositive=self.can_be_nonpositive or self.kind == "yield", source=self.provider)


MARKETS: tuple[MarketSpec, ...] = (
    MarketSpec("gold", "Gold", "yahoo", "GC=F", "price", ("gold", "xau", "xauusd"), unit='USD / troy oz', representation='price', can_be_nonpositive=False),
    MarketSpec("sp500", "S&P 500", "yahoo", "^GSPC", "price", ("s&p 500", "s&p", "sp500", "stocks"), unit='index points', representation='index', can_be_nonpositive=False),
    MarketSpec("nasdaq", "Nasdaq", "yahoo", "^IXIC", "price", ("nasdaq", "nasdaq composite"), unit='index points', representation='index', can_be_nonpositive=False),
    MarketSpec("dxy", "US Dollar Index", "yahoo", "DX-Y.NYB", "price", ("dxy", "dollar index", "us dollar index"), unit='index points', representation='index', can_be_nonpositive=False),
    MarketSpec("wti", "WTI crude oil", "yahoo", "CL=F", "price", ("wti", "crude oil", "oil"), unit='USD / barrel', representation='signed_flow', can_be_nonpositive=True),
    MarketSpec("eurusd", "EUR/USD", "yahoo", "EURUSD=X", "price", ("eur/usd", "eurusd", "euro dollar"), unit='USD per EUR', representation='price', can_be_nonpositive=False),
    MarketSpec("gbpusd", "GBP/USD", "yahoo", "GBPUSD=X", "price", ("gbp/usd", "gbpusd", "pound dollar"), unit='USD per GBP', representation='price', can_be_nonpositive=False),
    MarketSpec("usdjpy", "USD/JPY", "yahoo", "JPY=X", "price", ("usd/jpy", "usdjpy", "dollar yen"), unit='JPY per USD', representation='price', can_be_nonpositive=False),
    MarketSpec("us2y", "US 2Y Treasury yield", "fred", "DGS2", "yield", ("2-year yield", "2 year yield", "2y yield", "us2y", "2 year treasury")),
    MarketSpec("us10y", "US 10Y Treasury yield", "fred", "DGS10", "yield", ("10-year yield", "10 year yield", "10y yield", "us10y", "10 year treasury")),
    MarketSpec("us30y", "US 30Y Treasury yield", "fred", "DGS30", "yield", ("30-year yield", "30 year yield", "30y yield", "us30y", "30 year treasury")),
)


class MarketRegistry:
    def __init__(self, specs: tuple[MarketSpec, ...] = MARKETS) -> None:
        self.specs = specs
        self._by_key = {s.key: s for s in specs}

    def get(self, key: str) -> MarketSpec | None:
        return self._by_key.get(key)

    def resolve_all(self, text: str) -> tuple[MarketSpec, ...]:
        q = " ".join(text.lower().split())
        hits: list[tuple[int, MarketSpec]] = []
        for spec in self.specs:
            best = max((len(alias) for alias in spec.aliases if alias in q), default=0)
            if best:
                hits.append((best, spec))
        hits.sort(key=lambda x: -x[0])
        out: list[MarketSpec] = []
        seen: set[str] = set()
        for _, spec in hits:
            if spec.key not in seen:
                out.append(spec)
                seen.add(spec.key)
        return tuple(out)
