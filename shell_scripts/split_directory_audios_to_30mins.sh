#!/bin/bash
# Script to split audio files in 91_02_novels directory into 30-minute chunks
# Uses a splitter audio file between different original files

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the parent directory (scripts root)
SCRIPTS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_SCRIPT="${SCRIPTS_ROOT}/audio_processing/split_long_audios_to_smaller_ones.py"

TARGET_DIR="/Users/hamzafouad/my_workspace/personal/audios/added_21_01_2026/35_39_05__virtues_of_quran"
SPLITTER_AUDIO="/Users/hamzafouad/my_workspace/personal/audios/dont_forget_allah_minshawi.mp3"

# Optional: Specify custom output directory for split chunks
# If not set, chunks will be created in a directory named "{TARGET_DIR}__splitted"
# Uncomment and modify the line below to use a custom output directory:
# OUTPUT_DIR="/path/to/custom/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handling function
error_exit() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    error_exit "Python script not found at $PYTHON_SCRIPT"
fi

# Check if target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    error_exit "Target directory not found: $TARGET_DIR"
fi

# Check if splitter audio exists
if [ ! -f "$SPLITTER_AUDIO" ]; then
    error_exit "Splitter audio file not found: $SPLITTER_AUDIO"
fi

# Get CPU count for parallel processing
CPU_COUNT=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)

echo -e "${GREEN}Starting audio splitting process...${NC}"
echo "Target directory: $TARGET_DIR"
echo "Splitter audio: $SPLITTER_AUDIO"
echo "Workers: $CPU_COUNT"
echo ""

# Build command arguments
CMD_ARGS=(
    "$TARGET_DIR"
    --minutes 30
    --splitter-audio "$SPLITTER_AUDIO"
    --workers "$CPU_COUNT"
)

# Add output directory if specified
if [ -n "${OUTPUT_DIR:-}" ]; then
    CMD_ARGS+=(--output-dir "$OUTPUT_DIR")
    echo "Output directory: $OUTPUT_DIR"
fi

# Run the Python script with parallel processing
python3 "$PYTHON_SCRIPT" "${CMD_ARGS[@]}"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Process completed successfully!${NC}"
else
    echo -e "${RED}Process completed with errors (exit code: $EXIT_CODE)${NC}"
    exit $EXIT_CODE
fi
