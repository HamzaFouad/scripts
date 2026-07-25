#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strip unnecessary metadata from MP3 files in place: embedded thumbnails/album art,
comments, and any other ID3 tags (title, location, encoder info, etc.), while
preserving the "speed_applied" tag used by speed_audio_script_v2.py for idempotency.

Stream-copies the audio (no re-encode), so this is fast and lossless — it only
touches the container/metadata layer, not the audio data itself.

Usage:
  python strip_metadata.py /path/to/directory
  python strip_metadata.py /path/to/directory --recursive
  python strip_metadata.py /path/to/directory --dry-run
  python strip_metadata.py /path/to/directory --force

Notes:
- Requires: ffmpeg, ffprobe
- Drops any attached-picture stream (thumbnails/cover art) and all metadata tags.
- Re-adds the speed_applied tag afterward if the original file had one.
- Skips files that are already clean (no tags besides speed_applied, single audio
  stream) unless --force is given.
- Only replaces the original after verifying the stripped output's duration matches
  (stream copy should be exact, but this guards against a bad ffmpeg run).
"""

import argparse
import concurrent.futures as futures
import json
import logging
import math
import os
import shlex
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_WORKERS = 4
SPEED_TAG_KEY = "speed_applied"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    OK = "ok"
    SKIP = "skip"
    ERROR = "error"
    DRY_RUN = "dry-run"


@dataclass
class ProcessingResult:
    status: ProcessingStatus
    message: str


@dataclass
class ProcessingConfig:
    base_directory: Path
    recursive: bool
    workers: int
    dry_run: bool
    force: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "ProcessingConfig":
        return cls(
            base_directory=Path(args.base).expanduser().resolve(),
            recursive=args.recursive,
            workers=args.workers,
            dry_run=args.dry_run,
            force=args.force,
        )

    def validate(self) -> None:
        if not self.base_directory.exists() or not self.base_directory.is_dir():
            logger.error(f"Base path not found or not a directory: {self.base_directory}")
            raise SystemExit(2)


class CommandRunner:
    @staticmethod
    def run(cmd: List[str]) -> Tuple[int, str, str]:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr


class AudioAnalyzer:
    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner

    def probe(self, audio_path: Path) -> Optional[dict]:
        """Full ffprobe json (format + streams), or None if unavailable."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:format_tags:stream=codec_type",
            "-of", "json",
            str(audio_path),
        ]
        return_code, stdout, _ = self.command_runner.run(cmd)
        if return_code != 0:
            return None
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            return None

    def get_duration_seconds(self, data: dict) -> Optional[float]:
        try:
            duration = float(data["format"]["duration"])
            if math.isfinite(duration) and duration > 0:
                return duration
        except (KeyError, ValueError, TypeError):
            pass
        return None

    def get_speed_tag(self, data: dict) -> Optional[str]:
        tags = data.get("format", {}).get("tags", {}) if data else {}
        for key, value in tags.items():
            if key.lower() == SPEED_TAG_KEY:
                return value
        return None

    # ffmpeg's muxer always re-injects its own "encoder" tag on write, regardless of
    # -map_metadata -1 — harmless, but must be ignored or "clean" would never converge.
    IGNORED_TAGS = {SPEED_TAG_KEY, "encoder"}

    def is_already_clean(self, data: dict) -> bool:
        """True if the file has only an audio stream and no tags besides speed_applied/encoder."""
        if not data:
            return False
        streams = data.get("streams", [])
        if len(streams) != 1 or streams[0].get("codec_type") != "audio":
            return False
        tags = data.get("format", {}).get("tags", {})
        extra_keys = [k for k in tags if k.lower() not in self.IGNORED_TAGS]
        return len(extra_keys) == 0


class MetadataStripper:
    """Strips metadata/thumbnails from an MP3 in place, preserving speed_applied."""

    def __init__(self, command_runner: CommandRunner, audio_analyzer: AudioAnalyzer):
        self.command_runner = command_runner
        self.audio_analyzer = audio_analyzer

    @staticmethod
    def _temp_output_path(input_file: Path) -> Path:
        return input_file.parent / f"{input_file.stem}.stripped.tmp{input_file.suffix}"

    def _build_command(self, input_file: Path, tmp_output: Path, speed_tag: Optional[str]) -> List[str]:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(input_file),
            "-map", "0:a:0",
            "-c:a", "copy",
            "-map_metadata", "-1",
        ]
        if speed_tag is not None:
            cmd += ["-metadata", f"{SPEED_TAG_KEY}={speed_tag}"]
        cmd.append(str(tmp_output))
        return cmd

    def strip_and_replace(self, input_file: Path, dry_run: bool) -> Tuple[ProcessingStatus, str]:
        data = self.audio_analyzer.probe(input_file)
        if data is None:
            return ProcessingStatus.ERROR, f"[PROBE FAILED] {input_file.name}"

        speed_tag = self.audio_analyzer.get_speed_tag(data)
        tmp_output = self._temp_output_path(input_file)
        cmd = self._build_command(input_file, tmp_output, speed_tag)

        if dry_run:
            return ProcessingStatus.DRY_RUN, " ".join(shlex.quote(c) for c in cmd)

        return_code, _, stderr = self.command_runner.run(cmd)
        if return_code != 0:
            tmp_output.unlink(missing_ok=True)
            return ProcessingStatus.ERROR, f"[FFMPEG FAILED] {input_file.name}: {stderr}"

        original_duration = self.audio_analyzer.get_duration_seconds(data)
        new_data = self.audio_analyzer.probe(tmp_output)
        new_duration = self.audio_analyzer.get_duration_seconds(new_data) if new_data else None

        if original_duration is None or new_duration is None:
            tmp_output.unlink(missing_ok=True)
            return ProcessingStatus.ERROR, f"[VERIFY FAILED] {input_file.name}: could not read duration. Original left untouched."

        tolerance = max(1.0, original_duration * 0.005)
        if abs(new_duration - original_duration) > tolerance:
            tmp_output.unlink(missing_ok=True)
            return (
                ProcessingStatus.ERROR,
                f"[VERIFY FAILED] {input_file.name}: duration changed ({original_duration:.1f}s -> "
                f"{new_duration:.1f}s). Original left untouched.",
            )

        os.replace(tmp_output, input_file)
        tag_note = f", kept speed_applied={speed_tag}" if speed_tag else ""
        return ProcessingStatus.OK, f"[STRIPPED] {input_file.name}{tag_note}"


class FileCollector:
    @staticmethod
    def collect_mp3s(base_directory: Path, recursive: bool = False) -> List[Path]:
        if recursive:
            files = [p for p in base_directory.rglob("*.mp3") if p.is_file()]
        else:
            files = [p for p in base_directory.glob("*.mp3") if p.is_file()]
        return sorted(files)


class MetadataStripProcessor:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.command_runner = CommandRunner()
        self.audio_analyzer = AudioAnalyzer(self.command_runner)
        self.stripper = MetadataStripper(self.command_runner, self.audio_analyzer)

    def process_file(self, input_file: Path) -> ProcessingResult:
        try:
            if not self.config.force:
                data = self.audio_analyzer.probe(input_file)
                if data and self.audio_analyzer.is_already_clean(data):
                    return ProcessingResult(ProcessingStatus.SKIP, f"[ALREADY CLEAN] {input_file.name}")

            status, message = self.stripper.strip_and_replace(input_file, self.config.dry_run)
            return ProcessingResult(status, message)
        except Exception as e:
            logger.exception(f"Exception processing {input_file}")
            return ProcessingResult(ProcessingStatus.ERROR, f"[EXCEPTION] {input_file}: {e}")

    def process_all(self) -> Tuple[int, int, int]:
        files = FileCollector.collect_mp3s(self.config.base_directory, self.config.recursive)
        if not files:
            logger.info(f"No MP3 files found in {self.config.base_directory}")
            return 0, 0, 0

        logger.info(f"Found {len(files)} mp3 files in {self.config.base_directory}")
        logger.info(
            f"Recursive: {self.config.recursive} | Workers: {self.config.workers} | "
            f"Dry-run: {self.config.dry_run} | Force: {self.config.force}"
        )

        ok = skipped = errors = 0
        with futures.ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            future_to_file = {executor.submit(self.process_file, f): f for f in files}
            for future in futures.as_completed(future_to_file):
                result = future.result()
                if result.status == ProcessingStatus.OK:
                    ok += 1
                elif result.status in (ProcessingStatus.SKIP, ProcessingStatus.DRY_RUN):
                    skipped += 1
                else:
                    errors += 1
                logger.info(f"{result.status.value.upper():7} | {result.message}")

        return ok, skipped, errors


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strip metadata/thumbnails from MP3s in place, preserving speed_applied."
    )
    parser.add_argument("base", type=str, help="Directory to scan for MP3 files.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories recursively.")
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count() or DEFAULT_WORKERS,
        help="Number of parallel workers (default: CPU count).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print ffmpeg commands without executing.")
    parser.add_argument("--force", action="store_true", help="Re-process files even if already clean.")
    return parser


def print_summary(ok: int, skipped: int, errors: int) -> None:
    logger.info("\n=== SUMMARY ===")
    logger.info(f"OK: {ok} | SKIPPED: {skipped} | ERRORS: {errors}")


def main() -> None:
    parser = create_argument_parser()
    args = parser.parse_args()
    config = ProcessingConfig.from_args(args)
    config.validate()
    processor = MetadataStripProcessor(config)
    ok, skipped, errors = processor.process_all()
    print_summary(ok, skipped, errors)


if __name__ == "__main__":
    main()
