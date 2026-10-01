# Model Drift Observatory

`mdo` compares baseline and current observations of external APIs supplied in local JSON files. It measures exact status, response text, response field set, and latency changes. It makes no API requests. Python 3.10 or later, CPU only, standard-library runtime, no database or model calls.

Hypothesis: deterministic comparisons pinned to planted ground truth can provide trustworthy, reviewable evidence of changes in supplied observations. The synthetic acceptance target is 200 paired records, 80 planted changed pairs, zero false positives, and a demo under five seconds. This does not establish production accuracy.

## Quickstart

From the repository in PowerShell (setuptools and pytest must already be installed; no network installation is needed):

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
mdo fixtures --out demo
mdo run --input demo
mdo report --format md
python -m pytest -q
```

The exact chained demo `mdo fixtures --out demo && mdo run --input demo && mdo report --format md` works in PowerShell 7. Module invocation also works without installation: `python -m model_drift_observatory.cli ...`.

If pip warns that its user Scripts directory is absent from PATH, add it to the current session before running `mdo`:

```powershell
$mdoScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"
$env:PATH = "$mdoScripts;$env:PATH"
```

For the smallest hand-written example:

```powershell
mdo run --input examples/tiny
mdo report --format json
```

This example contains five synthetic pairs: four changed and one unchanged. Keep output files outside the input directory. Default saved results are `.mdo/results.json`; a subsequent run replaces them atomically.

## Input format

Each record is a pair for the same manually chosen API probe, not a single request. The caller is responsible for matching probe configuration, request, and environment. Put UTF-8 `.json` envelopes directly in one directory. All ordinary files are inspected; unsupported formats are rejected. Subdirectories are not traversed. `expectations.json` is reserved fixture metadata and never consumed by the engine.

```json
{
  "_comment": "SYNTHETIC illustrative input, not real API measurements",
  "synthetic": true,
  "records": [{
    "id": "probe-1",
    "api": "example-api",
    "synthetic": true,
    "baseline": {"date": "2026-09-01", "status": 200, "response": "ok", "fields": ["answer"], "latency_ms": "100"},
    "current": {"date": "2026-09-02", "status": 200, "response": "new", "fields": ["answer"], "latency_ms": "100"}
  }]
}
```

Required fields are exact; missing and unknown fields produce schema errors. IDs are unique across the directory and contain 1 to 256 characters. API labels have 1 to 4096 characters. Response strings may be empty and have at most 100000 characters. Field lists contain up to 1000 distinct nonempty names, each up to 256 characters. Unicode and Windows path strings are supported with JSON escaping.

Statuses are integer HTTP codes from 100 through 599. Dates are ISO calendar dates, baseline no later than current, both no later than `--as-of`. The reproducible default cutoff is 2026-09-30; for later observations supply an explicit cutoff. Latencies and thresholds are finite nonnegative decimals from 0 through 1000000000, with at most 18 fractional places and 64 characters of numeric text. Decimal strings are recommended to preserve precision. Booleans are never accepted as numbers. Negative amounts or other unknown domain fields are rejected, not silently ignored.

For Henry's manually entered real observations, set envelope and record `synthetic` to `false`, and describe collection and authorship in `_comment`. Reports call these user-declared real inputs; the tool cannot verify authorship. Do not commit private trials or API secrets. Mixed provenance uses separate envelopes and reconciles each record count.

## Subcommand catalogue

| Command | Example | Purpose |
| --- | --- | --- |
| fixtures | `mdo fixtures --out demo` | Write deterministic 200-pair fixtures and independent expectations |
| validate | `mdo validate --input demo --as-of 2026-09-30` | Check schema, dates, provenance consistency, and global ID uniqueness |
| compare | `mdo compare --input demo --latency-threshold-ms 100 --format json --out comparison.json` | Compute and render without saving intermediate state |
| run | `mdo run --input demo --results .mdo/results.json` | Compute a reusable local result |
| report | `mdo report --format md --out report.md` | Render saved results with provenance and traceability |

Every command supplies `--help` and an example. Errors exit with code 2, successful commands with code 0. Missing input/results have named errors and usage hints. JSON parse errors name the file and parser line. Schema errors name the file, document line 1, record index, and offending field. Unsupported CSV/YAML produce a named format error, rather than being silently skipped. Atomic report writes leave no partial temporary files on failure and preserve existing files until replacement succeeds.

## Comparison rules and architecture

```text
JSON envelopes -> CLI parsing and provenance checks -> pure core validation/comparison
                                                          |
                                                          v
                                            saved JSON with input SHA-256 hashes
                                                          |
                                                          v
                                            Markdown / JSON provenance report
fixture generator -> labelled observations + independent hand-computed expectations
```

Status and response text comparisons are exact. Field order is ignored; missing or additional field names count as schema drift. Latency changes count only when the absolute difference is strictly greater than the configured threshold. Both faster and slower changes count; signed deltas appear in findings. Categories can overlap, so category counts need not sum to changed pairs. Changed plus unchanged always equals total pairs. Reports include full before/after observations for each changed ID and SHA-256 hashes for every consumed file. No observed baseline variability or statistical significance is inferred from a single pair.

Files, records, and JSON keys are sorted for deterministic results. There is no clock-dependent output or randomness, so no random seed is required. Same input bytes and options produce byte-identical result and report files. File hashes intentionally change when input formatting changes. A supplied em dash is escaped as the literal JSON escape `\u2014` in outputs, preserving JSON round trips while avoiding that character in rendered surfaces.

## Honesty boundary and fixture policy

All figures are computed from input pairs. Synthetic results demonstrate correctness on planted examples only. This tool does not discover, predict, estimate API-wide drift, or claim causality. Unmeasured time and money savings are explicitly labelled unmeasured; no savings are claimed. Thresholds are user choices, not learned estimates. Reports always distinguish synthetic fixtures from user-declared real inputs, including empty and mixed datasets. Saved results are local trusted artifacts, not signed attestations.

JSON does not allow header comments: each fixture instead carries a top-level `_comment` beginning with SYNTHETIC and `synthetic: true`; each record also carries `synthetic: true`. Fixtures are labelled inside files, CLI output, and report banners. The 200 pairs consist of four disjoint blocks of 20 changes (status, response, schema, latency) and 120 unchanged controls. Expectations are hand-computed separately and are not read during comparison. Tests deliberately modify observations to prove figures change. No real trial results are shipped.

## Evidence, failure modes, and improvement hook

See `EVIDENCE.md` for measured local checks and `LESSONS.md` for operating lessons. Bounds and unknown-field rejection protect against negative, nonfinite, oversized, duplicate, and schema-drift values. Malformed inputs fail the entire run without replacing saved results. Empty directories generate zero reports. Response volatility, poor probe matching, hidden server changes, manually incorrect records, secrets in response payloads, and unrepresentative sampling remain user responsibilities. Full response text is included in findings, so redact sensitive data before input. A large directory is limited by available memory; this is a small local analysis tool.

After two weeks of actual use, measure record-level disagreement rate against a hand-checked real sample: `(false positive pairs + false negative pairs) / hand-checked pairs`. Record dates, sample size, labels, mismatches, and whether the tool was used in a private trial log. A zero-size sample gives an unmeasured rate, never zero accuracy error. If the error rate exceeds 10 percent, fix the most frequent failure cause and retest, or kill with the reason recorded. If the tool is not used, record that finding and kill it.

The two-week window starts at first real use, not at build completion. The final verdict remains pending that evidence. Expand if it earns daily use or revenue; integrate if it overlaps heavily with a sibling project; commercialise if a buyer would pay as-is; maintain as portfolio evidence otherwise; kill if unused or unable to meet acceptance criteria. See `VERDICT.md`. Public publishing is a separate verification step; this build performs no publication.
