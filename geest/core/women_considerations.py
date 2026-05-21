# -*- coding: utf-8 -*-
"""Helpers for women considerations factor enablement rules."""

__copyright__ = "Copyright 2024, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"


def resolve_women_enabling_for_factor(factor_id: str, women_enabling: int) -> int:
    """Resolve women-enabling value with backward-compatibility rules.

    Args:
        factor_id: Factor identifier from the model.
        women_enabling: Original women-enabling value from model metadata.

    Returns:
        Effective women-enabling value to use for enable/disable logic.
    """
    if factor_id.lower() == "education" and women_enabling == 0:
        return 1
    return women_enabling
