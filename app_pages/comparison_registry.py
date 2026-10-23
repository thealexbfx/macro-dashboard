"""Compatibility import: the root registry owns comparison definitions."""
from comparison_registry import (COMPARISON_REGISTRY, build_comparison_registry,
                                 comparison_options, get_comparison_series)

__all__ = ["COMPARISON_REGISTRY", "build_comparison_registry", "comparison_options", "get_comparison_series"]
