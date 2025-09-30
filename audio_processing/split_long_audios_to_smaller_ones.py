#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split long MP3s into 30-minute chunks, preserving numeric prefixes.

Naming rule (examples):
- Input : 02_01_04_How long does it take to learn to speak English fluently？.mp3
- Output: 02_01_04__01_How long does it take to learn to speak English fluently？.mp3
         02_01_04__02_How long does it take to learn to speak English fluently？.mp3
         ...

Concurrency: processes multiple files in parallel.

Usage:
  python split_mp3s.py /path/to/base --minutes 30 --workers 4
  python split_mp3s.py . --dry-run

Notes:
- Requires: ffmpeg, ffprobe
- Skips files that already look like split parts (contain "__<number>_" after the numeric prefix).
"""

import argparse
import concurrent.futures as futures
import json
import math
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# Regex to capture:
#   Group 1 = numeric prefix with underscores (e.g., "02_01_04")
#   Group 2 = the rest starting with an underscore up to before the extension (e.g., "_How long ...")
# We apply it to the stem (name without extension) and later re-append .mp3
PREFIX_RE = re.compile(r"^(\d+(?:_\d+)*)(_.+)$", flags=re.UNICODE)

# Detect already-split pattern like: 02_01_04__01_How...
ALREADY_SPLIT_RE = re.compile(r"^(\d+(?:_\d+)*)__\d{1,3}_.+$", flags=re.UNICODE)

def run_cmd(cmd: str) -> Tuple[int, str, str]:
    """Run a shell command, return (rc, stdout, stderr)."""
    proc = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()
    return proc.returncode, out, err


def ffprobe_duration_seconds(path: Path) -> Optional[float]:
    """Return duration in seconds using ffprobe, or None if unavailable."""
    cmd = f'ffprobe -v error -show_entries format=duration -of json {shlex.quote(str(path))}'
    rc, out, err = run_cmd(cmd)
    if rc != 0:
        return None
    try:
        data = json.loads(out)
        dur = float(data["format"]["duration"])
        if math.isfinite(dur) and dur > 0:
            return dur
    except Exception:
        pass
    return None


def is_already_split(filename_stem: str) -> bool:
    return bool(ALREADY_SPLIT_RE.match(filename_stem))


def compute_output_pattern(infile: Path) -> Optional[str]:
    """
    Build an ffmpeg segment output pattern in the SAME folder.
    We keep the original title part as-is (including Arabic/punctuation).
    Pattern will be something like:
        <dir>/<numeric_prefix>__%02d<title_part>.mp3
    """
    stem = infile.stem  # name without extension
    m = PREFIX_RE.match(stem)
    if not m:
        return None  # doesn't match the "NN[_NN]*_Title" scheme

    numeric_prefix = m.group(1)   # e.g., 02_01_04
    title_part = m.group(2)       # e.g., _How long does it take...

    # Our pattern uses %02d; we’ll set segment_start_number=1 to start at 01
    # We keep spaces and non-ASCII safely; ffmpeg handles UTF-8 paths.
    pattern_name = f"{numeric_prefix}__%02d{title_part}.mp3"
    return str(infile.parent / pattern_name)


def split_with_ffmpeg(infile: Path, minutes: int, dry_run: bool = False, overwrite: bool = False) -> Tuple[str, str]:
    """
    Split infile into <minutes>-minute segments (default 30) using ffmpeg -f segment with stream copy.
    Returns (status, message)
    """
    # Verify duration
    dur = ffprobe_duration_seconds(infile)
    if dur is None:
        return ("skip", f"[NO DURATION] {infile}")

    limit = minutes * 60
    if dur <= limit + 1:  # small tolerance
        return ("skip", f"[<= {minutes} min] {infile.name}")

    # Avoid re-splitting already-split files
    if is_already_split(infile.stem):
        return ("skip", f"[ALREADY SPLIT NAME] {infile.name}")

    output_pattern = compute_output_pattern(infile)
    if not output_pattern:
        return ("skip", f"[NAME MISMATCH] {infile.name} does not match expected 'NN[_NN]*_Title.mp3' pattern")

    # If chunks already exist and overwrite=False, skip
    parent = infile.parent
    # glob escaped: we can quickly check for first two parts to decide
    expected_first = (Path(output_pattern.replace("%02d", "01"))).name
    existing = list(parent.glob(expected_first))
    if existing and not overwrite:
        return ("skip", f"[EXISTS] {expected_first} ... (set --overwrite to re-split)")

    # Build ffmpeg command
    # -c copy  -> no re-encode (fast)
    # -f segment -segment_time <sec> -> split by time
    # -reset_timestamps 1 -> clean timestamps per segment
    # -segment_start_number 1 -> numbering starts at 1 (so %02d -> 01, 02, ...)
    cmd = (
        f'ffmpeg -hide_banner -loglevel error '
        f'-i {shlex.quote(str(infile))} '
        f'-f segment -segment_time {limit} -c copy '
        f'-reset_timestamps 1 -map 0 -segment_start_number 1 '
        f'{shlex.quote(output_pattern)}'
    )

    if dry_run:
        return ("dry-run", f"{cmd}")

    rc, out, err = run_cmd(cmd)
    if rc != 0:
        # Some MP3s may fail with -c copy around segment boundaries; fallback to re-encode if needed.
        fallback_cmd = (
            f'ffmpeg -hide_banner -loglevel error '
            f'-i {shlex.quote(str(infile))} '
            f'-f segment -segment_time {limit} -c:a libmp3lame -b:a 192k '
            f'-reset_timestamps 1 -map 0:a:0 -segment_start_number 1 '
            f'{shlex.quote(output_pattern)}'
        )
        rc2, out2, err2 = run_cmd(fallback_cmd)
        if rc2 != 0:
            return ("error", f"[FFMPEG FAIL] {infile.name}\ncopy_err: {err}\nreenc_err: {err2}")
        return ("ok", f"[RE-ENCODED] {infile.name} -> {Path(output_pattern).name.replace('%02d','01..')}")

    return ("ok", f"[SPLIT] {infile.name} -> {Path(output_pattern).name.replace('%02d','01..')}")


def collect_mp3s(base: Path) -> list[Path]:
    return [p for p in base.rglob("*.mp3") if p.is_file()]


def process_one(infile: Path, minutes: int, dry_run: bool, overwrite: bool) -> Tuple[str, str]:
    try:
        return split_with_ffmpeg(infile, minutes=minutes, dry_run=dry_run, overwrite=overwrite)
    except Exception as e:
        return ("error", f"[EXCEPTION] {infile}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Split MP3s longer than N minutes into chunks, preserving numeric prefixes.")
    ap.add_argument("base", type=str, help="Base directory to scan (recursively).")
    ap.add_argument("--minutes", type=int, default=30, help="Chunk length in minutes (default: 30).")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Parallel workers (default: CPU count).")
    ap.add_argument("--dry-run", action="store_true", help="Print the actions/ffmpeg commands without executing.")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing split parts if present.")
    args = ap.parse_args()

    base = Path(args.base).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        print(f"[ERROR] Base path not found or not a directory: {base}")
        raise SystemExit(2)

    files = collect_mp3s(base)
    if not files:
        print("[INFO] No MP3 files found.")
        return

    print(f"[INFO] Found {len(files)} mp3 files under {base}")
    print(f"[INFO] Minutes per chunk: {args.minutes} | Workers: {args.workers} | Dry-run: {args.dry_run} | Overwrite: {args.overwrite}")

    # Run concurrently
    ok = err = skipped = 0
    with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        tasks = [
            ex.submit(process_one, f, args.minutes, args.dry_run, args.overwrite)
            for f in files
        ]
        for fut in futures.as_completed(tasks):
            status, msg = fut.result()
            if status == "ok":
                ok += 1
            elif status in ("skip", "dry-run"):
                skipped += 1
            else:
                err += 1
            print(f"{status.upper():7} | {msg}")

    print("\n=== SUMMARY ===")
    print(f"OK: {ok} | SKIPPED: {skipped} | ERRORS: {err}")


if __name__ == "__main__":
    main()
