#!/usr/bin/env python3
import argparse
import csv
import json
import statistics
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "assets/config.json").read_text())
    protocol = (root / "references/protocol.md").read_text()
    if "statistical significance" not in protocol:
        raise ValueError("Missing pilot interpretation constraint")
    observations: dict[str, list[float]] = {variant: [] for variant in config["variants"]}
    with args.input.open(newline="") as source:
        for row in csv.DictReader(source):
            observations[row["variant"]].append(float(row["latency_ms"]))
    counts = {len(values) for values in observations.values()}
    if len(counts) != 1 or min(counts) < config["minimum_trials"]:
        raise ValueError("Expected balanced repeated measurements")
    baseline, candidate = (statistics.fmean(observations[name]) for name in config["variants"])
    result = {
        "baseline_mean_ms": baseline,
        "candidate_mean_ms": candidate,
        "difference_ms": candidate - baseline,
        "trials_per_variant": min(counts),
        "conclusion": config["conclusion"],
    }
    report = (root / "templates/report.md").read_text().format(**result)
    args.out.mkdir()
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.out / "report.md").write_text(report)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
