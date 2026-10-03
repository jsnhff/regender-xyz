# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""
CLI Module

Provides the Textual TUI for Regender.
"""

from .tui import RegenderTUI, run_selection, run_tui

__all__ = [
    "RegenderTUI",
    "run_tui",
    "run_selection",
]
