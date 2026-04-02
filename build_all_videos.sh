#!/usr/bin/env bash
# Build videos for all lectures using ffmpeg.
#
# Usage:
#   ./build_all_videos.sh /path/to/course              # all lectures
#   ./build_all_videos.sh /path/to/course intro         # single lecture
#   ./build_all_videos.sh /path/to/course --clean       # remove intermediate clips
#   ./build_all_videos.sh /path/to/course --dry-run     # preview only
#
# Lectures are discovered from lecturer.toml in the course directory.
#
# Requires: uv, ffmpeg

set -euo pipefail

# In Docker, uv needs --project /app to find the Python package
UV="uv run"
[[ "${LECTURER_DOCKER:-}" == "1" ]] && UV="uv run --project /app"

CLEAN=false
DRY_RUN=false

# First positional arg is the course directory
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <course-dir> [lecture-name...] [--clean] [--dry-run]" >&2
    exit 1
fi
export LECTURER_COURSE_DIR="$1"
shift

# Parse remaining flags and lecture names
args=()
for arg in "$@"; do
    if [[ "$arg" == "--clean" ]]; then
        CLEAN=true
    elif [[ "$arg" == "--dry-run" ]]; then
        DRY_RUN=true
    else
        args+=("$arg")
    fi
done
set -- "${args[@]+"${args[@]}"}"

# Discover content directory from config
CONTENT_DIR=$($UV python -c "from lecturer.config import get_content_dir; print(get_content_dir())")

if [[ $# -gt 0 ]]; then
    LECTURES=("$@")
else
    while IFS= read -r line; do
        LECTURES+=("$line")
    done < <($UV python -c "from lecturer.config import list_lectures; [print(l.name) for l in list_lectures()]")
fi

if [[ ${#LECTURES[@]} -eq 0 ]]; then
    echo "No lectures found in $CONTENT_DIR"
    exit 0
fi

echo "Content: $CONTENT_DIR"
echo "Lectures: ${LECTURES[*]}"
echo ""

for lecture in "${LECTURES[@]}"; do
    lecture_dir="$CONTENT_DIR/${lecture}"

    if [[ ! -d "$lecture_dir" ]]; then
        echo "SKIP: $lecture — directory not found"
        continue
    fi

    echo "========================================"
    echo "Building video: $lecture"
    echo "========================================"

    # shellcheck disable=SC2086
    cmd=($UV python -m lecturer.build_video "$lecture")

    if [[ "$DRY_RUN" == true ]]; then
        cmd+=(--dry-run)
    fi

    if [[ "$CLEAN" == true ]]; then
        cmd+=(--clean)
    fi

    "${cmd[@]}"

    echo ""
done

echo "All done."
