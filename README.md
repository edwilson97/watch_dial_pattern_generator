# Watch Dial Pattern Generator

Current version: **1.1.0**. See [release notes](RELEASE-NOTES.md) for changes.

A mathematical grayscale height-map generator for watch dials. Supports a Tkinter desktop GUI and CLI, 25 pattern families, pattern-specific GUI settings, and 8/16-bit PNG plus JSON metadata exports. No artificial lighting is applied to engraving exports.

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
attach the ZIP files to a GitHub Release. Once the Windows signing setup below is
complete, the workflow signs the Windows executable with Azure Artifact Signing.
Previously published unsigned downloads are unchanged. GitHub's
macOS builds are signed with the configured Developer ID Application certificate,
but are not yet notarized, so macOS Gatekeeper may still require approval. On macOS,
use **System Settings → Privacy & Security → Open Anyway** if you trust the build.
Notarization requires additional Apple credentials and is not configured yet.

### Windows signing setup (Azure Artifact Signing)

The workflow uses these Artifact Signing resources:

| Setting | Value |
| --- | --- |
| Account | `DialPatternGeneratorApp` |
| Certificate profile | `DialPatternGeneratorApp` |
| Azure region | Central US |
| Endpoint | `https://cus.codesigning.azure.net/` |

The certificate profile must be **Public Trust** for public Windows downloads;
Public Trust Test and Private Trust profiles are not publicly trusted. Azure keeps
the signing key; no certificate export or client secret is needed for this setup.

1. In the Azure portal, open **Microsoft Entra ID → App registrations → New
   registration**. Name the application `GitHub-DialPatternGeneratorApp`, select
   accounts in this organizational directory only (single tenant), leave the
   redirect URI empty, and register it. Record the **Application (client) ID** and
   **Directory (tenant) ID** from its Overview page. Also record the **Subscription
   ID** from the subscription containing the signing account.
2. In this GitHub repository, open **Settings → Environments → New environment**
   and create `native-signing`. Under its deployment branches and tags, select
   **Selected branches and tags** and allow the `main` branch and `v*` tags (also
   allow `master` if that branch is used). The native-build matrix uses this
   environment; only its Windows job signs in to Azure.
3. Back in the Entra app registration, open **Certificates & secrets → Federated
   credentials → Add credential**. Choose **GitHub Actions deploying Azure
   resources** and enter:

   | Field | Value |
   | --- | --- |
   | Organization/owner | `edwilson97` |
   | Organization ID (GitHub owner ID) | `6722229` |
   | Repository | `watch_dial_pattern_generator` |
   | Repository ID | `1427720192` |
   | Entity type | Environment |
   | Environment | `native-signing` |
   | Credential name | `github-native-signing` |
   | Issuer | `https://token.actions.githubusercontent.com` |
   | Audience | `api://AzureADTokenExchange` |
   | Subject | `repo:edwilson97@6722229/watch_dial_pattern_generator@1427720192:environment:native-signing` |

   The GitHub wizard fills the issuer, audience, and subject. Verify that they
   match the values above, then add the credential. This environment-based subject
   works for release tags without creating an Azure credential for each tag.
   This repository uses GitHub's immutable subject format, so both numeric IDs
   are required. Although the portal labels the owner field "Organization", this
   repository is owned by the personal account `edwilson97`; use that account's
   name and numeric ID.
4. Open **Artifact Signing Accounts → DialPatternGeneratorApp → Access control
   (IAM) → Add role assignment**. Select **Artifact Signing Certificate Profile
   Signer**, choose **User, group, or service principal**, and select the
   `GitHub-DialPatternGeneratorApp` application. Review and assign the role on this
   signing account. Subscription-wide Contributor access is not needed.
5. In GitHub, open **Settings → Environments → native-signing → Environment
   secrets** and add:

   | Secret | Value |
   | --- | --- |
   | `AZURE_CLIENT_ID` | Application (client) ID from step 1. |
   | `AZURE_TENANT_ID` | Directory (tenant) ID from step 1. |
   | `AZURE_SUBSCRIPTION_ID` | Subscription ID containing the signing account. |

Once this workflow is on `main`, run **Actions → Build native apps → Run workflow**
against `main`. The Windows job checks configuration, builds with PyInstaller,
authenticates using GitHub OIDC, signs `WatchDialPatternGenerator.exe`, verifies
the Authenticode signature and timestamp, and then runs the packaged-app smoke
checks and creates the ZIP. Missing credentials, failed signing, or an invalid or
untimestamped signature fail the job before a download is uploaded. Bundled
third-party libraries retain their existing signatures.

The Azure identity needs the signer role even if your own Azure user can sign.
Allow time for a new role assignment to propagate before retrying a failed build.
Existing tags, including `v1.1.0`, still point to their original workflow; running
an old tag will not use this signing configuration. Use a new tag after the change
is merged, or manually build the updated `main` branch.

References: [Microsoft's OIDC setup](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect),
[Artifact Signing authentication and signer role](https://github.com/Azure/artifact-signing-action/blob/main/docs/OIDC.md),
[signing action](https://github.com/Azure/artifact-signing-action), and
[regional endpoints and timestamping](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations).

### macOS signing setup

Both macOS jobs require these repository secrets under **Settings → Secrets and
variables → Actions**:

| Secret | Value |
| --- | --- |
| `MACOS_CERTIFICATE_P12_BASE64` | Base64-encoded `.p12` containing the Developer ID Application certificate and its private key. |
| `MACOS_CERTIFICATE_PASSWORD` | The `.p12` export password. |
| `MACOS_SIGNING_IDENTITY` | Full certificate identity, such as `Developer ID Application: Bridge Watches LLC (TEAMID)`. |

The workflow imports the identity into a temporary keychain and passes it to
PyInstaller, which signs the executable, bundled libraries, and app with hardened
runtime and timestamps. CI verifies the expected Developer ID signature and runs
the packaged-app smoke checks. Missing signing secrets fail macOS builds rather
than publishing ad-hoc signed downloads. The keychain and certificate file are
removed at the end of the job.

Local builds can use a signing identity already installed in Keychain Access by
setting `MACOS_SIGNING_IDENTITY` before running PyInstaller. Without that variable,
local macOS builds retain PyInstaller's default ad-hoc signing.

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
python3 dial_patterns.py --help
```

To see all available options for the CLI, use the `-h` or `--help` command line parameter.

Available patterns: `hobnail`, `barleycorn`, `sunburst`, `basketweave`, `tapisserie`, `fishscales`, `flinque`, `wave`, `annularwave`, `graindorge`, `flamme`, `panier`, `escargot`, `moire`, `chevron`, `rosette`, `sectorrings`, `honeycomb`, `perlage`, `diamondlattice`, `isometriccubes`, `fanscallop`, `asanoha`, `brick`, and `dimples`.

[View the pattern catalog (PNG)](images/pattern_catalog.png) for a visual guide to all 25 patterns.

The GUI shows only fields relevant to the chosen pattern and includes a scrollable settings area.

The GUI remembers edited pitch values per pattern until **Reset to defaults**.

The grayscale preview refreshes when you edit a parameter and move focus to another
field. Pattern, style, and checkbox changes refresh immediately. Invalid entries
keep the last valid preview visible and show an error in the status text.

## Dimples (golf ball texture)

Select **Dimples (golf ball texture)** for staggered rows of round recessed bowls
with flat land between them. **Pattern pitch** sets center-to-center spacing;
**Dimple diameter** sets the opening diameter and must be positive and no larger
than the pitch. Set diameter equal to pitch for touching dimple edges; larger
pitch leaves flat space between them. Defaults are 0.75 mm pitch and 0.65 mm diameter. **Target depth**
sets the design relief depth. Rotation, pattern offset, inversion, circular masking,
and live 3D inspection are supported. White is the flat surface; black is the
bottom of a dimple.

```bash
python3 dial_patterns.py --cli --pattern dimples --pitch-mm 0.75 \
  --dimple-diameter-mm 0.65 --depth-mm 0.15 --output dimples.png
```

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

This tests all 25 generators and PNG exports and creates `images/pattern_catalog.png`.

## Full test suite (including real Tkinter GUI interaction)

The test runner exercises all 25 mathematical pattern renderers and GUI workflows.
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
