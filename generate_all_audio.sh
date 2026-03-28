#!/usr/bin/env bash
# Generate audio for all lectures using ElevenLabs TTS.
#
# Usage:
#   export ELEVENLABS_API_KEY=sk_...
#   ./generate_all_audio.sh                  # all lectures (auto-discovered)
#   ./generate_all_audio.sh ai-agents-why    # single lecture by name
#   ./generate_all_audio.sh --force          # regenerate all, overwrite existing MP3s
#
# Lectures are discovered from the content directory configured in
# lecturer.toml. Pass lecture names as arguments to override.
#
# Requires: uv, elevenlabs Python package

set -euo pipefail

MODEL="eleven_v3"
FORCE=false

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
    echo "Error: ELEVENLABS_API_KEY is not set." >&2
    exit 1
fi

# Voice ID: from env, or from lecturer.toml, or fail
VOICE_ID="${ELEVENLABS_VOICE_ID:-$(uv run python -c "from lecturer.config import load_config; print(load_config().get('voice_id', ''))" 2>/dev/null)}"
if [[ -z "$VOICE_ID" ]]; then
    echo "Error: voice ID not set. Set ELEVENLABS_VOICE_ID or add voice_id to lecturer.toml." >&2
    exit 1
fi

# Parse flags
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
    script="$CONTENT_DIR/${lecture}/narration_script.md"

    if [[ ! -f "$script" ]]; then
        echo "SKIP: $lecture — no narration_script.md"
        continue
    fi

    echo "========================================"
    echo "Generating audio: $lecture"
    echo "========================================"

    cmd=(uv run python -m lecturer.generate_audio
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
