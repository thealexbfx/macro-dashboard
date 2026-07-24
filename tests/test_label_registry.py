"""Tests for context-aware MacroLens labels."""

from macro_engine.labels import (
    classify_breadth,
    classify_state,
    classify_trend,
)


def test_growth_state_labels():
    assert classify_state("growth", 0.70) == "Very Strong"
    assert classify_state("growth", 0.30) == "Strong"
    assert classify_state("growth", 0.00) == "Normal"
    assert classify_state("growth", -0.30) == "Weak"
    assert classify_state("growth", -0.70) == "Very Weak"


def test_inflation_state_labels():
    assert classify_state("inflation", 0.70) == "Very High Pressure"
    assert classify_state("inflation", 0.30) == "High Pressure"
    assert classify_state("inflation", 0.00) == "Normal Pressure"
    assert classify_state("inflation", -0.30) == "Low Pressure"
    assert classify_state("inflation", -0.70) == "Very Low Pressure"


def test_growth_trend_labels():
    assert classify_trend("growth", 0.30) == "Improving"
    assert classify_trend("growth", 0.00) == "Stable"
    assert classify_trend("growth", -0.30) == "Deteriorating"


def test_inflation_trend_labels():
    assert classify_trend("inflation", 0.30) == "Accelerating"
    assert classify_trend("inflation", 0.00) == "Stable"
    assert classify_trend("inflation", -0.30) == "Cooling"


def test_growth_breadth_labels():
    assert classify_breadth("growth", 1.00) == "Broadly Positive"
    assert classify_breadth("growth", 0.50) == "Mostly Positive"
    assert classify_breadth("growth", 0.00) == "Mixed"
    assert classify_breadth("growth", -0.50) == "Mostly Negative"
    assert classify_breadth("growth", -1.00) == "Broadly Negative"


def test_inflation_breadth_labels():
    assert classify_breadth("inflation", 1.00) == "Broadly Inflationary"
    assert classify_breadth("inflation", 0.50) == "Mostly Inflationary"
    assert classify_breadth("inflation", 0.00) == "Mixed"
    assert classify_breadth("inflation", -0.50) == "Mostly Disinflationary"
    assert classify_breadth("inflation", -1.00) == "Broadly Disinflationary"


def test_unknown_pillar_uses_default_labels():
    assert classify_state("unknown", 0.70) == "Very Strong"
    assert classify_trend("unknown", 0.30) == "Improving"
    assert classify_breadth("unknown", 1.00) == "Broadly Positive"