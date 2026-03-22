"""Egg size classification using bounding box ratio method.

Converts pixel-space bounding box dimensions to real-world millimeters
using a known reference (nest box width), then classifies into USDA-approximate
size categories: small, medium, large, jumbo.
"""

from __future__ import annotations

# USDA-approximate egg height thresholds in millimeters.
# Classification uses strict greater-than: e.g., >63mm is jumbo.
SIZE_THRESHOLDS: dict[str, float] = {
    "jumbo": 63.0,   # > 63mm
    "large": 56.0,   # > 56mm
    "medium": 50.0,  # > 50mm
    # <= 50mm is "small"
}


def classify_size_from_mm(height_mm: float) -> str:
    """Classify egg size from height in millimeters.

    Args:
        height_mm: Egg height measurement in millimeters.

    Returns:
        Size category string: "jumbo", "large", "medium", or "small".
    """
    if height_mm > SIZE_THRESHOLDS["jumbo"]:
        return "jumbo"
    if height_mm > SIZE_THRESHOLDS["large"]:
        return "large"
    if height_mm > SIZE_THRESHOLDS["medium"]:
        return "medium"
    return "small"


def classify_by_ratio(
    egg_bbox: list,
    zone_rect: dict,
    nest_box_width_mm: float = 300.0,
) -> tuple[str, float]:
    """Classify egg size using bounding box ratio against known zone width.

    Computes pixel-to-mm conversion factor from the zone width (which maps
    to the physical nest box width), then converts egg bbox height to mm.

    Args:
        egg_bbox: Bounding box in [x1, y1, x2, y2] format.
        zone_rect: Zone rectangle dict with keys x1, y1, x2, y2.
        nest_box_width_mm: Physical width of the nest box in millimeters.

    Returns:
        Tuple of (size_category, height_mm) where height_mm is rounded to 1 decimal.
    """
    zone_width_px = zone_rect["x2"] - zone_rect["x1"]
    px_per_mm = zone_width_px / nest_box_width_mm
    egg_height_px = egg_bbox[3] - egg_bbox[1]  # y2 - y1
    egg_height_mm = egg_height_px / px_per_mm
    return classify_size_from_mm(egg_height_mm), round(egg_height_mm, 1)


class SizeClassifier:
    """Stateful size classifier that holds zone configuration.

    Wraps classify_by_ratio for convenient repeated classification
    with the same zone config.
    """

    def __init__(self, zone_config: dict, method: str = "bbox_ratio") -> None:
        """Initialize classifier with zone configuration.

        Args:
            zone_config: Dict with x1, y1, x2, y2, and optionally nest_box_width_mm.
            method: Classification method (currently only "bbox_ratio" supported).
        """
        self.zone_config = zone_config
        self.nest_box_width_mm: float = zone_config.get("nest_box_width_mm", 300.0)
        self.method = method

    def classify(self, egg_bbox: list) -> tuple[str, float]:
        """Classify a single egg's size from its bounding box.

        Args:
            egg_bbox: Bounding box in [x1, y1, x2, y2] format.

        Returns:
            Tuple of (size_category, height_mm).
        """
        return classify_by_ratio(egg_bbox, self.zone_config, self.nest_box_width_mm)
