"""Where a run puts its output.

Every artifact a run produces belongs together: the book, the source it came
from, the cast, the name map, the QC report, the substitution log, the decision
sheet. They only mean anything as a set -- a name map describes exactly one
transformed book, and beside a different one it is worse than nothing.

They used to share a folder per book. The CLI wrote to "<book>-<timestamp>",
the TUI to "<book>" with the timestamp in the filename instead, so two runs of
the same book overwrote each other's name_map.json and name_report.json while
the books themselves sat side by side looking fine. An all_female run in
September silently replaced the nonbinary run's map from fifteen minutes
earlier.

One folder per run, grouped under the book, so the set stays together and
older runs stay readable.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

OUTPUT_ROOT = Path("books/output")


def book_slug(input_path: str | Path) -> str:
    """A folder-safe name for the book, without the Gutenberg id."""
    stem = Path(input_path).stem
    # "pg1342-pride-and-prejudice" -> "pride-and-prejudice"
    if re.match(r"^pg\d+[-_]", stem):
        stem = re.split(r"[-_]", stem, maxsplit=1)[1]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return slug or "book"


def run_directory(
    input_path: str | Path,
    transform_type: str,
    when: datetime | None = None,
    root: Path | None = None,
    create: bool = True,
) -> Path:
    """The folder this run owns: books/output/<book>/<transform>_<when>.

    Unique to the minute. Two runs of the same transform inside one minute
    would collide, which in practice means a rerun after an immediate failure,
    and sharing that folder is the right answer for it.
    """
    stamp = (when or datetime.now()).strftime("%Y-%m-%d_%H-%M")
    directory = (root or OUTPUT_ROOT) / book_slug(input_path) / f"{transform_type}_{stamp}"
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def keep_source(input_path: str | Path, directory: Path) -> Path | None:
    """Copy the book this run started from in beside its output.

    Without it a folder cannot be checked against anything: comparing a
    transform to its source is the only way to tell a miss from a success, and
    six months on nobody remembers which file on disk was the input, or whether
    it has been edited since.
    """
    source = Path(input_path)
    if not source.exists() or not source.is_file():
        return None
    destination = directory / f"source{source.suffix or '.txt'}"
    try:
        if not destination.exists():
            shutil.copy2(source, destination)
    except OSError:
        return None
    return destination


def normalize_dropped_path(text: str) -> str:
    """Turn what a terminal produces when you drop a file into a usable path.

    Dropping a file does not paste the path -- it pastes the path as a shell
    would need it written, and every terminal does that slightly differently:

        /Users/me/test books/x.txt      typed by hand
        /Users/me/test\\ books/x.txt     macOS Terminal, iTerm: escaped spaces
        '/Users/me/test books/x.txt'    quoted when it contains a space
        "/Users/me/test books/x.txt"    the same, double-quoted
        file:///Users/me/test%20books/  some apps drop a URL instead

    None of those open with Path() as written, so dropping a file whose folder
    has a space in its name -- "regender-xyz test books" -- silently did
    nothing at all.

    Quotes are unwrapped before backslashes are touched: inside quotes a
    backslash is a literal character, and unescaping there would corrupt a path
    that genuinely contains one.
    """
    from urllib.parse import unquote, urlparse

    text = text.strip()
    if not text:
        return text

    if text.startswith("file://"):
        return unquote(urlparse(text).path)

    for quote in ("'", '"'):
        if len(text) > 1 and text.startswith(quote) and text.endswith(quote):
            return text[1:-1]

    # Unquoted: a backslash escapes the character after it, which is how a
    # terminal writes a space it does not want the shell to split on.
    return re.sub(r"\\(.)", r"\1", text)
