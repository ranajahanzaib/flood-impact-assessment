import numpy as np
import pytest
import torch

from ml.adapters.baseline import BaselineWaterAdapter
from ml.adapters.clay import ClayAdapter
from ml.adapters.prithvi import PrithviAdapter
from ml.evaluation.metrics import compute_segmentation_metrics
from ml.inference.tiled import run_tiled_inference
from ml.models.base import get_compute_device
from ml.training.trainer import DiceBCELoss


def test_device_selection():
    device = get_compute_device()
    assert isinstance(device, torch.device)
    assert device.type in ["cuda", "mps", "cpu"]

def test_baseline_adapter_contract():
    adapter = BaselineWaterAdapter()
    meta = adapter.get_metadata()
    assert meta["model_id"] == "baseline-radar-optical-v1"
    assert "sentinel-1" in meta["supported_sensors"]

    # Test S1 input
    s1_data = np.full((2, 32, 32), -10.0, dtype=np.float32)
    s1_data[0, 10:20, 10:20] = -22.0  # VV water
    s1_data[1, 10:20, 10:20] = -26.0  # VH water

    prob, mask = adapter.predict(s1_data, sensor="sentinel-1", bands=["VV", "VH"])
    assert prob.shape == (32, 32)
    assert mask.shape == (32, 32)
    assert np.all(mask[10:20, 10:20] == True)
    assert np.all(mask[0:5, 0:5] == False)

def test_prithvi_adapter_contract():
    adapter = PrithviAdapter()
    meta = adapter.get_metadata()
    assert "Prithvi-EO-2.0-300M" in meta["model_id"]
    assert meta["resolution_m"] == 30.0

    # Test 6-band optical input
    optical_data = np.full((6, 32, 32), 1000.0, dtype=np.float32)
    prob, mask = adapter.predict(
        optical_data,
        sensor="sentinel-2",
        bands=["B02", "B03", "B04", "B8A", "B11", "B12"]
    )
    assert prob.shape == (32, 32)
    assert mask.shape == (32, 32)
    assert prob.dtype == np.float32

    # Incompatible sensor must raise ValueError
    with pytest.raises(ValueError, match="Prithvi-EO-2.0 expects optical"):
        adapter.predict(optical_data, sensor="sentinel-1", bands=["VV", "VH"])

def test_clay_adapter_contract():
    adapter = ClayAdapter()
    meta = adapter.get_metadata()
    assert meta["model_id"] == "made-with-clay/Clay"

    data = np.random.randn(10, 32, 32).astype(np.float32)
    prob, mask = adapter.predict(data, sensor="multisensor", bands=[f"b{i}" for i in range(10)])
    assert prob.shape == (32, 32)
    assert mask.shape == (32, 32)

def test_segmentation_metrics():
    # Ground truth: 10x10 with 4 positive pixels
    target = np.zeros((10, 10), dtype=bool)
    target[2:4, 2:4] = True  # 4 pixels

    # Prediction: 3 true positives, 1 false positive, 1 false negative
    pred = np.zeros((10, 10), dtype=bool)
    pred[2:4, 2:3] = True  # 2 TP
    pred[2, 3] = True      # 1 TP (total 3 TP)
    pred[5, 5] = True      # 1 FP

    # Probabilities
    probs = pred.astype(float) * 0.9 + (~pred).astype(float) * 0.1

    metrics = compute_segmentation_metrics(pred, target, pred_prob=probs)
    # TP=3, FP=1, FN=1 -> IoU = 3 / (3+1+1) = 3/5 = 0.6
    assert pytest.approx(metrics["iou"], rel=1e-3) == 0.6
    # Dice = 2*3 / (2*3 + 1 + 1) = 6/8 = 0.75
    assert pytest.approx(metrics["dice"], rel=1e-3) == 0.75
    assert pytest.approx(metrics["precision"], rel=1e-3) == 0.75
    assert pytest.approx(metrics["recall"], rel=1e-3) == 0.75
    assert "brier_score" in metrics
    assert "expected_calibration_error" in metrics

def test_dice_bce_loss():
    loss_fn = DiceBCELoss()
    logits = torch.randn(2, 1, 16, 16, requires_grad=True)
    targets = torch.randint(0, 2, (2, 1, 16, 16)).float()

    loss = loss_fn(logits, targets)
    assert loss.item() > 0.0
    loss.backward()
    assert logits.grad is not None

def test_tiled_inference():
    adapter = BaselineWaterAdapter()
    large_data = np.full((2, 600, 600), -8.0, dtype=np.float32)
    large_data[0, 100:200, 100:200] = -22.0

    prob, mask = run_tiled_inference(
        adapter=adapter,
        raster_data=large_data,
        sensor="sentinel-1",
        bands=["VV", "VH"],
        tile_size=256,
        overlap=32
    )
    assert prob.shape == (600, 600)
    assert mask.shape == (600, 600)
    assert np.all(mask[120:180, 120:180] == True)
    assert np.all(mask[0:50, 0:50] == False)
