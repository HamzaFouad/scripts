#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split long MP3s into 30-minute chunks, preserving numeric prefixes.

Naming rule (examples):
- Input : 02_01_04_How long does it take to learn to speak English fluently？.mp3
- Output: 02_01_04__01_How long does it take to learn to speak English fluently？.mp3
         02_01_04__02_How long does it take to learn to speak English fluently？.mp3
         ...

Files that don't start with a numeric prefix (any naming at all) are also split, using
the full original filename with a "__NN" suffix instead:
- Input : Some Arbitrary Title.mp3
- Output: Some Arbitrary Title__01.mp3
         Some Arbitrary Title__02.mp3
         ...

Processes files in parallel to maintain order and (optionally) add a splitter audio file
between different originals.

Usage:
  python split_long_audios_to_smaller_ones.py /path/to/directory --minutes 30
  python split_long_audios_to_smaller_ones.py /path/to/directory --splitter-audio /path/to/splitter.mp3
  python split_long_audios_to_smaller_ones.py /path/to/directory --output-dir /path/to/output
  python split_long_audios_to_smaller_ones.py /path/to/directory --delete-original
  python split_long_audios_to_smaller_ones.py . --dry-run

Output Location:
- By default, split chunks are created in place, alongside the original files.
- Use --output-dir to write chunks to a different directory instead.

Notes:
- Requires: ffmpeg, ffprobe
- Skips files that already look like split parts (contain "__<number>" after the stem).
- If --splitter-audio is given, that audio file is copied in after each original file that
  was split, to visually/audibly separate chunks. Without it, no splitter is created.
- Use --delete-original to remove the source file once its chunks are verified (duration
  match). Irreversible; never happens on a dry run.
"""

import argparse
import concurrent.futures as futures
import json
import logging
import math
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Constants
DEFAULT_CHUNK_MINUTES = 30
DEFAULT_WORKERS = 4
SPLITTER_NUMBER = 999  # Used to ensure splitter files sort after all chunks

# Regex patterns
PREFIX_PATTERN = re.compile(r"^(\d+(?:_\d+)*)(_.+)$", flags=re.UNICODE)
# Already-split chunk produced from a numeric-prefixed original, e.g. "02_01__01_Title"
ALREADY_SPLIT_PATTERN = re.compile(r"^(\d+(?:_\d+)*)__\d{1,3}_.+$", flags=re.UNICODE)
# Already-split chunk produced from a non-prefixed original, e.g. "Some Title__01"
ALREADY_SPLIT_FALLBACK_PATTERN = re.compile(r"^.+__\d{1,3}$", flags=re.UNICODE)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of file processing."""
    OK = "ok"
    SKIP = "skip"
    ERROR = "error"
    DRY_RUN = "dry-run"


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    status: ProcessingStatus
    message: str
    output_pattern: Optional[Path]
    input_file: Path

    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.OK

    @property
    def should_create_splitter(self) -> bool:
        """Check if splitter file should be created."""
        return self.status in (ProcessingStatus.OK, ProcessingStatus.DRY_RUN) and self.output_pattern is not None


@dataclass
class ProcessingConfig:
    """Configuration for audio splitting."""
    base_directory: Path
    output_directory: Path
    chunk_minutes: int
    recursive: bool
    splitter_audio: Optional[Path]
    workers: int
    dry_run: bool
    overwrite: bool
    delete_original: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "ProcessingConfig":
        """Create configuration from command line arguments."""
        base = Path(args.base).expanduser().resolve()
        splitter = None
        if args.splitter_audio:
            splitter = Path(args.splitter_audio).expanduser().resolve()
        
        # Default output directory is the base directory itself (chunks land in place,
        # alongside the originals).
        if args.output_dir:
            output_dir = Path(args.output_dir).expanduser().resolve()
        else:
            output_dir = base

        return cls(
            base_directory=base,
            output_directory=output_dir,
            chunk_minutes=args.minutes,
            recursive=args.recursive,
            splitter_audio=splitter,
            workers=args.workers,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            delete_original=args.delete_original,
        )

    def validate(self) -> None:
        """Validate configuration and raise SystemExit if invalid."""
        if not self.base_directory.exists() or not self.base_directory.is_dir():
            logger.error(f"Base path not found or not a directory: {self.base_directory}")
            raise SystemExit(2)

        if self.splitter_audio and (not self.splitter_audio.exists() or not self.splitter_audio.is_file()):
            logger.error(f"Splitter audio file not found: {self.splitter_audio}")
            raise SystemExit(2)
        
        # Create output directory if it doesn't exist yet (skip on dry runs, which
        # must not have side effects).
        if self.dry_run:
            return
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.error(f"Cannot create output directory {self.output_directory}: {e}")
            raise SystemExit(2)


class CommandRunner:
    """Handles execution of shell commands."""

    @staticmethod
    def run(cmd: str) -> Tuple[int, str, str]:
        """
        Run a shell command and return return code, stdout, and stderr.

        Args:
            cmd: Command string to execute

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        proc = subprocess.Popen(
            shlex.split(cmd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr


class AudioAnalyzer:
    """Handles audio file analysis using ffprobe."""

    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner

    def get_duration_seconds(self, audio_path: Path) -> Optional[float]:
        """
        Get audio file duration in seconds using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds, or None if unavailable
        """
        cmd = (
            f'ffprobe -v error -show_entries format=duration -of json '
            f'{shlex.quote(str(audio_path))}'
        )
        return_code, stdout, _ = self.command_runner.run(cmd)

        if return_code != 0:
            return None

        try:
            data = json.loads(stdout)
            duration = float(data["format"]["duration"])
            if math.isfinite(duration) and duration > 0:
                return duration
        except (KeyError, ValueError, TypeError) as e:
            logger.debug(f"Failed to parse duration for {audio_path}: {e}")

        return None


class FilenameParser:
    """Handles parsing and validation of audio filenames."""

    @staticmethod
    def is_already_split(filename_stem: str) -> bool:
        """
        Check if filename indicates it's already a split chunk.

        Args:
            filename_stem: Filename without extension

        Returns:
            True if filename matches already-split pattern
        """
        return bool(ALREADY_SPLIT_PATTERN.match(filename_stem)) or bool(
            ALREADY_SPLIT_FALLBACK_PATTERN.match(filename_stem)
        )

    @staticmethod
    def extract_prefix_and_title(filename_stem: str) -> Optional[Tuple[str, str]]:
        """
        Extract numeric prefix and title from filename.

        Args:
            filename_stem: Filename without extension

        Returns:
            Tuple of (numeric_prefix, title_part) or None if pattern doesn't match
        """
        match = PREFIX_PATTERN.match(filename_stem)
        if not match:
            return None
        return match.group(1), match.group(2)

    @staticmethod
    def compute_output_pattern(input_file: Path, output_directory: Path) -> str:
        """
        Build ffmpeg segment output pattern for splitting.

        Files with a numeric prefix (e.g. "02_01_Title.mp3") keep that prefix and have
        "__NN" inserted before the title. Any other naming falls back to using the full
        original filename with "__NN" appended, so every filename can be split.

        Args:
            input_file: Input audio file path
            output_directory: Output directory for split chunks.

        Returns:
            Output pattern string for ffmpeg.
        """
        stem = input_file.stem
        parsed = FilenameParser.extract_prefix_and_title(stem)
        if parsed:
            numeric_prefix, title_part = parsed
            pattern_name = f"{numeric_prefix}__%02d{title_part}.mp3"
        else:
            pattern_name = f"{stem}__%02d.mp3"
        return str(output_directory / pattern_name)


class FFmpegSplitter:
    """Handles audio splitting using ffmpeg."""

    def __init__(self, command_runner: CommandRunner, audio_analyzer: AudioAnalyzer, output_directory: Path):
        self.command_runner = command_runner
        self.audio_analyzer = audio_analyzer
        self.output_directory = output_directory

    def split(
        self,
        input_file: Path,
        chunk_minutes: int,
        dry_run: bool = False,
        overwrite: bool = False,
    ) -> Tuple[ProcessingStatus, str, Optional[Path]]:
        """
        Split audio file into chunks.

        Args:
            input_file: Path to input audio file
            chunk_minutes: Length of each chunk in minutes
            dry_run: If True, only print commands without executing
            overwrite: If True, overwrite existing chunks

        Returns:
            Tuple of (status, message, output_pattern_path)
        """
        # Validate duration
        duration = self.audio_analyzer.get_duration_seconds(input_file)
        if duration is None:
            return (
                ProcessingStatus.SKIP,
                f"[NO DURATION] {input_file.name}",
                None,
            )

        chunk_seconds = chunk_minutes * 60
        if duration <= chunk_seconds + 1:  # Small tolerance
            return (
                ProcessingStatus.SKIP,
                f"[<= {chunk_minutes} min] {input_file.name}",
                None,
            )

        # Skip already-split files
        if FilenameParser.is_already_split(input_file.stem):
            return (
                ProcessingStatus.SKIP,
                f"[ALREADY SPLIT NAME] {input_file.name}",
                None,
            )

        # Compute output pattern
        output_pattern = FilenameParser.compute_output_pattern(input_file, self.output_directory)

        # Check if chunks already exist
        if not overwrite and self._chunks_exist(output_pattern):
            expected_first = Path(output_pattern.replace("%02d", "01")).name
            return (
                ProcessingStatus.SKIP,
                f"[EXISTS] {expected_first} ... (set --overwrite to re-split)",
                None,
            )

        if dry_run:
            cmd = self._build_command(input_file, chunk_seconds, output_pattern)
            return ProcessingStatus.DRY_RUN, cmd, Path(output_pattern)

        # Try stream copy first (faster)
        status, message = self._split_with_copy(input_file, chunk_seconds, output_pattern)
        if status == ProcessingStatus.OK:
            return status, message, Path(output_pattern)

        # Fallback to re-encoding if copy fails
        return self._split_with_reencode(input_file, chunk_seconds, output_pattern)

    def _chunks_exist(self, output_pattern: str) -> bool:
        """Check if output chunks already exist."""
        pattern_path = Path(output_pattern)
        expected_first = pattern_path.parent / pattern_path.name.replace("%02d", "01")
        return expected_first.exists()

    def _build_command(
        self, input_file: Path, chunk_seconds: int, output_pattern: str, reencode: bool = False
    ) -> str:
        """Build ffmpeg command for splitting."""
        base_cmd = (
            f'ffmpeg -hide_banner -loglevel error '
            f'-i {shlex.quote(str(input_file))} '
            f'-f segment -segment_time {chunk_seconds} '
            f'-reset_timestamps 1 -segment_start_number 1 '
        )

        if reencode:
            cmd = (
                f'{base_cmd}'
                f'-c:a libmp3lame -b:a 192k -map 0:a:0 '
                f'{shlex.quote(output_pattern)}'
            )
        else:
            cmd = (
                f'{base_cmd}'
                f'-c copy -map 0 '
                f'{shlex.quote(output_pattern)}'
            )

        return cmd

    def _split_with_copy(
        self, input_file: Path, chunk_seconds: int, output_pattern: str
    ) -> Tuple[ProcessingStatus, str]:
        """Split using stream copy (fast, no re-encoding)."""
        cmd = self._build_command(input_file, chunk_seconds, output_pattern, reencode=False)
        return_code, _, stderr = self.command_runner.run(cmd)

        if return_code == 0:
            pattern_name = Path(output_pattern).name.replace("%02d", "01..")
            return ProcessingStatus.OK, f"[SPLIT] {input_file.name} -> {pattern_name}"

        return ProcessingStatus.ERROR, f"[COPY FAILED] {input_file.name}: {stderr}"

    def _split_with_reencode(
        self, input_file: Path, chunk_seconds: int, output_pattern: str
    ) -> Tuple[ProcessingStatus, str, Optional[Path]]:
        """Split using re-encoding (fallback when copy fails)."""
        cmd = self._build_command(input_file, chunk_seconds, output_pattern, reencode=True)
        return_code, _, stderr = self.command_runner.run(cmd)

        if return_code == 0:
            pattern_name = Path(output_pattern).name.replace("%02d", "01..")
            return (
                ProcessingStatus.OK,
                f"[RE-ENCODED] {input_file.name} -> {pattern_name}",
                Path(output_pattern),
            )

        return (
            ProcessingStatus.ERROR,
            f"[FFMPEG FAIL] {input_file.name}: {stderr}",
            None,
        )


class SplitterFileManager:
    """Manages creation of splitter files between different original files."""

    @staticmethod
    def create(
        directory: Path,
        original_filename: str,
        splitter_audio: Optional[Path] = None,
        dry_run: bool = False,
    ) -> None:
        """
        Create a splitter file after processing an original file.

        Args:
            directory: Directory where splitter file should be created
            original_filename: Name of the original file that was split
            splitter_audio: Audio file to copy as splitter. If not given, no splitter
                is created (there's no use in a silent, unplayable marker file).
            dry_run: If True, only print what would be done
        """
        if not splitter_audio:
            return

        splitter_path = SplitterFileManager._generate_splitter_path(
            directory, original_filename, splitter_audio
        )

        if dry_run:
            logger.info(f"  [DRY-RUN] Would copy splitter audio: {splitter_path}")
            return

        try:
            shutil.copy2(splitter_audio, splitter_path)
        except (OSError, IOError) as e:
            logger.warning(f"Could not create splitter file {splitter_path}: {e}")

    @staticmethod
    def _generate_splitter_path(
        directory: Path, original_filename: str, splitter_audio: Path
    ) -> Path:
        """Generate path for splitter file."""
        stem = Path(original_filename).stem
        parsed = FilenameParser.extract_prefix_and_title(stem)

        suffix = splitter_audio.suffix
        if parsed:
            numeric_prefix, _ = parsed
            splitter_name = f"{numeric_prefix}__{SPLITTER_NUMBER}_SPLITTER{suffix}"
        else:
            # Fallback for non-prefixed filenames. Use the same "__NNN_SPLITTER" suffix
            # style as the prefixed case so it sorts after "{stem}__01.mp3", "__02.mp3", etc.
            splitter_name = f"{stem}__{SPLITTER_NUMBER}_SPLITTER{suffix}"

        return directory / splitter_name


class FileCollector:
    """Collects audio files from directories."""

    @staticmethod
    def collect_mp3s(base_directory: Path, recursive: bool = False) -> List[Path]:
        """
        Collect MP3 files from directory.

        Args:
            base_directory: Base directory to search
            recursive: If True, search subdirectories recursively

        Returns:
            Sorted list of MP3 file paths
        """
        if recursive:
            files = [p for p in base_directory.rglob("*.mp3") if p.is_file()]
        else:
            files = [p for p in base_directory.glob("*.mp3") if p.is_file()]

        return sorted(files)


class AudioSplitterProcessor:
    """Main processor for splitting audio files."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.command_runner = CommandRunner()
        self.audio_analyzer = AudioAnalyzer(self.command_runner)
        self.ffmpeg_splitter = FFmpegSplitter(
            self.command_runner, 
            self.audio_analyzer, 
            self.config.output_directory
        )

    def process_file(self, input_file: Path) -> ProcessingResult:
        """
        Process a single audio file.

        Args:
            input_file: Path to audio file to process

        Returns:
            ProcessingResult with status and details
        """
        try:
            status, message, output_pattern = self.ffmpeg_splitter.split(
                input_file,
                self.config.chunk_minutes,
                self.config.dry_run,
                self.config.overwrite,
            )

            result = ProcessingResult(
                status=status,
                message=message,
                output_pattern=output_pattern,
                input_file=input_file,
            )

            # Create splitter file if needed
            if result.should_create_splitter:
                SplitterFileManager.create(
                    self.config.output_directory,
                    input_file.name,
                    self.config.splitter_audio,
                    self.config.dry_run,
                )

            if (
                self.config.delete_original
                and not self.config.dry_run
                and result.status == ProcessingStatus.OK
                and result.output_pattern is not None
            ):
                self._verify_and_delete_original(input_file, result.output_pattern)

            return result

        except Exception as e:
            logger.exception(f"Exception processing {input_file}")
            return ProcessingResult(
                status=ProcessingStatus.ERROR,
                message=f"[EXCEPTION] {input_file}: {e}",
                output_pattern=None,
                input_file=input_file,
            )

    def _find_chunk_files(self, output_pattern: Path) -> List[Path]:
        """
        Find the chunk files actually produced for an ffmpeg segment output pattern
        (which contains a literal "%02d" placeholder for the segment number).
        """
        directory = output_pattern.parent
        prefix, _, rest = output_pattern.name.partition("%02d")
        if not directory.exists():
            return []

        matches = []
        for f in directory.iterdir():
            name = f.name
            if f.is_file() and name.startswith(prefix) and name.endswith(rest):
                middle = name[len(prefix): len(name) - len(rest)]
                if middle.isdigit():
                    matches.append(f)
        return sorted(matches)

    def _verify_and_delete_original(self, input_file: Path, output_pattern: Path) -> None:
        """
        Delete the original file, but only after verifying its chunks exist and their
        total duration closely matches the original's duration.
        """
        chunk_files = self._find_chunk_files(output_pattern)
        if len(chunk_files) < 2:
            logger.warning(
                f"[VERIFY FAILED] {input_file.name}: expected multiple chunks, found "
                f"{len(chunk_files)}. Keeping original."
            )
            return

        original_duration = self.audio_analyzer.get_duration_seconds(input_file)
        chunk_durations = [self.audio_analyzer.get_duration_seconds(c) for c in chunk_files]
        if original_duration is None or any(d is None for d in chunk_durations):
            logger.warning(
                f"[VERIFY FAILED] {input_file.name}: could not read duration of original "
                f"or one of its chunks. Keeping original."
            )
            return

        chunks_duration = sum(chunk_durations)
        tolerance = max(5.0, original_duration * 0.01)
        if abs(chunks_duration - original_duration) > tolerance:
            logger.warning(
                f"[VERIFY FAILED] {input_file.name}: original={original_duration:.1f}s "
                f"chunks={chunks_duration:.1f}s (diff exceeds {tolerance:.1f}s tolerance). "
                f"Keeping original."
            )
            return

        try:
            input_file.unlink()
            logger.info(
                f"[DELETED ORIGINAL] {input_file.name} (verified {len(chunk_files)} chunks, "
                f"{chunks_duration:.1f}s ≈ {original_duration:.1f}s)"
            )
        except OSError as e:
            logger.warning(f"Could not delete original {input_file}: {e}")

    def process_all(self) -> Tuple[int, int, int]:
        """
        Process all audio files in the configured directory.

        Returns:
            Tuple of (ok_count, skipped_count, error_count)
        """
        files = FileCollector.collect_mp3s(
            self.config.base_directory, self.config.recursive
        )

        if not files:
            logger.info(f"No MP3 files found in {self.config.base_directory}")
            return 0, 0, 0

        logger.info(f"Found {len(files)} mp3 files in {self.config.base_directory}")
        self._log_configuration()

        if self.config.workers > 1:
            return self._process_parallel(files)
        else:
            return self._process_sequential(files)

    def _log_configuration(self) -> None:
        """Log processing configuration."""
        config_info = (
            f"Minutes per chunk: {self.config.chunk_minutes} | "
            f"Output directory: {self.config.output_directory} | "
            f"Recursive: {self.config.recursive} | "
            f"Workers: {self.config.workers} | "
            f"Dry-run: {self.config.dry_run} | "
            f"Overwrite: {self.config.overwrite} | "
            f"Delete original: {self.config.delete_original}"
        )
        logger.info(config_info)

        if self.config.workers > 1:
            logger.info(f"Processing files in parallel with {self.config.workers} workers...\n")
        else:
            logger.info("Processing files sequentially...\n")

    def _process_parallel(self, files: List[Path]) -> Tuple[int, int, int]:
        """Process files in parallel."""
        ok = skipped = errors = 0

        with futures.ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            future_to_file = {
                executor.submit(self.process_file, file): file for file in files
            }

            for future in futures.as_completed(future_to_file):
                result = future.result()
                ok, skipped, errors = self._update_counts(result, ok, skipped, errors)
                logger.info(f"{result.status.value.upper():7} | {result.message}")

        return ok, skipped, errors

    def _process_sequential(self, files: List[Path]) -> Tuple[int, int, int]:
        """Process files sequentially."""
        ok = skipped = errors = 0

        for file in files:
            result = self.process_file(file)
            ok, skipped, errors = self._update_counts(result, ok, skipped, errors)
            logger.info(f"{result.status.value.upper():7} | {result.message}")

        return ok, skipped, errors

    @staticmethod
    def _update_counts(
        result: ProcessingResult, ok: int, skipped: int, errors: int
    ) -> Tuple[int, int, int]:
        """Update processing counts based on result."""
        if result.status == ProcessingStatus.OK:
            ok += 1
        elif result.status in (ProcessingStatus.SKIP, ProcessingStatus.DRY_RUN):
            skipped += 1
        else:
            errors += 1
        return ok, skipped, errors


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Split MP3s longer than N minutes into chunks, preserving numeric prefixes. "
            "Processes files in parallel to maintain order and add splitter files between different originals."
        )
    )
    parser.add_argument(
        "base",
        type=str,
        help="Directory to scan for MP3 files.",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=DEFAULT_CHUNK_MINUTES,
        help=f"Chunk length in minutes (default: {DEFAULT_CHUNK_MINUTES}).",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Scan subdirectories recursively.",
    )
    parser.add_argument(
        "--splitter-audio",
        type=str,
        help="Path to audio file to use as splitter between different originals.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for split chunks. If not specified, chunks are written in place, alongside the originals.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or DEFAULT_WORKERS,
        help="Number of parallel workers (default: CPU count).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the actions/ffmpeg commands without executing.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing split parts if present.",
    )
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help=(
            "Delete the original file after splitting, but only once its chunks are "
            "verified to exist and their total duration matches the original. "
            "Irreversible. Never deletes on a dry run."
        ),
    )
    return parser


def print_summary(ok: int, skipped: int, errors: int, splitter_audio: Optional[Path]) -> None:
    """Print processing summary."""
    logger.info("\n=== SUMMARY ===")
    logger.info(f"OK: {ok} | SKIPPED: {skipped} | ERRORS: {errors}")

    if ok > 0 and splitter_audio:
        logger.info(
            "Splitter audio files have been copied after each split file to visually separate chunks."
        )


def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    config = ProcessingConfig.from_args(args)
    config.validate()

    if config.splitter_audio:
        logger.info(f"Using splitter audio: {config.splitter_audio}")

    processor = AudioSplitterProcessor(config)
    ok, skipped, errors = processor.process_all()

    print_summary(ok, skipped, errors, config.splitter_audio)


if __name__ == "__main__":
    main()
