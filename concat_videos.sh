#!/usr/bin/env bash
# Concatenate all lecture videos into a single MP4, in the order
# defined in lecturer.toml.
#
# Usage:
#   ./concat_videos.sh /path/to/course                 # default output
#   ./concat_videos.sh /path/to/course -o out.mp4      # custom output
#   ./concat_videos.sh /path/to/course --dry-run       # preview only
#
# Requires: ffmpeg

set -euo pipefail

# In Docker, uv needs --project /app to find the Python package
UV="uv run"
[[ "${LECTURER_DOCKER:-}" == "1" ]] && UV="uv run --project /app"

DRY_RUN=false
OUTPUT=""

# First positional arg is the course directory
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <course-dir> [-o output.mp4] [--dry-run]" >&2
    exit 1
fi
export LECTURER_COURSE_DIR="$1"
shift

# Parse remaining flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Discover directories from config
CONTENT_DIR=$($UV python -c "from lecturer.config import get_content_dir; print(get_content_dir())")
OUTPUT_DIR=$($UV python -c "from lecturer.config import get_output_dir; print(get_output_dir())")
COURSE_NAME=$($UV python -c "from lecturer.config import load_config; print(load_config()['name'])")

# Discover lectures in order
LECTURES=()
while IFS= read -r line; do
    LECTURES+=("$line")
done < <($UV python -c "from lecturer.config import list_lectures; [print(l.name) for l in list_lectures()]")

if [[ ${#LECTURES[@]} -eq 0 ]]; then
    echo "No lectures found"
    exit 0
fi

# Collect existing video files
VIDEOS=()
for lecture in "${LECTURES[@]}"; do
    video="$CONTENT_DIR/${lecture}/${lecture}.mp4"
    if [[ -f "$video" ]]; then
        VIDEOS+=("$video")
    else
        echo "SKIP: $lecture — no ${lecture}.mp4 found"
    fi
done

if [[ ${#VIDEOS[@]} -eq 0 ]]; then
    echo "No video files found to concatenate"
    exit 1
fi

# Determine output path
if [[ -z "$OUTPUT" ]]; then
    mkdir -p "$OUTPUT_DIR"
    SAFE_NAME=$(echo "$COURSE_NAME" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
    OUTPUT="$OUTPUT_DIR/${SAFE_NAME:-lecture}.mp4"
fi

echo "Concatenating ${#VIDEOS[@]} videos:"
for v in "${VIDEOS[@]}"; do
    echo "  $(basename "$(dirname "$v")")/$(basename "$v")"
done
echo "Output: $OUTPUT"
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo "(dry run — no files created)"
    exit 0
fi

# Build ffmpeg concat file
CONCAT_LIST=$(mktemp /tmp/concat_XXXXXX.txt)
trap 'rm -f "$CONCAT_LIST"' EXIT

for v in "${VIDEOS[@]}"; do
    echo "file '$v'" >> "$CONCAT_LIST"
done

ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -fflags +genpts -c copy "$OUTPUT"

echo ""
echo "Done: $OUTPUT"
