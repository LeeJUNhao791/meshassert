# Check STL and GLB dimensions in a pull request

Use MeshAssert in a repository that stores a dimension contract, a manufacturing STL, and a preview GLB. The workflow runs the CLI on pull requests and saves a single JSON report with the results for both models.

1. Copy the workflow below to `.github/workflows/meshassert-pr-gate.yml` in your repository.
2. Set `FIXTURES` and the filenames passed to `--expect`, `--stl`, and `--glb` to match your project. Use `--stl-unit m` if your STL coordinates are in metres.
3. Open a pull request to run the check. In the target branch's protection rule, add **MeshAssert dimensions** as a required check and choose GitHub Actions as its source. GitHub blocks merging when that check fails. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)

The example paths match the consumer repository's ribbed-bracket fixture. The second checkout uses the exact commit published as [MeshAssert v0.1.0](https://github.com/LeeJUNhao791/meshassert/releases/tag/v0.1.0).

```yaml
name: MeshAssert PR gate

on: pull_request

permissions:
  contents: read

jobs:
  dimensions:
    name: MeshAssert dimensions
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Check out MeshAssert v0.1.0
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          repository: LeeJUNhao791/meshassert
          ref: 438e20a6d614c644739679911ca30043b330149e
          path: .meshassert
          persist-credentials: false
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: '3.11'
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version: '22'
      - name: Check CAD-axis dimensions
        env:
          FIXTURES: examples/meshassert-ribbed-bracket/fixtures
        run: |
          python -B .meshassert/meshassert.py \
            --expect "$FIXTURES/expected.json" \
            --stl "$FIXTURES/ribbed_bracket.stl" --stl-unit mm \
            --glb "$FIXTURES/candidate.glb" > "$RUNNER_TEMP/meshassert-report.json"
      - name: Upload MeshAssert JSON
        if: ${{ always() }}
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: meshassert-dimensions
          path: ${{ runner.temp }}/meshassert-report.json
          if-no-files-found: error
```

## Read the report

Open the Actions run and download **meshassert-dimensions** under **Artifacts**. It contains `meshassert-report.json`. The workflow uploads the report after a passing check and after a failed check.

The independent consumer PR used a 57 × 29 × 35 mm contract with ±0.15 mm tolerance per axis. Its **MeshAssert dimensions** job was required on the verification branch. [Consumer PR #9](https://github.com/LeeJUNhao791/glb-dimension-check/pull/9)

| GLB height | Result | JSON report |
| --- | --- | --- |
| 35 mm | Both models passed. | [Passing run](https://github.com/LeeJUNhao791/glb-dimension-check/actions/runs/45567383613#artifacts) |
| 37 mm | GLB failed on CAD Z, STL passed, and GitHub blocked the merge. | [Failing run](https://github.com/LeeJUNhao791/glb-dimension-check/actions/runs/45567771564#artifacts) |
