#!/usr/bin/env bash
# Generate PNG images and PDF for all lectures using Marp CLI.
#
# Usage:
#   ./generate_slides.sh /path/to/course       # all lectures
#   ./generate_slides.sh /path/to/course intro  # single lecture
#   ./generate_slides.sh /path/to/course --pdf-only
#
# Lectures are discovered from lecturer.toml in the course directory.
#
# Requires: marp (npm install -g @marp-team/marp-cli)

set -euo pipefail

# In Docker, uv needs --project /app to find the Python package
UV="uv run"
[[ "${LECTURER_DOCKER:-}" == "1" ]] && UV="uv run --project /app"

PDF_ONLY=false

# First positional arg is the course directory
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <course-dir> [lecture-name...] [--pdf-only]" >&2
    exit 1
fi
export LECTURER_COURSE_DIR="$1"
shift

# Parse remaining flags and lecture names
args=()
for arg in "$@"; do
    if [[ "$arg" == "--pdf-only" ]]; then
        PDF_ONLY=true
    else
        args+=("$arg")
    fi
done
set -- "${args[@]+"${args[@]}"}"

# Discover content directory and theme from config
CONTENT_DIR=$($UV python -c "from lecturer.config import get_content_dir; print(get_content_dir())")

# Use theme from course dir if available, fall back to bundled theme
if [[ -d "$LECTURER_COURSE_DIR/themes" ]]; then
    THEME="$LECTURER_COURSE_DIR/themes/graph_paper.css"
elif [[ "${LECTURER_DOCKER:-}" == "1" ]]; then
    THEME="/app/themes/graph_paper.css"
else
    THEME="themes/graph_paper.css"
fi

if [[ $# -gt 0 ]]; then
    LECTURES=("$@")
else
    while IFS= read -r line; do
        LECTURES+=("$line")
    done < <($UV python -c "from lecturer.config import list_lectures; [print(l.name) for l in list_lectures()]")
fi

if [[ ${#LECTURES[@]} -eq 0 ]]; then
    echo "No lectures with slides found in $CONTENT_DIR"
    exit 0
fi

echo "Content: $CONTENT_DIR"
echo "Lectures: ${LECTURES[*]}"
echo ""

for lecture in "${LECTURES[@]}"; do
    slides="$CONTENT_DIR/${lecture}/slides/slides.md"

    if [[ ! -f "$slides" ]]; then
        echo "SKIP: $lecture — no slides/slides.md"
        continue
    fi

    echo "========================================"
    echo "Generating slides: $lecture"
    echo "========================================"

    if [[ "$PDF_ONLY" == false ]]; then
        marp "$slides" --images png --theme-set "$THEME" --allow-local-files
    fi

    marp "$slides" --pdf --pdf-outlines --theme-set "$THEME" --allow-local-files

    echo ""
done

echo "All done."
