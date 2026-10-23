"""Additive research endpoint; existing Ask contracts remain intact."""

from typing import Literal

from fastapi import APIRouter, HTTPException

from backend.app.services.historical_relationships import (
    HistoricalRelationshipService,
    RelationshipSeriesRegistry,
)

router = APIRouter(prefix="/api/research/relationships", tags=["research"])


@router.get("/series")
def relationship_series():
    registry = RelationshipSeriesRegistry()
    return [{"key": spec.key, "name": spec.name} for spec in registry._specs.values()]


@router.get("")
def research_relationship(
    target: str,
    driver: str,
    timeframe: Literal[
        "6_months", "1_year", "3_years", "5_years", "10_years"
    ] = "5_years",
    economy: Literal["usa", "uk", "euro", "japan"] = "usa",
):
    try:
        return {
            "customer_answer": HistoricalRelationshipService()
            .analyze(target, driver, timeframe, economy)
            .to_dict()
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(
            status_code=503, detail="Relationship data is unavailable or insufficient."
        ) from exc
