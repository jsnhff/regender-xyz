"""
Chapter-by-chapter QC for a transformed book. No LLM calls, no API keys.

    python scripts/qc_report.py SOURCE.json TRANSFORMED.json gender_swap
    python scripts/qc_report.py source.json swap.json gender_swap --json out/qc.json
    python scripts/qc_report.py source.json swap.json gender_swap --fail-on auto_fixable

Exits non-zero when findings at or above --fail-on are present, so it can gate
CI or a print run.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.transformation import TransformType  # noqa: E402
from src.services.qc_service import (  # noqa: E402
    AUTO_FIXABLE,
    NEEDS_REVIEW,
    STRUCTURAL,
    check_files,
    format_report,
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
    args = parser.parse_args()

    report = check_files(
        args.source,
        args.transformed,
        TransformType(args.transform_type),
        report_path=args.json_path,
    )
    print(format_report(report, limit=args.limit))
    if args.json_path:
        print(f"\nFull report written to {args.json_path}")

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
