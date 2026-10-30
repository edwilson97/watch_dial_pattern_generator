# Watch Dial Pattern Generator

Current version: **1.2.0**. See [release notes](RELEASE-NOTES.md) for changes.

A mathematical grayscale height-map generator for watch dials. Supports a Tkinter desktop GUI and CLI, 27 pattern families, pattern-specific GUI settings, and 8/16-bit PNG plus JSON metadata exports. No artificial lighting is applied to engraving exports.

## Donate/Sponsor

If this app helps with your watchmaking projects, consider supporting its development with a monetary donation. Contributions help fund ongoing development and maintenance. ***Support is entirely optional***—the project remains free and open source. To donate, simply click the **Buy Me A Coffee** link below, or the **Sponsor** button above <a href="https://buymeacoffee.com/edwilson97" target="_blank" rel="noopener noreferrer"><img src="./images/SponsorButton.png" width="75" alt="Sponsor Button"></a>

[☕ Buy Me A Coffee](https://buymeacoffee.com/edwilson97) 

## License

Copyright (c) 2026 Bridge Watches LLC. Licensed under the [MIT License](LICENSE).

## Standalone Windows and macOS downloads

The [Build native apps workflow](https://github.com/edwilson97/watch_dial_pattern_generator/actions/workflows/build-native.yml)
packages the app with Python, Tkinter, NumPy, Pillow, PyVista, and VTK included.
Users do not need to install Python or run `pip`.

To create downloads, push this workflow to GitHub, then open **Actions → Build native
apps → Run workflow**. It also runs on pushes to `main`/`master` and
tags beginning with `v`. After a successful run, download the matching artifact
from the run's **Artifacts** section and extract it. Each artifact is the ZIP itself,
with no additional ZIP wrapper:

| Download | Platform | Launch |
| --- | --- | --- |
| `WatchDialPatternGenerator-windows-x64.zip` | 64-bit Windows | Extract the entire folder and open `WatchDialPatternGenerator.exe` inside it. Keep `_internal` beside the executable. |
| `WatchDialPatternGenerator-macos-arm64.zip` | Apple Silicon Mac, macOS 15 or newer | Extract and open `WatchDialPatternGenerator.app`. |
| `WatchDialPatternGenerator-macos-x64.zip` | Intel Mac, macOS 15 or newer | Extract and open `WatchDialPatternGenerator.app`. |

Artifacts are kept for 30 days. For permanent public downloads, a maintainer can
attach the ZIP files to a GitHub Release.

The apps launch without a terminal window. On macOS, CLI arguments can also be
passed directly to `WatchDialPatternGenerator.app/Contents/MacOS/WatchDialPatternGenerator`.
For a Windows CLI with terminal output, use the Python installation instructions below.

### Build locally

Build on the target OS and CPU architecture using Python 3.12 with Tkinter:

```bash
python -m pip install -r requirements-build.txt
python -m PyInstaller --clean --noconfirm WatchDialPatternGenerator.spec
python scripts/check_bundle.py
```

Windows output is in `dist/WatchDialPatternGenerator/`; macOS output is
`dist/WatchDialPatternGenerator.app`. Builds use a folder bundle because VTK includes
large native libraries. macOS archives use `ditto` to preserve the app's links and
permissions. The workflow records installed dependency versions in each download.

CI runs geometry and subprocess regression tests, then checks the actual packaged
app's Tk/Pillow initialization, VTK mesh construction, and 8/16-bit PNG plus JSON
exports from a temporary working directory. Interactive 3D rendering and native
save dialogs still need a manual check on each platform before distributing a release.

## Install and run (macOS)

Use Python 3.12 or 3.13 with Tkinter enabled and available VTK wheels. From the project folder:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python dial_patterns.py
```

If `import tkinter` fails, install a Python distribution with Tcl/Tk support (for example the official python.org macOS installer). CLI mode does not require an active display, though Pillow's ImageTk import still requires Tkinter to be installed.

After creating the environment, you can also launch directly with
`.venv/bin/python dial_patterns.py`. PyVista uses VTK for the interactive inspection window;
no Qt installation is needed. Inspection opens in its own process so the generator remains
responsive. Closing the generator also closes its inspection windows.

## Install and run (Windows)

Install **64-bit Python 3.12 or 3.13** from [python.org](https://www.python.org/downloads/windows/),
including Tcl/Tk support and the Python launcher (`py`). For installer details, see
[Python's Windows setup guide](https://docs.python.org/3.13/using/windows.html).
Download and extract this project, or clone the repository, then open PowerShell
in the project folder (the folder containing `dial_patterns.py` and `requirements.txt`).

Run these commands to create an isolated environment, install dependencies, and
start the desktop GUI:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe dial_patterns.py
```

If you installed Python 3.12, use `py -3.12` in the first command. If `py` is not
recognized, reopen your terminal after installing Python, or use the full path
to your Python 3.12/3.13 executable to create the environment.

On subsequent runs, open PowerShell in the project folder and run:

```powershell
.\.venv\Scripts\python.exe dial_patterns.py
```

These commands also work in Command Prompt. They invoke the environment's Python
directly, so no activation or PowerShell execution-policy change is required. If
you prefer activation, use `.\.venv\Scripts\Activate.ps1` in PowerShell or
`.venv\Scripts\activate.bat` in Command Prompt, then run `python dial_patterns.py`.
See [Python's virtual environment documentation](https://docs.python.org/3.13/library/venv.html)
for details.

To check Tkinter, run `.\.venv\Scripts\python.exe -m tkinter`; a small test window
should open. If it fails, modify or reinstall Python with Tcl/Tk support enabled
and recreate the environment. PyVista installs VTK for the **Inspect enlarged / 3D**
window through `requirements.txt`; no Qt installation is needed.

For CLI use, replace `python3` in the examples below with
`.\.venv\Scripts\python.exe`. For example:

```powershell
.\.venv\Scripts\python.exe dial_patterns.py --cli --pattern rosette --pitch-mm 0.75 --output rosette.png
```

## CLI

```bash
python3 dial_patterns.py --cli --pattern rosette --pitch-mm 0.75 --grooves 24 --amplitude 0.4 --pixels 2048 --output rosette.png
python3 dial_patterns.py --cli --pattern tapisserie --pitch-mm 0.75 --groove-width-mm 0.30 --bevel-width-mm 0.08 --output tapisserie.png
python3 dial_patterns.py --cli --pattern honeycomb --pitch-mm 0.8 --output honeycomb.png
python3 dial_patterns.py --cli --pattern ingenieur --pitch-mm 2.0 --ingenieur-count 3 --ingenieur-gap-mm 0.06 --ingenieur-feature-width-mm 0.10 --output ingenieur.png
python3 dial_patterns.py --help
```

To see all available options for the CLI, use the `-h` or `--help` command line parameter.

Available patterns: `hobnail`, `barleycorn`, `sunburst`, `basketweave`, `tapisserie`, `fishscales`, `flinque`, `wave`, `horizontalribbing`, `annularwave`, `graindorge`, `flamme`, `panier`, `escargot`, `moire`, `chevron`, `rosette`, `sectorrings`, `honeycomb`, `perlage`, `diamondlattice`, `isometriccubes`, `fanscallop`, `asanoha`, `brick`, `dimples`, and `ingenieur`.

[View the pattern catalog (PNG)](images/pattern_catalog.png) for a visual guide to all 27 patterns.

**Ribs & Posts** (CLI key: `ingenieur`) alternates squares of horizontal raised ribs with squares
of circular, flat-topped posts. The default is three ribs alternating with a 3×3 post
array. Pattern pitch defaults to 2 mm and sets one square's width; the full checkerboard repeats every
two squares. Adjust the feature count (1–12), square gap, rib width/post diameter,
rotation, and offset. Feature width must be less than `(pitch - gap) / count`.
Both motifs have short beveled edges and share the same relief height. Use Invert
to recess the motifs. This is an interpretation of the texture, not an exact replica.

The GUI shows only fields relevant to the chosen pattern and includes a scrollable settings area.

The GUI remembers edited pitch values per pattern until **Reset to defaults**.

The grayscale preview refreshes when you edit a parameter and move focus to another
field. Pattern, style, and checkbox changes refresh immediately. Invalid entries
keep the last valid preview visible and show an error in the status text.

The small preview uses a higher-resolution render and filtered reduction to avoid
false patterns and jagged lattice edges. The 3D viewer starts in **Mesh: Auto
(groove detail)**, which retains more samples across Asanoha and cube grooves.
It still uses the exported height-map samples. If the viewer reports too few
source pixels, increase **Output pixels / side** (try 4096 for a 28.5 mm dial);
if it reports too few mesh samples, select Auto or reduce the crop width.
For Asanoha, **engraved** leaves flat interiors between recessed lines, while
**faceted** and **rounded** add sculpted relief between them.

## Exclusion zones (experimental)

Open **Exclusion zones (0)…** to reserve flat areas for a logo, date window,
center hole footprint, or hour markers. Choose a rectangle or circle, enter its
dimensions and center, then **Add → Apply to dial**. To edit an existing zone,
select it, change its fields, and choose **Update selected → Apply to dial**.
Closing the editor discards changes that have not been applied. Remove a zone
with **Remove selected → Apply to dial**; **Reset to defaults** clears all zones.

Positions are in millimeters from dial center: positive X goes right and positive
Y goes up. Width is the diameter for circles; rectangle height is ignored for
circles. **Clearance** adds space around the footprint (with rounded corners on
rectangles). **Edge feather** blends back into the pattern outside the clearance,
leaving the entire reserved footprint flat. Set feather to zero for a sharp edge.
**Flat surface level** defaults to 1 (white / highest); it stays fixed when the
pattern is inverted. Pattern rotation and offset do not move the zones.

Multiple zones are supported; later zones take precedence in overlaps. Select a
zone and use **Move up** to draw it earlier (behind), or **Move down** to draw it
later (on top), then **Apply to dial**. The selection follows the moved zone.
Applied zones affect the grayscale preview, live 3D inspection, both PNG exports, and JSON
settings. These are flat height-map areas, not actual holes or a separate laser
exclusion mask. This first version clips relief at the boundary; it does not omit
whole motifs or bend the pattern around the zone.

![Original, sharp exclusions, and feathered exclusions](images/exclusion_zones_preview.png)

For the CLI, pass a JSON list of zone objects:

```bash
python3 dial_patterns.py --cli --pattern ingenieur --circular --exclusion-zones-file examples/exclusion_zones.json --output dial_with_zones.png
```

See [example zone settings](examples/exclusion_zones.json). Available fields are
`shape` (`rectangle` or `circle`), `x_mm`, `y_mm`, `width_mm`, `height_mm`,
`clearance_mm`, `feather_mm`, and `level`. The export JSON includes the normalized
list under `exclusion_zones`. Rebuild the comparison image with
`python3 scripts/render_exclusion_demo.py`.

## Interpretation and limitations

- **White = highest surface; black = deepest recess.** Exported 16-bit PNG contains uint16 grayscale values. The 8-bit PNG is for easier software compatibility.
- Target depth is **metadata**, not calibrated material removal. Test and calibrate laser settings before engraving a dial.
- Newly added patterns are **mathematical, stylized interpretations**, not exact reconstructions of historical engine-turning tooling or authenticated artisanal patterns.
- The application exports **raster height maps, not CNC G-code**.
- GUI display has not been visually validated on macOS. Automated render and export tests are included.

## Tests

```bash
python3 -m tests.test_patterns
```

This tests all 27 generators and PNG exports and creates `images/pattern_catalog.png`.

## Full test suite (including real Tkinter GUI interaction)

The test runner exercises all 27 mathematical pattern renderers and GUI workflows.
It opens a real Tk window, selects every pattern, verifies visible parameter controls,
updates a preview, invokes the GUI export button, and verifies 8/16-bit PNG and JSON output.
Native save dialogs and message boxes are mocked to make tests deterministic.

On macOS with an active desktop session:

```bash
python3 -m tests.run_tests
```

On headless Linux (requires Xvfb):

```bash
xvfb-run -a python3 -m tests.run_tests
```

The GUI test requires a working Tkinter installation and graphical display (or Xvfb).
It is not a native macOS UI rendering test.

## LightBurn 2.1 / 100 W JPT MOPA / F190 lens workflow

LightBurn 2.1 supports 16-bit depth maps in **3D Sliced** image mode for Galvo devices. Import the primary 16-bit PNG, set its physical width to the exported `size_mm`, and use 3D Sliced for layered relief. The `_8bit.png` file is a compatibility copy; the shaded inspection image is not an engraving input.

White is the highest surface and black is the deepest recess. `depth_mm` describes the intended relief span and scales the inspection geometry; it does not set material removal in LightBurn. Pass count, material, focus, speed, power, frequency and pulse width require coupon calibration. A 100 W rating and F190 focal length alone do not establish spot size or achievable detail, so this application does not prescribe laser parameters from those specifications.

At 28.5 mm / 2048 pixels, raster spacing is approximately 13.9 µm. The default 100 µm Perlage ring spacing has about 7.2 pixels per cycle; enlarge ring spacing or increase output resolution when inspecting fine graining. Raster spacing is not the laser spot size or LightBurn scan interval. Inspect minimum feature sizes against measured engraving trials.

Circular mode fills exterior pixels with the selected grayscale level; it does not produce an exclusion mask. Use an appropriate boundary/crop in the engraving workflow, especially because the default black exterior denotes the deepest level.

References: [LightBurn 2.1 Galvo cut settings](https://docs.lightburnsoftware.com/2.1/Reference/CutSettingsEditor/GalvoSpecificCutSettings/) and [3D Sliced engraving guide](https://docs.lightburnsoftware.com/2.1/Guides/3DSlicedImage/).

## Release history

See [RELEASE-NOTES.md](RELEASE-NOTES.md) for the full release history.
