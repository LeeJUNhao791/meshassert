"""Check the two bundled CAD examples through the MeshAssert CLI."""

import json
import math
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
AXES = "xyz"
STATUS = ("pass", "fail", "invalid")

# Case name, STL, GLB, exit code, expected per-asset status and axis deviations.
PLATE = [
    ("plate nominal", "mounting_plate.stl", "mounting_plate.glb", 0, ("pass", {}), ("pass", {})),
    ("plate wide STL", "controls/wide.stl", "mounting_plate.glb", 1, ("fail", {"x": 1}), ("pass", {})),
    ("plate thick GLB", "mounting_plate.stl", "controls/thick.glb", 1, ("pass", {}), ("fail", {"z": 1})),
    ("invalid STL", "controls/broken.stl", "mounting_plate.glb", 2, ("invalid", {}), ("pass", {})),
    ("invalid GLB", "mounting_plate.stl", "controls/broken.glb", 2, ("pass", {}), ("invalid", {})),
    ("invalid before mismatch", "controls/wide.stl", "controls/broken.glb", 2,
     ("fail", {"x": 1}), ("invalid", {})),
    ("invalid contract", "mounting_plate.stl", "mounting_plate.glb", 2, ("invalid", {}), ("invalid", {})),
]

BRACKET = [
    ("bracket nominal", "ribbed_bracket.stl", "ribbed_bracket.glb", 0, ("pass", {}), ("pass", {})),
    ("bracket tall GLB", "ribbed_bracket.stl", "ribbed_bracket_tall.glb", 1, ("pass", {}), ("fail", {"z": 2})),
]


def verify_examples(folder, expected, tolerance, cases):
    fixture = f"fixtures/{folder}/"
    for name, stl, glb, code, stl_result, glb_result in cases:
        invalid_contract = name == "invalid contract"
        contract = fixture + ("controls/broken.json" if invalid_contract else "expected.json")
        command = [
            sys.executable, "meshassert.py", "--expect", contract,
            "--stl", fixture + stl, "--stl-unit", "mm", "--glb", fixture + glb,
        ]
        first, repeat = (subprocess.run(command, cwd=ROOT, capture_output=True) for _ in range(2))
        assert first.returncode == code and not first.stderr, (name, first)
        assert (first.returncode, first.stdout, first.stderr) == (repeat.returncode, repeat.stdout, repeat.stderr), name
        report = json.loads(first.stdout)
        assert report["status"] == STATUS[code], name
        assert report["axis_frame"] == "cad" and report["contract"] == contract, name
        if invalid_contract:
            assert report["error"] and "expected_mm" not in report, name
        else:
            assert report["expected_mm"] == dict(zip(AXES, expected)), name
            assert report["tolerance_mm"] == tolerance, name

        for kind, filename, (status, changes), role, unit, source_axes in (
            ("stl", stl, stl_result, "manufacturing_mesh", "mm", "xyz"),
            ("glb", glb, glb_result, "preview_asset", "m", "xzy"),
        ):
            asset = report["assets"][kind]
            assert asset["file"] == fixture + filename and asset["status"] == status, (name, kind, asset)
            assert asset["role"] == role and asset["coordinate_unit"] == unit, (name, kind)
            assert asset["source_axes"] == dict(zip(AXES, source_axes)), (name, kind)
            if status == "invalid":
                assert asset["error"] and "dimensions_mm" not in asset, (name, kind)
                continue
            assert asset["out_of_tolerance_axes"] == list(changes), (name, kind, asset)
            for axis, nominal in zip(AXES, expected):
                deviation = changes.get(axis, 0)
                assert math.isclose(asset["dimensions_mm"][axis], nominal + deviation, abs_tol=0.002), asset
                assert math.isclose(asset["deviation_mm"][axis], deviation, abs_tol=0.002), asset
                assert asset["within_tolerance"][axis] is (axis not in changes), asset

        print(f"PASS {name} (exit {code}, STL {stl_result[0]}, GLB {glb_result[0]})")


if __name__ == "__main__":
    verify_examples("mounting-plate", (64, 40, 6), 0.2, PLATE)
    verify_examples("ribbed-bracket", (57, 29, 35), 0.15, BRACKET)
