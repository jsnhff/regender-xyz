"""
Cassette provider — run the pipeline without an API key.

Records the prompts a run generates, so they can be answered by any model (or
by hand), then replays those answers back through the real pipeline. What gets
exercised is everything above the network: batching, the prompt the pipeline
actually builds, marker parsing, the retry path, name maps and the safety net.

    # 1. capture the prompts this book produces
    provider = CassetteProvider("cassettes/pp", mode="record")

    # 2. answer each <hash>.prompt.json into <hash>.response.txt

    # 3. run for real against those answers
    provider = CassetteProvider("cassettes/pp", mode="replay")

A recorded pair is deterministic for a given book and batching, so a cassette
can be committed and replayed in CI as a regression test over real model output.
"""

import hashlib
import json
import re
from pathlib import Path

# Matches the [[Pn]] markers the transform prompt asks the model to echo back.
_MARKER = re.compile(r"^\[\[P(\d+)\]\]$", re.MULTILINE)


class CassetteMissingError(RuntimeError):
    """Replay was asked for a prompt with no recorded answer."""


class CassetteProvider:
    """Stands in for an LLM provider, backed by prompts and answers on disk."""

    def __init__(
        self,
        directory: str,
        mode: str = "replay",
        name: str = "cassette",
        model: str = "cassette-1",
    ):
        if mode not in ("record", "replay"):
            raise ValueError(f"mode must be 'record' or 'replay', got {mode!r}")
        self.directory = Path(directory)
        self.mode = mode
        self.name = name
        self.model = model
        self.calls: list[str] = []
        self.directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ paths

    @staticmethod
    def key_for(system: str, user: str) -> str:
        """Stable id for a prompt, so recording and replay agree on the file."""
        digest = hashlib.sha256(f"{system}\x00{user}".encode())
        return digest.hexdigest()[:16]

    def prompt_path(self, key: str) -> Path:
        return self.directory / f"{key}.prompt.json"

    def response_path(self, key: str) -> Path:
        return self.directory / f"{key}.response.txt"

    # --------------------------------------------------------------- provider

    async def complete(self, messages: list[dict], **_kwargs) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] != "system"), "")
        key = self.key_for(system, user)
        self.calls.append(key)

        if self.mode == "record":
            self.prompt_path(key).write_text(
                json.dumps({"key": key, "system": system, "user": user}, indent=2),
                encoding="utf-8",
            )
            # Echo the source back untouched. The run still completes, so the
            # whole set of prompts is captured in one pass, and the output is
            # discarded — only the prompts are wanted here.
            return echo_source(user)

        recorded = self.response_path(key)
        if not recorded.exists():
            self.prompt_path(key).write_text(
                json.dumps({"key": key, "system": system, "user": user}, indent=2),
                encoding="utf-8",
            )
            raise CassetteMissingError(
                f"No answer recorded for prompt {key}. Its text has been written "
                f"to {self.prompt_path(key)} — answer it in {recorded}."
            )
        return recorded.read_text(encoding="utf-8")

    # Some call sites still use the older name.
    complete_async = complete

    # ----------------------------------------------------------------- status

    def pending(self) -> list[Path]:
        """Recorded prompts that have no answer yet."""
        return sorted(
            path
            for path in self.directory.glob("*.prompt.json")
            if not self.response_path(path.name.split(".")[0]).exists()
        )


def split_marked_prompt(user: str) -> list[tuple[str, str]]:
    """Pull (marker index, paragraph) pairs out of a transform prompt."""
    body = user.split("\n\n", 1)[1] if "\n\n" in user else user
    blocks = []
    for block in body.split("\n\n"):
        marker, _, text = block.partition("\n")
        match = _MARKER.match(marker.strip())
        if match:
            blocks.append((match.group(1), text.strip()))
        else:
            blocks.append((str(len(blocks) + 1), block.strip()))
    return blocks


def echo_source(user: str) -> str:
    """A response that returns every paragraph unchanged, markers intact."""
    return "\n\n".join(f"[[P{index}]]\n{text}" for index, text in split_marked_prompt(user))


def build_response(paragraphs: list[str], start: int = 1) -> str:
    """Format transformed paragraphs the way the prompt asks for them back."""
    return "\n\n".join(f"[[P{index}]]\n{text}" for index, text in enumerate(paragraphs, start))


def write_response(directory: str, key: str, paragraphs: list[str]) -> Path:
    """Save an answer for a recorded prompt."""
    path = Path(directory) / f"{key}.response.txt"
    path.write_text(build_response(paragraphs), encoding="utf-8")
    return path


def load_prompt(path: str) -> dict:
    """Read a recorded prompt, with its paragraphs already split out."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["paragraphs"] = split_marked_prompt(data["user"])
    return data


def cassette_for(directory: str, mode: str = "replay") -> CassetteProvider:
    """Convenience constructor mirroring the provider plugins."""
    return CassetteProvider(directory, mode=mode)


__all__ = [
    "CassetteMissingError",
    "CassetteProvider",
    "build_response",
    "cassette_for",
    "echo_source",
    "load_prompt",
    "split_marked_prompt",
    "write_response",
]
