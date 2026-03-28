#!/usr/bin/env bash
# Build videos for all lectures using ffmpeg.
#
# Usage:
#   ./build_all_videos.sh                    # all lectures
#   ./build_all_videos.sh ui4iot-web         # single lecture by name
#   ./build_all_videos.sh --clean            # remove intermediate clips after assembly
#   ./build_all_videos.sh --dry-run          # show what would be assembled
#
# Lectures are discovered from the content directory configured in
# lecturer.toml. Pass lecture names as arguments to override.
#
# Requires: uv, ffmpeg

set -euo pipefail

CLEAN=false
DRY_RUN=false

# Parse flags
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
CONTENT_DIR=$(uv run python -c "from lecturer.config import get_content_dir; print(get_content_dir())")

if [[ $# -gt 0 ]]; then
    LECTURES=("$@")
else
    # Use lecture order from lecturer.toml (falls back to auto-discovery)
    while IFS= read -r line; do
        LECTURES+=("$line")
    done < <(uv run python -c "from lecturer.config import list_lectures; [print(l.name) for l in list_lectures()]")
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

    cmd=(uv run python -m lecturer.build_video "$lecture")

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
