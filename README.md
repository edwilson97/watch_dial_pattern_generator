# Watch Dial Pattern Generator v4

A mathematical grayscale height-map generator for watch dials. Supports a Tkinter desktop GUI and CLI, 23 pattern families, pattern-specific GUI settings, and 8/16-bit PNG plus JSON metadata exports. No artificial lighting is applied.

## Install and run (macOS)

Use Python 3.10+ with Tkinter enabled. From the extracted folder:

```bash
python3 -m pip install -r requirements.txt
python3 dial_patterns.py
```

If `import tkinter` fails, install a Python distribution with Tcl/Tk support (for example the official python.org macOS installer). CLI mode does not require an active display, though Pillow's ImageTk import still requires Tkinter to be installed.

## CLI

```bash
python3 dial_patterns.py --cli --pattern rosette --pitch-mm 0.75 --grooves 24 --amplitude 0.4 --pixels 2048 --output rosette.png
python3 dial_patterns.py --cli --pattern tapisserie --pitch-mm 0.75 --groove-width-mm 0.30 --bevel-width-mm 0.08 --output tapisserie.png
python3 dial_patterns.py --cli --pattern honeycomb --pitch-mm 0.8 --output honeycomb.png
python3 dial_patterns.py --help
```

New patterns: `graindorge`, `flamme`, `panier`, `escargot`, `moire`, `chevron`, `rosette`, `sectorrings`, `honeycomb`, `perlage`, `diamondlattice`, `isometriccubes`, `fanscallop`, `asanoha`. Existing nine remain unchanged.

New controls include `--amplitude`, `--secondary-pitch-mm`, `--angle-deg`, and `--segments`. The GUI shows only fields relevant to the chosen pattern and includes a scrollable settings area.

## Interpretation and limitations

- **White = highest surface; black = deepest recess.** Exported 16-bit PNG contains uint16 grayscale values. The 8-bit PNG is for easier software compatibility.
- Target depth is **metadata**, not calibrated material removal. Test and calibrate laser settings before engraving a dial.
- Newly added patterns are **mathematical, stylized interpretations**, not exact reconstructions of historical engine-turning tooling or authenticated artisanal patterns.
- The application exports **raster height maps, not CNC G-code**.
- GUI display has not been visually validated on macOS. Automated render and export tests are included.

## Tests

```bash
python3 test_patterns.py
```

This tests all 23 generators and PNG exports and creates `pattern_catalog.png`.

## Full test suite (including real Tkinter GUI interaction)

The test runner exercises all 23 mathematical pattern renderers and GUI workflows.
It opens a real Tk window, selects every pattern, verifies visible parameter controls,
updates a preview, invokes the GUI export button, and verifies 8/16-bit PNG and JSON output.
Native save dialogs and message boxes are mocked to make tests deterministic.

On macOS with an active desktop session:

```bash
python3 run_tests.py
```

On headless Linux (requires Xvfb):

```bash
xvfb-run -a python3 run_tests.py
```

The GUI test requires a working Tkinter installation and graphical display (or Xvfb).
It is not a native macOS UI rendering test.

## v4.2.5 — Brick and Reset

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

Use `python3 run_tests.py` to run the expanded regression and GUI test suite.
Grayscale denotes relative height, not a calibrated laser-removal depth.

## v4.2.4 — Fish Scales relief update

- Replaced the old arc-ridge Fish Scales generator with true relief geometry.
- Added three selectable Fish Scales styles: engraved, faceted, and rounded.
- Added GUI/CLI support and regression tests for the new Fish Scales relief styles.

## v4.2.3 — Asanoha multiple relief styles

- Added three selectable Asanoha styles: engraved, faceted, and rounded.
- Added GUI and CLI support for choosing the Asanoha style.
- Added regression tests verifying the styles remain distinct and that relief styles produce meaningful mid-tone depth variation.

## v4.2.2 — Asanoha relief update

- Changed Asanoha from a line-engraving-like pattern to a true faceted relief height map with sculpted surfaces between the grooves.
- Retained controllable line width while adding meaningful Z variation across the non-groove cells.
- Added regression tests to confirm the relief contains substantial mid-tone height variation beyond the groove network.

## v4.2.1 — corrected geometric families

- **Asanoha:** constructed from repeated hexagonal hemp-leaf line segments, including six radial arms, diagonal leaf ribs and perimeter connections. The `--line-width-mm` argument controls actual recessed stroke width.
- **Isometric Cubes:** three rhombus faces tessellate a hexagonal cell. They occupy three distinct height terraces (no directional lighting). `--cube-gap-mm` controls recessed boundaries; `--cube-step-fraction` controls physical relative-height differences.
- Both share a regular triangular tiling only; they no longer share the same synthetic wave-form algorithm.
- New tests: `test_distinct_lattices.py` plus additional GUI field visibility checks.

Examples:

```sh
python3 dial_patterns.py --cli --pattern asanoha --pitch-mm .8 --line-width-mm .055 --output asanoha.png
python3 dial_patterns.py --cli --pattern isometriccubes --pitch-mm .8 --cube-gap-mm .04 --cube-step-fraction .28 --output cubes.png
```

Note: The stepped cube surfaces are actual height terraces; the resulting physical relief will not appear identical to a conventionally shaded 3D cube graphic under all viewing conditions.

## v4.2: refined pattern geometry

The v4.2 release retains all 23 patterns and adds pattern-specific parameters:

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

Run the expanded suite (including GUI interaction tests): `python3 run_tests.py` (on headless Linux: `xvfb-run -a python3 run_tests.py`).
