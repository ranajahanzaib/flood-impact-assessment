import numpy as np


def calculate_temporal_persistence(
    observation_masks: list[np.ndarray],
    observation_valid_masks: list[np.ndarray],
    observation_timestamps: list[str]
) -> dict[str, np.ndarray]:
    """
    Measures temporal inundation persistence across multi-temporal flood observations.
    
    Returns dict containing:
        - valid_observation_count: int array
        - flood_observation_count: int array
        - persistence_ratio: float array in [0, 1]
        - observation_gap_flag: boolean array
    """
    if not observation_masks:
        raise ValueError("At least one observation mask is required")

    height, width = observation_masks[0].shape
    valid_count = np.zeros((height, width), dtype=np.int32)
    flood_count = np.zeros((height, width), dtype=np.int32)

    for mask, valid in zip(observation_masks, observation_valid_masks):
        valid_count += valid.astype(np.int32)
        flood_count += (mask & valid).astype(np.int32)

    # Persistence ratio: fraction of valid observations that were inundated
    persistence_ratio = np.zeros((height, width), dtype=np.float32)
    has_valid = valid_count > 0
    persistence_ratio[has_valid] = (
        flood_count[has_valid].astype(np.float32) / valid_count[has_valid].astype(np.float32)
    )

    # Observation gap: total observations available vs valid observations for this pixel
    total_obs = len(observation_masks)
    # If more than half the observations were missing or obscured
    gap_flag = (total_obs - valid_count) > (total_obs // 2)

    return {
        "valid_count": valid_count,
        "flood_count": flood_count,
        "persistence_ratio": persistence_ratio,
        "observation_gap_flag": gap_flag
    }
