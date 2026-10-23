from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Callable

from backend.app.infrastructure.cache import load_macro_cache
from macro_engine.models.environment import MacroEnvironmentResult


class MacroServiceError(RuntimeError):
    """Raised when a requested macro environment cannot be served."""


@dataclass(frozen=True)
class MacroPillarView:
    id: str
    name: str
    state_score: float
    state_label: str
    trend_score: float
    trend_label: str
    breadth_score: float
    breadth_label: str
    confidence_score: float
    confidence_label: str
    key_drivers: tuple[str, ...]
    flags: tuple[str, ...]


@dataclass(frozen=True)
class MacroEnvironmentView:
    economy: str
    as_of_date: date | None
    overall_direction: str
    environment_label: str
    environment_summary: str
    activity_score: float
    activity_label: str
    inflation_impulse_score: float
    inflation_impulse_label: str
    financial_impulse_score: float
    financial_impulse_label: str
    confidence_score: float
    confidence_label: str
    conviction_score: float
    conviction_label: str
    key_drivers: tuple[str, ...]
    flags: tuple[str, ...]
    pillars: tuple[MacroPillarView, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation for API/front-end consumers."""
        payload = asdict(self)
        if self.as_of_date is not None:
            payload["as_of_date"] = self.as_of_date.isoformat()
        return payload


COUNTRY_ALIASES = {
    "us": "usa",
    "usa": "usa",
    "united-states": "usa",
    "united_states": "usa",
    "euro": "euro",
    "euro-area": "euro",
    "euro_area": "euro",
    "eu": "euro",
    "uk": "uk",
    "united-kingdom": "uk",
    "united_kingdom": "uk",
    "japan": "japan",
    "jp": "japan",
}

CACHE_NAMES = {
    "usa": "usa_environment",
    "euro": "euro_environment",
    "uk": "uk_environment",
    "japan": "japan_environment",
}


class MacroService:
    """Serve current MacroLens environments without depending on Streamlit.

    V1 intentionally reads the existing shared/local environment cache instead
    of invoking Streamlit page loaders. Refreshing data remains a separate
    concern. This gives FastAPI and any future frontend a stable boundary
    around the existing MacroLens research engine.
    """

    def __init__(self, cache_loader: Callable[[str], Any] = load_macro_cache) -> None:
        self._cache_loader = cache_loader

    @staticmethod
    def _normalise_country(country: str) -> str:
        key = country.strip().lower().replace(" ", "-")
        normalised = COUNTRY_ALIASES.get(key)
        if normalised is None:
            supported = ", ".join(sorted(CACHE_NAMES))
            raise MacroServiceError(
                f"Unsupported economy '{country}'. Supported economies: {supported}."
            )
        return normalised

    def get_current_environment(self, country: str) -> MacroEnvironmentView:
        country_key = self._normalise_country(country)
        cache_name = CACHE_NAMES[country_key]

        try:
            result = self._cache_loader(cache_name)
        except FileNotFoundError as exc:
            raise MacroServiceError(
                f"No cached macro environment is available for '{country_key}'."
            ) from exc
        except Exception as exc:
            raise MacroServiceError(
                f"Could not load macro environment for '{country_key}'."
            ) from exc

        if not isinstance(result, MacroEnvironmentResult):
            raise MacroServiceError(
                f"Cached value '{cache_name}' is not a MacroEnvironmentResult."
            )

        return self._to_view(result)

    @staticmethod
    def _to_view(result: MacroEnvironmentResult) -> MacroEnvironmentView:
        pillars = tuple(
            MacroPillarView(
                id=pillar.pillar_id,
                name=pillar.name,
                state_score=pillar.state_score,
                state_label=pillar.state_label,
                trend_score=pillar.trend_score,
                trend_label=pillar.trend_label,
                breadth_score=pillar.breadth_score,
                breadth_label=pillar.breadth_label,
                confidence_score=pillar.confidence_score,
                confidence_label=pillar.confidence_label,
                key_drivers=tuple(pillar.key_drivers),
                flags=tuple(pillar.flags),
            )
            for pillar in result.pillar_results
        )

        return MacroEnvironmentView(
            economy=result.economy,
            as_of_date=result.as_of_date,
            overall_direction=result.overall_direction,
            environment_label=result.environment_label,
            environment_summary=result.environment_summary,
            activity_score=result.activity_score,
            activity_label=result.activity_label,
            inflation_impulse_score=result.inflation_impulse_score,
            inflation_impulse_label=result.inflation_impulse_label,
            financial_impulse_score=result.financial_impulse_score,
            financial_impulse_label=result.financial_impulse_label,
            confidence_score=result.confidence_score,
            confidence_label=result.confidence_label,
            conviction_score=result.environment_conviction_score,
            conviction_label=result.environment_conviction_label,
            key_drivers=tuple(result.key_drivers),
            flags=tuple(result.flags),
            pillars=pillars,
        )
