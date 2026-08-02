from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macro_engine.decision.assets import (
    build_workspace,
    get_available_assets,
)
from macro_engine.decision.snapshots import (
    DecisionSnapshot,
    SnapshotChange,
    build_snapshot,
    compare_snapshots,
    find_last_material_change_date,
    load_latest_snapshot,
)
from macro_engine.decision.workspace import (
    DecisionWorkspaceResult,
)


@dataclass(frozen=True)
class ActiveIdea:
    asset_key: str
    display_name: str
    asset_class: str

    macro_direction: str
    directional_score: float
    model_confidence: float
    model_conviction: float

    alignment: str
    pricing_status: str
    stance: str

    current_snapshot: DecisionSnapshot
    previous_snapshot: DecisionSnapshot | None
    existing_today: DecisionSnapshot | None

    changes: tuple[SnapshotChange, ...]
    has_material_change: bool
    needs_attention: bool

    status_label: str
    summary: str

    last_material_change_date: date | None
    days_since_material_change: int | None

    workspace: DecisionWorkspaceResult


def _days_since(
    current_date: date,
    previous_date: date | None,
) -> int | None:
    if previous_date is None:
        return None

    return max(
        (current_date - previous_date).days,
        0,
    )


def _build_status(
    *,
    current_snapshot: DecisionSnapshot,
    previous_snapshot: DecisionSnapshot | None,
    existing_today: DecisionSnapshot | None,
    has_material_change: bool,
    changes: tuple[SnapshotChange, ...],
) -> tuple[str, str, bool]:
    if previous_snapshot is None:
        if existing_today is None:
            return (
                "Baseline Not Yet Saved",
                (
                    "Save the current state to establish a baseline "
                    "for future comparisons."
                ),
                True,
            )

        return (
            "Baseline Established",
            "This is the first saved state for this asset.",
            False,
        )

    if has_material_change:
        material_count = sum(
            change.material
            for change in changes
        )

        label = (
            "Material Change Detected"
            if material_count == 1
            else f"{material_count} Material Changes Detected"
        )

        return (
            label,
            (
                "The current state has changed materially since "
                f"{previous_snapshot.snapshot_date:%B %d, %Y}."
            ),
            True,
        )

    if changes:
        return (
            "No Material Change",
            (
                "Only secondary market context has changed since "
                f"{previous_snapshot.snapshot_date:%B %d, %Y}."
            ),
            False,
        )

    return (
        "Unchanged",
        (
            "No tracked decision fields have changed since "
            f"{previous_snapshot.snapshot_date:%B %d, %Y}."
        ),
        False,
    )


def build_active_idea(
    *,
    asset_key: str,
    asset_class: str,
    horizon_months: int | None = None,
) -> ActiveIdea:
    workspace = build_workspace(
        asset_key=asset_key,
        horizon_months=horizon_months,
    )

    current_snapshot = build_snapshot(workspace)

    previous_snapshot = load_latest_snapshot(
        asset_key,
        before_date=current_snapshot.snapshot_date,
    )

    latest_saved_snapshot = load_latest_snapshot(
        asset_key,
    )

    existing_today = (
        latest_saved_snapshot
        if (
            latest_saved_snapshot is not None
            and latest_saved_snapshot.snapshot_date
            == current_snapshot.snapshot_date
        )
        else None
    )

    comparison = compare_snapshots(
        current=current_snapshot,
        previous=previous_snapshot,
    )

    last_material_change_date = (
        find_last_material_change_date(asset_key)
    )

    if (
        previous_snapshot is not None
        and comparison.has_material_change
    ):
        last_material_change_date = (
            current_snapshot.snapshot_date
        )

    if (
        last_material_change_date is None
        and existing_today is not None
    ):
        last_material_change_date = (
            existing_today.snapshot_date
        )

    (
        status_label,
        summary,
        needs_attention,
    ) = _build_status(
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        existing_today=existing_today,
        has_material_change=(
            comparison.has_material_change
        ),
        changes=comparison.changes,
    )

    return ActiveIdea(
        asset_key=workspace.asset_key,
        display_name=workspace.display_name,
        asset_class=asset_class,
        macro_direction=workspace.idea.model_direction,
        directional_score=(
            workspace.idea.directional_score
        ),
        model_confidence=(
            workspace.idea.model_confidence
        ),
        model_conviction=(
            workspace.idea.model_conviction
        ),
        alignment=workspace.alignment.label,
        pricing_status=workspace.pricing.label,
        stance=workspace.decision.stance,
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        existing_today=existing_today,
        changes=comparison.changes,
        has_material_change=(
            comparison.has_material_change
        ),
        needs_attention=needs_attention,
        status_label=status_label,
        summary=summary,
        last_material_change_date=(
            last_material_change_date
        ),
        days_since_material_change=_days_since(
            current_date=current_snapshot.snapshot_date,
            previous_date=last_material_change_date,
        ),
        workspace=workspace,
    )


def _priority_rank(idea: ActiveIdea) -> int:
    if idea.has_material_change:
        return 0

    if idea.existing_today is None:
        return 1

    if idea.needs_attention:
        return 2

    return 3


def _stance_rank(stance: str) -> int:
    ranks = {
        "READY FOR REVIEW": 0,
        "WATCH": 1,
        "REVIEW": 2,
    }

    return ranks.get(
        stance,
        3,
    )


def build_active_ideas(
    *,
    asset_class: str | None = None,
    horizon_months: int | None = None,
) -> tuple[ActiveIdea, ...]:
    available_assets = get_available_assets()

    if asset_class is not None:
        available_assets = tuple(
            asset
            for asset in available_assets
            if asset.asset_class == asset_class
        )

    ideas: list[ActiveIdea] = []

    for asset in available_assets:
        idea = build_active_idea(
            asset_key=asset.key,
            asset_class=asset.asset_class,
            horizon_months=(
                horizon_months
                if horizon_months is not None
                else asset.default_horizon_months
            ),
        )

        ideas.append(idea)

    ideas.sort(
        key=lambda idea: (
            _priority_rank(idea),
            _stance_rank(idea.stance),
            -abs(idea.directional_score),
            idea.display_name,
        )
    )

    return tuple(ideas)


def get_attention_ideas(
    *,
    asset_class: str | None = None,
    horizon_months: int | None = None,
) -> tuple[ActiveIdea, ...]:
    return tuple(
        idea
        for idea in build_active_ideas(
            asset_class=asset_class,
            horizon_months=horizon_months,
        )
        if idea.needs_attention
    )


def get_stable_ideas(
    *,
    asset_class: str | None = None,
    horizon_months: int | None = None,
) -> tuple[ActiveIdea, ...]:
    return tuple(
        idea
        for idea in build_active_ideas(
            asset_class=asset_class,
            horizon_months=horizon_months,
        )
        if not idea.needs_attention
    )