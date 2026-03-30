#!/usr/bin/env bash
# Entrypoint for the Lecturer Docker container.
#
# Routes subcommands to the appropriate tool. Runs from /course
# (the mounted course directory).
set -euo pipefail

APP_DIR="/app"

# Ensure lecturer.toml exists in the mounted volume
check_config() {
    if [[ ! -f "lecturer.toml" ]]; then
        echo "Error: lecturer.toml not found in the mounted directory." >&2
        echo "" >&2
        echo "Make sure you mount your course directory:" >&2
        echo "  docker run -v /path/to/my-course:/course lecturer <command>" >&2
        echo "" >&2
        echo "Your course directory should contain lecturer.toml." >&2
        echo "See lecturer.toml.example in the repo for the format." >&2
        exit 1
    fi
}

# Copy default theme if the course doesn't have its own
ensure_themes() {
    if [[ ! -d "themes" ]]; then
        cp -r "$APP_DIR/themes" .
    fi
}

case "${1:-help}" in
    generate-slides)
        check_config
        ensure_themes
        shift
        exec "$APP_DIR/generate_slides.sh" "$@"
        ;;
    generate-audio)
        check_config
        if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
            echo "Error: ELEVENLABS_API_KEY not set." >&2
            echo "  docker run -e ELEVENLABS_API_KEY=sk_... lecturer generate-audio" >&2
            exit 1
        fi
        shift
        exec "$APP_DIR/generate_all_audio.sh" "$@"
        ;;
    build-videos)
        check_config
        shift
        exec "$APP_DIR/build_all_videos.sh" "$@"
        ;;
    concat)
        check_config
        shift
        exec "$APP_DIR/concat_videos.sh" "$@"
        ;;
    transcribe)
        shift
        exec uv run --project "$APP_DIR" python -m lecturer.transcribe "$@"
        ;;
    concat-pdf)
        check_config
        shift
        exec uv run --project "$APP_DIR" python -m lecturer.concat_pdf "$@"
        ;;
    shell)
        exec /bin/bash
        ;;
    help|--help|-h)
        cat <<'HELP'
Lecturer — video lecture generation toolkit

Usage:
  docker run -v ./my-course:/course lecturer <command> [options]

Commands:
  generate-slides    Export slides to PNG + PDF via Marp
  generate-audio     Generate MP3 narration via ElevenLabs TTS
  build-videos       Assemble per-lecture MP4 videos
  concat             Concatenate all videos into one MP4
  concat-pdf         Merge all slide PDFs into one handout
  transcribe         Transcribe a recording with Whisper
  shell              Open a bash shell in the container
  help               Show this help message

Examples:
  # Generate slide images
  docker run -v ./my-course:/course lecturer generate-slides

  # Generate audio (requires API key)
  docker run -v ./my-course:/course \
      -e ELEVENLABS_API_KEY=sk_... \
      lecturer generate-audio

  # Build all videos with 1-second pause between slides
  docker run -v ./my-course:/course lecturer build-videos --pause 1.0

  # Full pipeline
  docker run -v ./my-course:/course lecturer generate-slides
  docker run -v ./my-course:/course -e ELEVENLABS_API_KEY=sk_... lecturer generate-audio
  docker run -v ./my-course:/course lecturer build-videos --clean
  docker run -v ./my-course:/course lecturer concat

Environment variables:
  ELEVENLABS_API_KEY     Required for generate-audio
  ELEVENLABS_VOICE_ID    Voice ID (overrides lecturer.toml)
HELP
        ;;
    *)
        echo "Unknown command: $1" >&2
        echo "Run 'docker run lecturer help' for usage." >&2
        exit 1
        ;;
esac
