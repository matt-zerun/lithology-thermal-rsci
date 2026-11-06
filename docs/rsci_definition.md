# Canonical Response-Surface Consistency Index

RSCI is a post-hoc relative geometric diagnostic. It is not a mechanistic
validation score, a physical-validity score, an uncertainty measure, or an
accuracy-tuning criterion.

The canonical v1.1.0 definition is:

```text
RSCI(0–1) = 0.20 S_bounds
          + 0.25 S_smooth
          + 0.20 S_extrema
          + 0.20 S_gradient
          + 0.15 S_fragmentation

RSCI = 100 × RSCI(0–1)
```

The five components are boundedness, smoothness, local extrema, gradient
variation, and gradient-sign fragmentation. The implementation retains the
historical internal key `gradient_stability_score`; the publication term is
**gradient variation**.

## Numerical settings

| Setting | Canonical value |
|---|---:|
| Response grid | 80 × 80 nodes |
| Evaluation mask | State-level convex hull |
| Admissible λ interval | 0–5 W m⁻¹ K⁻¹ |
| Gaussian smoothing | σ = 1 grid cell |
| Extrema neighbourhood | 5 × 5 cells |
| Fragmentation tolerance | 5% of the 75th percentile of absolute gradient magnitude |
| Relative-component normalisation | Inverse min–max within lithology across 16 candidates |
| Output scale | 0–100 |

Boundedness is scored on an absolute scale. Smoothness, extrema, gradient
variation, and fragmentation are relative to the complete candidate set of the
corresponding lithology. In the final analysis, boundedness equalled 1 for
all 64 surfaces and therefore did not distinguish models.

High RSCI indicates geometric regularity under this framework. Oversmoothing
can produce a high score while reducing grouped predictive performance; clay
provides the clearest example. RSCI must therefore be interpreted
together with grouped validation, occupancy, cross-family agreement, and
response profiles.

## Coordinate convention and sensitivity

The production implementation calculates derivative-based diagnostics using
the physical coordinate spacing: water content in percent and measured wet
bulk density in Mg m⁻³. A coordinate-scaling sensitivity audit compared this
convention with water content expressed as a fraction and with both axes scaled
to 0–1 within lithology. Within-lithology ranks changed moderately, while the
predictive and interpretive role assignments and the main scientific
conclusions remained unchanged. RSCI is therefore a relative geometric
diagnostic defined under the stated coordinate convention, not a
scale-invariant surface-quality measure.
