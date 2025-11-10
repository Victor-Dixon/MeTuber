# CartoonStylePro Migration Notes

This document captures the preset updates introduced by `CartoonStylePro` and outlines how to recover the legacy appearance when needed.

## Summary

- The unified presets now enforce tuned defaults (bilateral smoothing, quantization, edge detection). These differ from the implicit values that older scripts relied on.
- Legacy automation that invoked the historical `Cartoon` or `CartoonStyle` classes without overriding parameters can observe visible changes (sharper edges, additional downscaling).
- To keep the classic look, explicitly override the parameters called out below or use the provided back-compat wrappers (`styles.artistic.cartoon.Cartoon` and `styles.artistic.cartoon.CartoonStyle`).

## Preset Deltas

| Preset | Legacy expectation | Current default | Restore legacy look |
| --- | --- | --- | --- |
| `Detailed` | No explicit downscale, adaptive edge thresholding | `downscale_factor=0.5`, `edge_method="Canny"`, `edge_dilate=1` | Pass `downscale_factor=1.0`, `edge_method="Adaptive"`, `adaptive_block=9`, `adaptive_C=2`, `edge_dilate=0` |
| `Fast` | Adaptive edges with optional downscale overrides supplied by callers | Unchanged logic; now hard-coded `downscale_factor=0.3`, `edge_method="Adaptive"` | Override `downscale_factor` and `edge_method` as required |
| `Advanced` | Callers chose edge operator; dilation disabled unless sharpening enabled | `edge_method="Canny"`, `edge_dilate=2`, `edge_erode=1` | Explicitly set `edge_method="Adaptive"` (or previous choice), `edge_dilate=0`, `edge_erode=0` |
| `Anime` | Adaptive threshold with lighter smoothing | Adds guard rails: `downscale_factor=0.25` min, forces adaptive edges | Supply custom `downscale_factor` and `edge_method` if you relied on different values |
| `Whole` | Previously matched whole-image pipeline without extra edge sharpening | `downscale_factor=0.35`, `edge_method="Canny"`, `edge_dilate=1` | Pass `edge_method="Adaptive"`, `downscale_factor=1.0`, `edge_dilate=0` |

> **Tip:** These presets can be combined with custom overrides. Only the parameters you specify are substituted; all others fall back to the preset defaults.

## Compatibility Shims

- `Cartoon` approximates the original “Cartoon (Detailed)” behavior. It forwards to `CartoonStylePro` but supplies the historical parameters (`quant_method="Uniform"`, original bilateral settings, adaptive edges). Use this class if you were importing `Cartoon` previously and prefer the old defaults.
- `CartoonStyle` serves the same purpose for the “Cartoon (Fast)” widget, preserving the former parameter layout and value ranges.

## Migration Recommendations

1. **Audit scripts** that instantiate `CartoonStylePro` (or call through `StyleManager`) without custom parameters. Decide whether the new defaults are acceptable.
2. **Pin explicit overrides** when you require legacy visuals. Example:
   ```python
   pro = CartoonStylePro()
   legacy_frame = pro.apply(
       frame,
       {
           "preset": "Detailed",
           "downscale_factor": 1.0,
           "edge_method": "Adaptive",
           "adaptive_block": 9,
           "adaptive_C": 2,
           "edge_dilate": 0,
       },
   )
   ```
3. **Adopt the wrappers** (`Cartoon`, `CartoonStyle`) for minimal code changes in automation or plugins that still expect the earlier signatures.
4. **Document project-specific overrides** so downstream consumers know whether to rely on the new sharper defaults or to keep parity with the legacy appearance.

## Tracking Future Adjustments

- Record additional preset tweaks in this file to keep downstream teams informed.
- When changing defaults, include rationale (quality, performance, bug fix) and the recipe to emulate the previous behavior.
- Consider adding automated regression snapshots for key presets to flag visual drifts early.


