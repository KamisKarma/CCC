"""Select the shortest valid program per case, independently verify, and package.

Without --write this only reports current best scores. --write creates five
submission files, report.json, and a ZIP under levels/level6/optimized_final,
after checking every chosen program with both independent and official engines.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from validate_level6_optimized import read_cases, read_programs, simulate, validate_files

DATASETS = ("example", "small", "medium", "large", "enormous")


def relative_name(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path.resolve())


def choose_programs(base: Path, extra_directories=()):
    reports, outputs, invalid = [], {}, []
    for dataset_index, name in enumerate(DATASETS):
        input_path = base / f"in_level-6_{dataset_index}-{name}.txt"
        output_name = f"out_level-6_{dataset_index}-{name}.txt"
        cases = read_cases(input_path)
        best = [None] * len(cases)
        best_sources = [None] * len(cases)
        baseline_sizes = [None] * len(cases)
        candidates_checked = Counter()

        def consider(case_index, program, source, *, baseline=False):
            verdict = simulate(cases[case_index], program)
            if not verdict["valid"]:
                invalid.append({"source": source, "case": case_index,
                                "reason": f"accepted {verdict['accepted']}, required {verdict['required']}"})
                return
            candidates_checked[source.split('/')[0]] += 1
            if baseline:
                baseline_sizes[case_index] = len(program)
            if best[case_index] is None or len(program) < len(best[case_index]):
                best[case_index], best_sources[case_index] = program, source

        def consider_file(path, *, baseline=False):
            if not path.exists():
                return
            source = relative_name(path, base)
            try:
                programs = read_programs(path)
                if len(programs) != len(cases):
                    raise ValueError(f"expected {len(cases)} programs, got {len(programs)}")
                for index, program in enumerate(programs):
                    consider(index, program, source, baseline=baseline)
            except (OSError, ValueError) as exc:
                invalid.append({"source": source, "reason": str(exc)})

        consider_file(base / output_name, baseline=True)
        consider_file(base / f"candidate-route-{dataset_index}.txt")
        directories = [base / directory for directory in (
            "optimized_beam", "optimized_beam_v2", "optimized_multibeam",
            "optimized_fivebeam", "optimized_sixbeam", "optimized_parallel", "optimized_compact", "optimized_augmented",
            "optimized_cycles", "optimized_sixwide", "optimized_sixrefine",
            "optimized_final", "optimized_compact_round2", "optimized_augmented_round2", "optimized_beam_round2",
        )] + list(extra_directories)
        seen_files = set()
        for directory in directories:
            consider_file(directory / output_name)
            for case_directory in (directory / name, directory / str(dataset_index)):
                for path in sorted(case_directory.glob("case_*.txt")):
                    if path.resolve() in seen_files:
                        continue
                    seen_files.add(path.resolve())
                    source = relative_name(path, base)
                    try:
                        case_index = int(path.stem.removeprefix("case_"))
                        if not 0 <= case_index < len(cases):
                            raise ValueError(f"invalid zero-based case index {case_index}")
                        programs = read_programs(path)
                        if len(programs) != 1:
                            raise ValueError(f"expected one program, got {len(programs)}")
                        consider(case_index, programs[0], source)
                    except (OSError, ValueError) as exc:
                        invalid.append({"source": source, "reason": str(exc)})
        missing = [index for index, program in enumerate(best) if program is None]
        if missing:
            raise ValueError(f"{name}: no valid candidates for cases {missing}")
        if any(size is None for size in baseline_sizes):
            raise ValueError(f"{name}: baseline missing or invalid")
        text = "\n\n".join("\n".join(" ".join(line) for line in program) for program in best) + "\n"
        outputs[output_name] = text
        score = sum(map(len, best))
        baseline_score = sum(baseline_sizes)
        reports.append({
            "dataset": name, "filename": output_name, "programs": len(cases),
            "patterns": sum(case.count for case in cases), "score": score,
            "baseline_score": baseline_score, "saved_lines": baseline_score - score,
            "reduction_percent": round(100 * (baseline_score - score) / baseline_score, 4),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "candidates_checked": dict(candidates_checked),
            "selected_sources": dict(Counter(source.split('/')[0] for source in best_sources)),
            "cases": [{"index": index, "required": case.count, "lines": len(program),
                       "baseline_lines": baseline_sizes[index], "source": best_sources[index]}
                      for index, (case, program) in enumerate(zip(cases, best))],
        })
    total = sum(report["score"] for report in reports)
    baseline_total = sum(report["baseline_score"] for report in reports)
    report = {
        "valid": True, "score_definition": "Total instruction lines; lower is better. Every line counts, including all-noop lines.",
        "score_including_example": total,
        "score_excluding_example": sum(item["score"] for item in reports[1:]),
        "baseline_including_example": baseline_total,
        "baseline_excluding_example": sum(item["baseline_score"] for item in reports[1:]),
        "saved_lines": baseline_total - total,
        "reduction_percent": round(100 * (baseline_total - total) / baseline_total, 4),
        "programs": sum(item["programs"] for item in reports),
        "patterns": sum(item["patterns"] for item in reports),
        "verification": {"independent_simulation": "passed", "official_sandbox": "not run in report-only mode"},
        "datasets": reports, "rejected_candidates": invalid,
    }
    return outputs, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1] / "levels" / "level6")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--candidate-dir", type=Path, action="append", default=[])
    parser.add_argument("--write", action="store_true", help="write and officially verify the final submission package")
    args = parser.parse_args()
    outputs, report = choose_programs(args.base_dir, args.candidate_dir)
    for item in report["datasets"]:
        print(f"{item['dataset']:9} {item['score']:>7,} lines (baseline {item['baseline_score']:,}; saved {item['saved_lines']:,}) "
              f"sources={item['selected_sources']}")
    print(f"TOTAL {report['score_including_example']:,}; excluding example {report['score_excluding_example']:,}; "
          f"reduction {report['reduction_percent']:.2f}%")
    if report["rejected_candidates"]:
        print(f"Rejected invalid or incomplete candidates: {len(report['rejected_candidates'])}")
        for item in report["rejected_candidates"][:8]:
            print(item)
    if not args.write:
        print("Report only. No final output files written; use --write to package.")
        return
    destination = args.output_dir or args.base_dir / "optimized_final"
    destination.mkdir(parents=True, exist_ok=True)
    for filename, text in outputs.items():
        path = destination / filename
        path.write_bytes(text.encode("utf-8"))
        verdict = validate_files(args.base_dir / filename.replace("out_", "in_", 1), path)
        if not verdict["valid"]:
            raise ValueError(f"Final file failed independent verification: {path}")
    sandbox = Path(__file__).with_name("verify_level6_sandbox.cjs")
    sandbox_result = subprocess.run(["node", str(sandbox), str(destination), str(args.base_dir)],
                                    check=True, capture_output=True, text=True)
    print(sandbox_result.stdout, end="")
    report["verification"]["official_sandbox"] = "passed"
    report["verification"]["official_sandbox_output"] = sandbox_result.stdout.strip()
    report_path = destination / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    archive = destination / "level6-optimized-outputs.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename in outputs:
            bundle.write(destination / filename, filename)
        bundle.write(report_path, "report.json")
    print(f"Wrote final outputs: {destination}")
    print(f"ZIP: {archive}")


if __name__ == "__main__":
    main()
