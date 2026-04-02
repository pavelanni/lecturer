#!/usr/bin/env bash
# Generate audio for all lectures using ElevenLabs TTS.
#
# Usage:
#   export ELEVENLABS_API_KEY=sk_...
#   ./generate_all_audio.sh /path/to/course           # all lectures
#   ./generate_all_audio.sh /path/to/course intro      # single lecture
#   ./generate_all_audio.sh /path/to/course --force    # regenerate existing MP3s
#
# Lectures are discovered from lecturer.toml in the course directory.
#
# Requires: uv, elevenlabs Python package

set -euo pipefail

# In Docker, uv needs --project /app to find the Python package
UV="uv run"
[[ "${LECTURER_DOCKER:-}" == "1" ]] && UV="uv run --project /app"

MODEL="eleven_v3"
FORCE=false

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
    echo "Error: ELEVENLABS_API_KEY is not set." >&2
    exit 1
fi

# First positional arg is the course directory
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <course-dir> [lecture-name...] [--force]" >&2
    exit 1
fi
export LECTURER_COURSE_DIR="$1"
shift

# Voice ID: from env, or from lecturer.toml, or fail
VOICE_ID="${ELEVENLABS_VOICE_ID:-$($UV python -c "from lecturer.config import load_config; print(load_config().get('voice_id', ''))" 2>/dev/null)}"
if [[ -z "$VOICE_ID" ]]; then
    echo "Error: voice ID not set. Set ELEVENLABS_VOICE_ID or add voice_id to lecturer.toml." >&2
    exit 1
fi

# Parse remaining flags and lecture names
args=()
for arg in "$@"; do
    if [[ "$arg" == "--force" ]]; then
        FORCE=true
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
    script="$CONTENT_DIR/${lecture}/narration_script.md"

    if [[ ! -f "$script" ]]; then
        echo "SKIP: $lecture — no narration_script.md"
        continue
    fi

    echo "========================================"
    echo "Generating audio: $lecture"
    echo "========================================"

    # shellcheck disable=SC2086
    cmd=($UV python -m lecturer.generate_audio
        "$script"
        --voice-id "$VOICE_ID"
        --model "$MODEL")

    if [[ "$FORCE" == true ]]; then
        cmd+=(--force)
    fi

    "${cmd[@]}"

    echo ""
done

echo "All done."
