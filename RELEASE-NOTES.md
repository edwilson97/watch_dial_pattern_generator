# Release Notes

## Unreleased

- Added Windows executable signing through Azure Artifact Signing with GitHub OIDC, SHA-256, and timestamp verification before packaging. Requires the Entra application and GitHub environment setup described in the README.

## v1.1.0 — Dimples and GUI improvements

- Show a busy cursor while the 3D Viewer starts, restoring it when the viewer appears or startup fails.
- Moved release history from the README to `RELEASE-NOTES.md`.
- Added mouse-wheel and trackpad scrolling to the pattern parameter panel, including scrolling over labels, entries, and dropdowns.
- Scoped Asanoha line-width and Isometric Cubes gap validation to their respective patterns, allowing small dimple pitches. Set dimple diameter equal to pitch for touching edges.
- Added **Dimples (golf ball texture)**: staggered round recesses with adjustable diameter, spacing, rotation, offset, and target depth. Available in the GUI, CLI, live 3D inspection, and PNG/settings exports.

## v1.0.0 — First official release

- Includes all 24 patterns, desktop and command-line interfaces, live 3D inspection, and PNG plus settings exports.
- Adds plain-language hover tips for every main GUI button, input field, dropdown, and checkbox.
- Displays version 1.0.0 in the GUI title. Run `python dial_patterns.py --version` to check the version from the command line.

## v0.2 — Relief geometry and enlarged inspection

- Basketweave and Panier ribbons now descend continuously to common recessed cell boundaries, replacing height jumps at crossovers. This deliberately changes their appearance.
- Fish Scales uses cells bounded by consecutive staggered arcs rather than resetting at horizontal rows. All three styles share recessed arc boundaries. Fan/Scallop uses the same continuous cell layout with internal radial ribs.
- Honeycomb now has flat hexagonal plateaus, recessed joints and linear bevels. Joint width is 5% of pitch; bevel width on each side is `(0.10 + 0.30 * softness) * pitch`. It replaces the old circular mounds.
- Perlage now approximates overlapping shallow circular grain strokes with feathered rims. Ring spacing (`--perlage-ring-pitch-mm`, default 0.1 mm) and overlap (`--perlage-overlap`, default 0.5, range 0–0.5) are independent controls. It is a stylized relief approximation of graining, not a simulation of abrasive tooling. Heights remain within 0.78–1, so relief uses at most 22% of the target depth range; output is intentionally not contrast-normalized.
- **Inspect enlarged / 3D** opens an interactive PyVista window linked to the current full output-resolution map. Drag to orbit/tilt, Shift-drag to pan, and use the wheel to zoom (right-drag also zooms). Crop controls update on release; depth exaggeration updates continuously. Camera position is preserved when changing crop, detail, coloring, or exaggeration. At 1× exaggeration, X/Y and design Z share millimeter units. Crop centers clamp at image edges. Open viewers update automatically about 350 ms after you pause editing a pattern parameter, including pattern selection, inversion, circular masking, size, resolution, and target depth. Full-resolution rendering runs in the background; large maps can take longer. Incomplete or invalid entries retain the last valid surface and show a status message in the generator. Older render results are discarded when newer edits arrive. Rotation, pan, zoom, projection, coloring, mesh detail, and depth exaggeration are preserved; crop controls clamp to the new dial size when needed.
- Mesh detail offers Fast (201), Balanced (401), and Fine (801) samples per side, capped by the source crop resolution. Samples retain their actual pixel-center positions and depth; no smoothing is applied to the geometry. Use a small crop or press **G** for the full-resolution nearest-neighbor grayscale height map to inspect narrow grooves. Press **G** again to restore the 3D camera.
- Camera shortcuts: **T** top, **F** front, **I** isometric, **R** fit/reset framing, **P** perspective/orthographic. **C** toggles depth coloring. **S** opens a save dialog for a labeled inspection screenshot. These screenshots never change the 16-bit engraving PNG. Regenerate older exported maps to adopt the corrected geometry.

## v0.1.5 — Brick and Reset

The Brick / Running Bond pattern uses exact millimeter-defined repeating rectangular
geometry, with alternating staggered courses. Available styles: engraved (flat
brick interiors with recessed joints), faceted (flat plateaus and linear bevels),
and rounded (smooth pillow relief). The Brick-specific GUI fields are shown only
when Brick is selected.

The **Reset to defaults** button restores the startup pattern, every entry and
selection (including hidden pattern-specific values), the invert/circular checkboxes,
and the preview. It does not delete exported files.

Example CLI:

```bash
python3 dial_patterns.py --cli --pattern brick --brick-width-mm 1.2 \
  --brick-height-mm 0.6 --brick-joint-mm 0.1 --brick-bevel-mm 0.08 \
  --brick-row-offset 0.5 --brick-style faceted --depth-mm 0.15 \
  --output brick_faceted.png
```

Use `python3 -m tests.run_tests` to run the expanded regression and GUI test suite.
Grayscale denotes relative height, not a calibrated laser-removal depth.

## v0.1.4 — Fish Scales relief update

- Replaced the old arc-ridge Fish Scales generator with true relief geometry.
- Added three selectable Fish Scales styles: engraved, faceted, and rounded.
- Added GUI/CLI support and regression tests for the new Fish Scales relief styles.

## v0.1.3 — Asanoha multiple relief styles

- Added three selectable Asanoha styles: engraved, faceted, and rounded.
- Added GUI and CLI support for choosing the Asanoha style.
- Added regression tests verifying the styles remain distinct and that relief styles produce meaningful mid-tone depth variation.

## v0.1.2 — Asanoha relief update

- Changed Asanoha from a line-engraving-like pattern to a true faceted relief height map with sculpted surfaces between the grooves.
- Retained controllable line width while adding meaningful Z variation across the non-groove cells.
- Added regression tests to confirm the relief contains substantial mid-tone height variation beyond the groove network.

## v0.1.1 — corrected geometric families

- **Asanoha:** constructed from repeated hexagonal hemp-leaf line segments, including six radial arms, diagonal leaf ribs and perimeter connections. The `--line-width-mm` argument controls actual recessed stroke width.
- **Isometric Cubes:** three rhombus faces tessellate a hexagonal cell. They occupy three distinct height terraces (no directional lighting). `--cube-gap-mm` controls recessed boundaries; `--cube-step-fraction` controls physical relative-height differences.
- Both share a regular triangular tiling only; they no longer share the same synthetic wave-form algorithm.
- New tests: `tests/test_distinct_lattices.py` plus additional GUI field visibility checks.

Examples:

```sh
python3 dial_patterns.py --cli --pattern asanoha --pitch-mm .8 --line-width-mm .055 --output asanoha.png
python3 dial_patterns.py --cli --pattern isometriccubes --pitch-mm .8 --cube-gap-mm .04 --cube-step-fraction .28 --output cubes.png
```

Note: The stepped cube surfaces are actual height terraces; the resulting physical relief will not appear identical to a conventionally shaded 3D cube graphic under all viewing conditions.

## v0.1: refined pattern geometry

The v0.1 release retains all 24 patterns and adds pattern-specific parameters:

- **Hobnail:** `--top-width-mm` makes a mathematically flat truncated-pyramid apex (0 = pointed).
- **Wave:** `--wave-meander-mm` controls lateral waviness independently from `--ridge-height-fraction` (0 = flat, 1 = full grayscale range).
- **Annular Wave:** `--ridge-height-fraction` adjusts concentric ridge height.
- **Grain d'Orge:** `--grain-aspect` adjusts grain elongation; `--amplitude` controls centerline curvature.
- **Flamme:** `--flame-taper` progressively narrows flame ridges outward.
- **Panier:** `--ribbon-curvature` independently controls woven ribbon bowing.
- **Rosette:** `--rosette-harmonics` mixes the primary petal frequency with its second harmonic.

All seven controls appear only when their pattern is selected in the GUI, are available from CLI, and are stored in the JSON metadata. These are mathematical stylizations, not guaranteed reproductions of historical engine-turning cutter trajectories. `depth_mm` remains target-depth metadata rather than a laser or CNC calibration.

Example:

```bash
python3 dial_patterns.py --cli --pattern hobnail --pitch-mm 0.75 --top-width-mm 0.18 --output truncated_hobnail.png
python3 dial_patterns.py --cli --pattern wave --pitch-mm 0.75 --wave-meander-mm 0.22 --ridge-height-fraction 0.6 --output wave.png
```

Run the expanded suite (including GUI interaction tests): `python3 -m tests.run_tests` (on headless Linux: `xvfb-run -a python3 -m tests.run_tests`).
