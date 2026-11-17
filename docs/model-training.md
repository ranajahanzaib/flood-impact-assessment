# Model Training & Evaluation Guide

## 1. Foundation Model Adapters

The platform provides a pluggable `ModelAdapter` interface:

1. **Baseline Physical Adapter**:
   - Immediate out-of-the-box execution with zero weight downloads.
   - Dual-polarization Sentinel-1 SAR backscatter thresholding + Sentinel-2 NDWI/MNDWI + DEM slope suppression.
2. **Prithvi-EO-2.0-300M Flood Adapter**:
   - Adapts `ibm-nasa-geospatial/Prithvi-EO-2.0-300M` 3D ViT embeddings.
   - Input: 6 HLS/Sentinel-2 bands (`B02`, `B03`, `B04`, `B8A`, `B11`, `B12`).
   - Downstream convolutional segmentation head (`FloodSegmentationHead`) trained with combined Dice + BCE loss.
3. **Clay Adapter**:
   - Adapts `made-with-clay/Clay` tokenized multi-sensor embeddings for joint radar-optical feature fusion.

---

## 2. Training Workflow

Run the reproducible training verification:

```bash
make train
```

The trainer implements:

- **Combined Loss Function**:
  $$\mathcal{L} = \frac{1}{2}\mathcal{L}_{\text{BCE}} + \frac{1}{2}(1 - \text{Dice})$$
- **Optimization**: AdamW with weight decay $1\times 10^{-4}$ and cosine learning rate scheduling.
- **Validation Checkpointing**: Evaluates IoU after each epoch and saves `best_model.pt`.

---

## 3. Evaluation Metrics

Run evaluation:

```bash
make evaluate
```

The evaluation suite computes:

- **Intersection over Union (IoU / Jaccard)**: $\frac{TP}{TP + FP + FN}$
- **Dice / F1-Score**: $\frac{2TP}{2TP + FP + FN}$
- **Precision, Recall, Specificity**
- **Brier Score**: $\frac{1}{N}\sum (p_i - y_i)^2$
- **Expected Calibration Error (ECE)** across 10 confidence bins to verify that prediction probabilities correspond to empirical accuracy.
