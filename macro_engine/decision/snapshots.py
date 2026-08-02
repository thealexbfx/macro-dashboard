from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import json
from pathlib import Path

from macro_engine.decision.workspace import DecisionWorkspaceResult


SNAPSHOT_DIRECTORY = Path("research_outputs/decision_snapshots")


@dataclass(frozen=True)
class DecisionSnapshot:
    asset_key: str
    display_name: str
    snapshot_date: date
    created_at: datetime

    macro_direction: str
    directional_score: float
    model_confidence: float
    model_conviction: float
    historical_support: str

    current_price: float
    price_trend: str
    momentum: str
    volatility_state: str

    alignment: str
    pricing_status: str
    decision_stance: str

    thesis: str


@dataclass(frozen=True)
class SnapshotChange:
    field: str
    label: str
    previous_value: str
    current_value: str
    material: bool


@dataclass(frozen=True)
class SnapshotComparison:
    current: DecisionSnapshot
    previous: DecisionSnapshot | None
    changes: tuple[SnapshotChange, ...]
    has_material_change: bool
    summary: str


def build_snapshot(
    workspace: DecisionWorkspaceResult,
) -> DecisionSnapshot:
    idea = workspace.idea
    market = workspace.market

    return DecisionSnapshot(
        asset_key=workspace.asset_key,
        display_name=workspace.display_name,
        snapshot_date=max(
            idea.as_of_date,
            market.as_of_date,
        ),
        created_at=datetime.now(),
        macro_direction=idea.model_direction,
        directional_score=idea.directional_score,
        model_confidence=idea.model_confidence,
        model_conviction=idea.model_conviction,
        historical_support=idea.historical_support,
        current_price=market.current_price,
        price_trend=market.trend_label,
        momentum=market.momentum_label,
        volatility_state=market.volatility_label,
        alignment=workspace.alignment.label,
        pricing_status=workspace.pricing.label,
        decision_stance=workspace.decision.stance,
        thesis=idea.thesis,
    )


def _snapshot_path(
    asset_key: str,
    snapshot_date: date,
) -> Path:
    asset_directory = SNAPSHOT_DIRECTORY / asset_key
    asset_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return asset_directory / f"{snapshot_date.isoformat()}.json"


def save_snapshot(
    snapshot: DecisionSnapshot,
) -> Path:
    path = _snapshot_path(
        asset_key=snapshot.asset_key,
        snapshot_date=snapshot.snapshot_date,
    )

    payload = asdict(snapshot)
    payload["snapshot_date"] = snapshot.snapshot_date.isoformat()
    payload["created_at"] = snapshot.created_at.isoformat()

    path.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def load_snapshot(
    path: Path,
) -> DecisionSnapshot:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    payload["snapshot_date"] = date.fromisoformat(
        payload["snapshot_date"]
    )
    payload["created_at"] = datetime.fromisoformat(
        payload["created_at"]
    )

    return DecisionSnapshot(**payload)


def load_latest_snapshot(
    asset_key: str,
    *,
    before_date: date | None = None,
) -> DecisionSnapshot | None:
    asset_directory = SNAPSHOT_DIRECTORY / asset_key

    if not asset_directory.exists():
        return None

    candidate_paths = sorted(
        asset_directory.glob("*.json"),
        reverse=True,
    )

    for path in candidate_paths:
        snapshot = load_snapshot(path)

        if (
            before_date is None
            or snapshot.snapshot_date < before_date
        ):
            return snapshot

    return None

def load_snapshot_history(
    asset_key: str,
) -> tuple[DecisionSnapshot, ...]:
    asset_directory = SNAPSHOT_DIRECTORY / asset_key

    if not asset_directory.exists():
        return ()

    snapshots = [
        load_snapshot(path)
        for path in sorted(asset_directory.glob("*.json"))
    ]

    return tuple(snapshots)


def find_last_material_change_date(
    asset_key: str,
) -> date | None:
    history = load_snapshot_history(asset_key)

    if not history:
        return None

    # The first saved snapshot establishes the baseline.
    last_material_change = history[0].snapshot_date

    for previous, current in zip(
        history,
        history[1:],
    ):
        comparison = compare_snapshots(
            current=current,
            previous=previous,
        )

        if comparison.has_material_change:
            last_material_change = current.snapshot_date

    return last_material_change

def _format_value(
    field: str,
    value: object,
) -> str:
    if field in {
        "directional_score",
    }:
        return f"{float(value):+.2f}"

    if field in {
        "model_confidence",
        "model_conviction",
    }:
        return f"{float(value):.0%}"

    if field == "current_price":
        return f"{float(value):.4f}"

    return str(value)


def compare_snapshots(
    current: DecisionSnapshot,
    previous: DecisionSnapshot | None,
) -> SnapshotComparison:
    if previous is None:
        return SnapshotComparison(
            current=current,
            previous=None,
            changes=(),
            has_material_change=True,
            summary="First saved snapshot for this asset.",
        )

    field_rules = (
        ("macro_direction", "Macro bias", True),
        ("price_trend", "Price trend", True),
        ("momentum", "Momentum", True),
        ("alignment", "Evidence alignment", True),
        ("pricing_status", "Pricing status", True),
        ("decision_stance", "Decision stance", True),
        ("historical_support", "Historical support", True),
        ("volatility_state", "Volatility state", False),
    )

    changes: list[SnapshotChange] = []

    for field, label, material in field_rules:
        previous_value = getattr(previous, field)
        current_value = getattr(current, field)

        if previous_value != current_value:
            changes.append(
                SnapshotChange(
                    field=field,
                    label=label,
                    previous_value=_format_value(
                        field,
                        previous_value,
                    ),
                    current_value=_format_value(
                        field,
                        current_value,
                    ),
                    material=material,
                )
            )

    score_change = abs(
        current.directional_score
        - previous.directional_score
    )

    if score_change >= 0.10:
        changes.append(
            SnapshotChange(
                field="directional_score",
                label="Macro score",
                previous_value=_format_value(
                    "directional_score",
                    previous.directional_score,
                ),
                current_value=_format_value(
                    "directional_score",
                    current.directional_score,
                ),
                material=True,
            )
        )

    confidence_change = abs(
        current.model_confidence
        - previous.model_confidence
    )

    if confidence_change >= 0.05:
        changes.append(
            SnapshotChange(
                field="model_confidence",
                label="Model confidence",
                previous_value=_format_value(
                    "model_confidence",
                    previous.model_confidence,
                ),
                current_value=_format_value(
                    "model_confidence",
                    current.model_confidence,
                ),
                material=True,
            )
        )

    conviction_change = abs(
        current.model_conviction
        - previous.model_conviction
    )

    if conviction_change >= 0.05:
        changes.append(
            SnapshotChange(
                field="model_conviction",
                label="Model conviction",
                previous_value=_format_value(
                    "model_conviction",
                    previous.model_conviction,
                ),
                current_value=_format_value(
                    "model_conviction",
                    current.model_conviction,
                ),
                material=True,
            )
        )

    material_changes = [
        change
        for change in changes
        if change.material
    ]

    if material_changes:
        summary = (
            f"{len(material_changes)} material change"
            + (
                ""
                if len(material_changes) == 1
                else "s"
            )
            + " detected since the previous snapshot."
        )
    elif changes:
        summary = (
            "No material change. Only secondary market context changed."
        )
    else:
        summary = "No change since the previous snapshot."

    return SnapshotComparison(
        current=current,
        previous=previous,
        changes=tuple(changes),
        has_material_change=bool(material_changes),
        summary=summary,
    )