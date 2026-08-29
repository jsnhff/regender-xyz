"""
Chapter-by-chapter QC for a transformed book. No LLM calls, no API keys.

    python scripts/qc_report.py SOURCE.json TRANSFORMED.json gender_swap
    python scripts/qc_report.py source.json swap.json gender_swap --json out/qc.json
    python scripts/qc_report.py source.json swap.json gender_swap --fail-on auto_fixable
    python scripts/qc_report.py source.json swap.json gender_swap --repair fixed.json

Exits non-zero when findings at or above --fail-on are present, so it can gate
CI or a print run. --repair re-runs the safety net over an existing transform
and writes a corrected book, no LLM calls needed.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.transformation import TransformType  # noqa: E402
from src.services.qc_service import (  # noqa: E402
    AUTO_FIXABLE,
    NEEDS_REVIEW,
    STRUCTURAL,
    QCService,
    format_report,
    load_book,
    repair_book,
)

SEVERITIES = {AUTO_FIXABLE: 0, STRUCTURAL: 1, NEEDS_REVIEW: 2}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Parsed source book JSON")
    parser.add_argument("transformed", help="Transformed book JSON")
    parser.add_argument(
        "transform_type",
        choices=[t.value for t in TransformType],
        help="Transform that produced the output",
    )
    parser.add_argument("--json", dest="json_path", help="Write the full report here")
    parser.add_argument(
        "--fail-on",
        choices=sorted(SEVERITIES, key=SEVERITIES.get),
        default=AUTO_FIXABLE,
        help="Exit non-zero when findings of this severity or worse exist (default: auto_fixable)",
    )
    parser.add_argument("--limit", type=int, default=8, help="Findings shown per severity")
    parser.add_argument(
        "--repair",
        metavar="OUT.json",
        help="Re-run the safety net against the source and write a corrected book",
    )
    args = parser.parse_args()

    transform_type = TransformType(args.transform_type)
    source = load_book(args.source)
    transformed = load_book(args.transformed)
    service = QCService(transform_type)

    report = service.check_book(source, transformed)
    print(format_report(report, limit=args.limit))

    if args.json_path:
        Path(args.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_path).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nFull report written to {args.json_path}")

    if args.repair:
        fixed = repair_book(source, transformed, transform_type)
        Path(args.repair).parent.mkdir(parents=True, exist_ok=True)
        Path(args.repair).write_text(json.dumps(fixed, indent=2), encoding="utf-8")
        after = service.check_book(source, fixed)
        print(
            f"\nRepaired book written to {args.repair}\n"
            f"  auto-fixable findings: {report.count(AUTO_FIXABLE)} -> "
            f"{after.count(AUTO_FIXABLE)}\n"
            f"  coverage:              {report.coverage:.1%} -> {after.coverage:.1%}"
        )
        report = after

    threshold = SEVERITIES[args.fail_on]
    blocking = sum(
        report.count(severity) for severity, rank in SEVERITIES.items() if rank <= threshold
    )
    if blocking:
        print(f"\nFAIL: {blocking} finding(s) at or above '{args.fail_on}'")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
