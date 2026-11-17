# Infrastructure Impact Analysis

## 1. Principles of Scientific Exposure Assessment

A geographic overlay between an inundation polygon and an infrastructure feature establishes **exposure** and geometric intersection; it does not, by itself, prove structural destruction, total financial loss, or impassability.

The platform uses rigorous terminology:

- **Potentially affected buildings** or **buildings intersecting observed inundation**.
- **Inundated road segments** (specifying affected length vs total segment length).

---

## 2. Building Footprint Analysis

For each building footprint polygon:

1. Reprojected to an equal-area metric coordinate system (`EPSG:6933`).
2. Footprint area ($m^2$) is calculated.
3. Intersection geometry with the unified candidate flood polygon is computed:
   $$\text{Intersection } \% = \frac{\text{Intersect Area}}{\text{Total Footprint Area}} \times 100$$
4. Buildings with $> 5\%$ intersection are categorized as potentially affected.
5. Buildings intersecting high-uncertainty regions are flagged as `is_uncertain: true`.

---

## 3. Road Network Analysis

1. Road centerline LineStrings are reprojected to equal-area metric coordinates.
2. Intersecting line segments are split at the inundation polygon boundaries.
3. The platform calculates:
   - Total road length ($m$, $km$)
   - Inundated road length ($m$, $km$)
   - Percentage of road network inundated
   - Affected segment count
   - Prevents classifying a 10 km highway as flooded when only a 40-meter bridge approach is submerged.
