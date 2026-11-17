import numpy as np


def compute_segmentation_metrics(
    pred_mask: np.ndarray,
    target_mask: np.ndarray,
    pred_prob: np.ndarray = None,
    ignore_mask: np.ndarray = None
) -> dict[str, float]:
    """
    Computes rigorous segmentation performance and calibration metrics.
    
    Args:
        pred_mask: boolean or uint8 binary prediction
        target_mask: boolean or uint8 binary ground truth
        pred_prob: optional float array in [0, 1] for Brier and ECE calibration
        ignore_mask: optional boolean mask of pixels to exclude (e.g. clouds, no-data, -1 values)
    """
    p = pred_mask.astype(bool)
    t = target_mask.astype(bool)

    if ignore_mask is not None:
        valid = ~ignore_mask.astype(bool)
        p = p[valid]
        t = t[valid]
        if pred_prob is not None:
            pred_prob = pred_prob[valid]

    # Confusion matrix elements
    tp = np.sum(p & t)
    fp = np.sum(p & ~t)
    fn = np.sum(~p & t)
    tn = np.sum(~p & ~t)

    epsilon = 1e-7
    iou = float(tp / (tp + fp + fn + epsilon))
    dice = float((2.0 * tp) / (2.0 * tp + fp + fn + epsilon))
    precision = float(tp / (tp + fp + epsilon))
    recall = float(tp / (tp + fn + epsilon))
    specificity = float(tn / (tn + fp + epsilon))

    metrics = {
        "iou": round(iou, 4),
        "dice": round(dice, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
    }

    # Probability calibration metrics
    if pred_prob is not None:
        prob = np.clip(pred_prob.flatten(), 0.0, 1.0)
        target = t.flatten().astype(float)

        # Brier score: MSE of predicted probabilities against ground truth
        brier = float(np.mean((prob - target) ** 2))
        metrics["brier_score"] = round(brier, 4)

        # Expected Calibration Error (ECE) with 10 bins
        n_bins = 10
        bin_limits = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        n_total = len(prob)

        for i in range(n_bins):
            bin_mask = (prob >= bin_limits[i]) & (prob < bin_limits[i + 1])
            if np.any(bin_mask):
                bin_acc = np.mean(target[bin_mask])
                bin_conf = np.mean(prob[bin_mask])
                ece += (np.sum(bin_mask) / n_total) * np.abs(bin_acc - bin_conf)

        metrics["expected_calibration_error"] = round(float(ece), 4)

    return metrics
