#!/bin/bash
# Split audios into 30-minute chunks for every subdirectory of a parent directory.
#
# Runs the python splitter once per subdirectory (NOT with --recursive), so each
# chunk is written next to its own original file instead of all landing in the parent.
#
# Usage:
#   ./split_subdirs_audios_to_30mins.sh /path/to/parent [--dry-run] [--delete-original]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_SCRIPT="${SCRIPTS_ROOT}/audio_processing/split_long_audios_to_smaller_ones.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error_exit() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

PARENT_DIR="${1:-}"
[ -n "$PARENT_DIR" ] || error_exit "Usage: $0 /path/to/parent [extra args passed to the python script]"
shift
EXTRA_ARGS=("$@")

[ -f "$PYTHON_SCRIPT" ] || error_exit "Python script not found at $PYTHON_SCRIPT"
[ -d "$PARENT_DIR" ] || error_exit "Parent directory not found: $PARENT_DIR"

CPU_COUNT=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)

echo -e "${GREEN}Splitting audios per subdirectory${NC}"
echo "Parent directory: $PARENT_DIR"
echo "Workers: $CPU_COUNT"
[ ${#EXTRA_ARGS[@]} -gt 0 ] && echo "Extra args: ${EXTRA_ARGS[*]}"
echo ""

FAILED=0
for SUBDIR in "$PARENT_DIR"/*/; do
    [ -d "$SUBDIR" ] || continue
    SUBDIR="${SUBDIR%/}"
    echo -e "${YELLOW}=== $(basename "$SUBDIR") ===${NC}"
    if ! python3 "$PYTHON_SCRIPT" "$SUBDIR" \
        --minutes 30 \
        --workers "$CPU_COUNT" \
        "${EXTRA_ARGS[@]}"; then
        echo -e "${RED}Failed on: $SUBDIR${NC}" >&2
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All subdirectories processed successfully!${NC}"
else
    echo -e "${RED}Completed with $FAILED failing subdirectories${NC}" >&2
    exit 1
fi
