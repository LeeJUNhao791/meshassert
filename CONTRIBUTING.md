# Contributing to MeshAssert

MeshAssert compares the three overall CAD-axis spans of a paired STL and GLB against one dimension contract. It does not check hole geometry, mirroring, mesh topology, or the quality of a manufactured part. Keep changes and claims within this scope.

## Verify a change

Clone the repository and open a shell in its root. Put Python and Node.js on your PATH; the current CI uses Python 3.11 and Node.js 22. The bundled checkers need no package installation for this verification command:

```sh
python -B verify.py
```

The existing script runs nine cases twice, checking nominal pairs, mismatches, invalid inputs, exit codes, per-asset results, and repeatable JSON output. Include the command and result in your pull request. If a change affects behavior, add the smallest relevant regression case to the existing verification where practical.

Keep fixture models, expected contracts, and saved JSON evidence in version control. Preserve the bundled checkers' license notices. Keep [README.md](README.md) and [README.zh-CN.md](README.zh-CN.md) consistent when updating user instructions.

## Report a bug

Use the bug-report template. Include your OS, Python and Node.js versions, MeshAssert release or commit, exact command, exit code, stdout JSON, and stderr. Share a minimal STL/GLB pair and contract you are allowed to publish, with the expected CAD X/Y/Z spans and STL unit. Explain what you expected and what happened; distinguish a dimension mismatch (`fail`) from an input or checker error (`invalid`).

For coordinate and unit setup, see [Check your STL and GLB exports](docs/check-your-exports.md).
