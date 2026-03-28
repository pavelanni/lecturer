#!/usr/bin/env bash
# Generate PNG images and PDF for all lectures using Marp CLI.
#
# Usage:
#   ./generate_slides.sh                    # all lectures
#   ./generate_slides.sh ai-agents-why      # single lecture
#   ./generate_slides.sh --pdf-only         # skip PNGs, generate PDFs only
#
# Lectures are discovered from the content directory configured in
# lecturer.toml.
#
# Requires: marp (npm install -g @marp-team/marp-cli)

set -euo pipefail

THEME="themes/graph_paper.css"
PDF_ONLY=false

# Parse flags
args=()
for arg in "$@"; do
    if [[ "$arg" == "--pdf-only" ]]; then
        PDF_ONLY=true
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
