# Check your STL and GLB exports

Check both exports from one CAD revision against the overall dimensions agreed for delivery.

## Prepare the exports

Use Python and Node.js on your PATH. Download **Source code (zip)**, extract the whole archive, and open a shell in the extracted `meshassert-0.2.0` folder. [MeshAssert v0.2.0](https://github.com/LeeJUNhao791/meshassert/releases/tag/v0.2.0)

Create an `inputs` folder. Copy your STL and GLB exports there as `part.stl` and `part.glb`. Keep the STL in the original CAD axes. Export the GLB with the standard glTF Y-up axes and metre units.

## Write the dimension contract

Read the three overall spans from the drawing. In your CAD software, identify which CAD axis each span belongs to. Enter the spans in millimetres even when the STL coordinates are in metres.

The Hammond 1590B drawing gives **112.40 × 60.50 × 31.00 mm** in length × width × height order. The STEP model uses X for length, Y for height, and Z for width. [Hammond drawing](https://www.hammfg.com/files/parts/pdf/1590B.pdf) · [STEP model used for the example](https://github.com/whbeers/enclosure_kicad_footprints/blob/e59b04e1130962d179eb39395b5c85b11a5789ce/Enclosures.pretty/1590B.stp)

Save this example as `inputs/dimensions.json` for the Hammond exports. For your own part, substitute its CAD spans and your agreed digital acceptance tolerance. `tolerance_mm` applies to each axis. This example uses ±0.10 mm for comparing the digital exports.

```json
{
  "expected_mm": {"x": 112.4, "y": 31.0, "z": 60.5},
  "tolerance_mm": 0.10
}
```

## Run the check

Read the STL unit in the CAD export settings or the export notes. STL does not store a unit. The Hammond STL uses millimetres, so the command uses `--stl-unit mm`. Use `--stl-unit m` for STL coordinates in metres.

```sh
python meshassert.py --expect inputs/dimensions.json --stl inputs/part.stl --stl-unit mm --glb inputs/part.glb
```

MeshAssert prints one JSON report. It reports both files in CAD X/Y/Z and millimetres, including the axis conversion for the GLB. Both Hammond exports passed at **112.400 × 31.000 × 60.500 mm**, rounded to three decimals.

## Read the result

Check the overall `status`, then read `assets.stl` and `assets.glb` separately. In each asset, `dimensions_mm` gives the measurements and `out_of_tolerance_axes` lists the axes that failed. For each of those axes, `deviation_mm` is measured minus expected. A positive value means the export is larger than the target.

| Exit code | `status` | What it means |
| --- | --- | --- |
| 0 | `pass` | Both exports meet the contract. |
| 1 | `fail` | Both exports could be measured. At least one axis is outside tolerance. |
| 2 | `invalid` | An input or checker error occurred. Read the `error` field and check the other asset's result. |

Try an out-of-tolerance case with the files included in the release.

```sh
python meshassert.py --expect fixtures/ribbed-bracket/expected.json --stl fixtures/ribbed-bracket/ribbed_bracket.stl --stl-unit mm --glb fixtures/ribbed-bracket/ribbed_bracket_tall.glb
```

The STL passes. The GLB reports `out_of_tolerance_axes: ["z"]` and a CAD Z deviation of about **+2.00 mm**. Its measured height is about **37.00 mm** against a target of **35.00 mm** with **±0.15 mm** tolerance. The command exits `1`. [Example JSON report](evidence/ribbed-bracket-fail.json)
