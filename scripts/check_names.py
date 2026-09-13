"""What the name map got wrong, before the book is transformed.

The map is built and audited before the first chapter, and the result is written
to name_report.json in the run folder -- so this can be read the moment
"Transforming" appears, and the run stopped if the answer is bad. Every fault it
finds costs nothing to fix at that point and 187 pages to fix afterwards.

    python scripts/check_names.py                 # the newest run
    python scripts/check_names.py <run folder>    # a particular one
"""

import json
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "books" / "output"


def newest_run() -> Path:
    folders = [p for p in OUTPUT.rglob("*") if p.is_dir() and (p / "name_report.json").exists()]
    if not folders:
        raise SystemExit("No run with a name report yet.")
    return max(folders, key=lambda p: p.stat().st_mtime)


def main() -> int:
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_run()
    report_path = run / "name_report.json"
    if not report_path.exists():
        raise SystemExit(f"No name_report.json in {run}")

    report = json.loads(report_path.read_text())
    print(f"{run.name}\n")
    print(
        f"  {report.get('entries', 0)} map entries, {report.get('accepted', 0)} characters renamed"
    )

    refused = report.get("refused") or {}
    if refused:
        print(f"\n  {len(refused)} supplied rename(s) refused before they reached the book:")
        for original, why in refused.items():
            print(f"     {original}: {why}")

    problems = report.get("problems")
    if problems is None:
        # An older run, or one that predates the audit: run it now.
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.models.character import CharacterAnalysis
        from src.services.name_engine import audit_name_map

        cast_path, map_path = run / "characters.json", run / "name_map.json"
        if not (cast_path.exists() and map_path.exists()):
            print("\n  (no audit recorded, and no cast to run one against)")
            return 0
        problems = audit_name_map(
            json.loads(map_path.read_text()),
            CharacterAnalysis.from_dict(json.loads(cast_path.read_text())),
        )
        print("\n  (no audit recorded for this run; here is one now)")

    flags = [f for f in report.get("flags", []) if "refused" not in f]
    if flags:
        print(f"\n  {len(flags)} note(s) from the engine:")
        for flag in flags[:10]:
            print(f"     {flag}")

    if problems:
        print(f"\n  {len(problems)} PROBLEM(S) IN THE MAP — fix these before transforming:")
        for problem in problems:
            print(f"     {problem}")
        return 1

    print("\n  No problems in the name map. Safe to transform.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
