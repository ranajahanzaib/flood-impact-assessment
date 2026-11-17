
import numpy as np

# Classification codes
CLASS_NO_WATER = 0
CLASS_PERMANENT_WATER = 1
CLASS_NEW_INUNDATION = 2
CLASS_RECEDED_WATER = 3
CLASS_NODATA = 255

def separate_permanent_and_flood_water(
    pre_water_mask: np.ndarray,
    pre_valid_mask: np.ndarray,
    during_water_mask: np.ndarray,
    during_valid_mask: np.ndarray,
    post_water_mask: np.ndarray | None = None,
    post_valid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Separates pre-existing baseline water from newly inundated land and receded areas.
    
    Returns:
        (classification_raster, newly_inundated_mask):
        classification_raster: uint8 array with CLASS_* values.
        newly_inundated_mask: boolean array (True where land was newly flooded during the event).
    """
    height, width = during_water_mask.shape
    classification = np.full((height, width), CLASS_NO_WATER, dtype=np.uint8)

    # 1. Any pixel invalid in during-event imagery is marked NODATA
    classification[~during_valid_mask] = CLASS_NODATA

    # 2. Permanent / pre-existing water:
    # A pixel observed as water in the pre-event observation (and valid)
    pre_water = pre_water_mask & pre_valid_mask
    classification[pre_water & during_valid_mask] = CLASS_PERMANENT_WATER

    # 3. Newly inundated land:
    # Water observed during the event, but NOT pre-existing water
    # Crucially: if pre-event was invalid/cloudy, it is marked as candidate new inundation with uncertainty flag
    during_water = during_water_mask & during_valid_mask
    new_inundation = during_water & ~pre_water
    classification[new_inundation] = CLASS_NEW_INUNDATION

    # 4. Receded water:
    # Observed newly flooded during event, but valid dry land after event
    if post_water_mask is not None and post_valid_mask is not None:
        recession = new_inundation & post_valid_mask & (~post_water_mask)
        classification[recession] = CLASS_RECEDED_WATER

    return classification, new_inundation
