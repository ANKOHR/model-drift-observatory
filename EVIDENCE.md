# Local build evidence

Measured on 2026-10-01, Windows, Python 3.12.10, CPU only. No external API, model, GPU, or network calls were made. The editable install used pip with `--no-index --no-deps --no-build-isolation`.

- Full pytest suite: 45 passed in 2.57 seconds in the final build verification.
- Installed `mdo` fixture generation, run, and Markdown report: 1.0540087 seconds total measured with PowerShell Stopwatch, report written to a local file. This is one local observation, not a performance guarantee.
- Installed `mdo report --format json` completed successfully and its counts and every changed ID were independently checked against expectations.json.
- Synthetic ground truth: 200 paired records, 80 changed, 120 unchanged, and 20 changes in each of four disjoint categories. All 80 expected IDs match the engine findings exactly, with zero false positive IDs and zero missed planted cases.
- The five-pair hand-written example produces four changed pairs and one control.
- Corrupting the first planted status back to 200 changes the computed total to 79 and status count to 19. The engine never consumes expectations.json.
- Repeated runs produce identical result and Markdown report bytes. Reports carry provenance and source SHA-256 hashes.
- Adversarial checks cover empty directories, malformed JSON with parser line, schema mismatch, global duplicate IDs, duplicate JSON keys, negative/nonfinite/excessive latency, future/reversed dates, oversized strings, Unicode, Windows paths, and atomic output failure cleanup.

Evidence-based build improvement: review identified that ordinary JSON parsing silently accepts duplicate object keys, which could overwrite a supplied observation. The input parser now rejects duplicate keys with a named parse error, pinned by a regression test. This improves input honesty without claiming any measured production benefit.

Final review improvement: a caller's low decimal precision could round a latency delta onto the threshold. Arithmetic now uses a private context; a regression test sets precision to two digits and traps inexact arithmetic while requiring identical findings for an 18-place decimal delta. Noncanonical ISO date forms also have explicit rejection tests. Reports now retain the supplied provenance declarations.

Boundaries: these measurements establish fixture correctness and a local demo runtime only. Real-world error rate, time saved, money saved, adoption, and buyer willingness to pay remain unmeasured. No real trials are shipped. The two-week improvement hook and final verdict are still pending real use.
