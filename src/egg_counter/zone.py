"""Zone containment logic for egg detection region."""

from typing import Union


def is_in_zone(
    box_xyxy: Union[list, tuple],
    zone_rect: dict,
) -> bool:
    """Check if the center of a bounding box is within the zone rectangle.

    Args:
        box_xyxy: Bounding box in [x1, y1, x2, y2] format (ultralytics xyxy).
        zone_rect: Zone rectangle dict with keys x1, y1, x2, y2.

    Returns:
        True if the bbox center is within the zone (inclusive boundaries).
    """
    cx = (box_xyxy[0] + box_xyxy[2]) / 2
    cy = (box_xyxy[1] + box_xyxy[3]) / 2

    return (
        zone_rect["x1"] <= cx <= zone_rect["x2"]
        and zone_rect["y1"] <= cy <= zone_rect["y2"]
    )
