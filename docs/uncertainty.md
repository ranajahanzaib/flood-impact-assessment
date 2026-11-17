# Uncertainty Assessment & Manual Verification

## 1. Uncertainty Signals

The platform rejects binary black-box claims and explicitly computes confidence and limitation signals:

1. **Model Prediction Entropy**:
   $$H(p) = -p \log_2(p) - (1-p) \log_2(1-p)$$
   Measures prediction hesitation, peaking at $p = 0.5$.
2. **Sensor Disagreement**:
   Computed wherever overlapping Sentinel-1 radar and Sentinel-2 optical scenes disagree (e.g. radar detects specular water backscatter, but optical reflectance indicates dry land). Disagreements are mapped rather than suppressed.
3. **Observation Gaps**:
   Identifies geographic regions where cloudy conditions or satellite orbit geometry omitted critical flood stages.
4. **Cloud & Shadow Contamination**:
   Identifies optical pixels obscured by clouds or cloud shadows, assigning maximum uncertainty ($1.0$).

---

## 2. Human-in-the-Loop Verification

High-uncertainty contiguous regions ($\ge 16$ pixels, uncertainty $\ge 0.65$) are polygonized into the **Manual Verification Queue**.

Analysts can:

1. Click the flagged region in the workspace.
2. Inspect underlying radar and optical sensor values.
3. Record an audited decision:
   - `confirmed_flood`
   - `confirmed_dry`
   - `dismissed`
4. Add analyst rationale notes. The decision is recorded without destructively overwriting original raw model evidence.
