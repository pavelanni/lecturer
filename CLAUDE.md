# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when
working with code in this repository.

## Project overview

A Python-based pipeline for generating short video lectures from slide
content, using the instructor's cloned voice. The pipeline is designed
to be course-agnostic — configure your course in `lecturer.toml`.

Pipeline stages: slides (PNG) -> narration script (Claude) -> audio
(ElevenLabs TTS) -> video (ffmpeg)

## Development setup

- Python 3.12, managed with `uv`
- Install dependencies: `uv sync`
- Key dependencies: `faster-whisper`, `mlx-whisper` (Apple Silicon),
  `elevenlabs` (optional `tts` extra: `uv sync --extra tts`)

## Key commands

| Step | Tool | Command |
|---|---|---|
| Generate slide PNGs | Marp CLI | `./generate_slides.sh` |
| Generate audio | ElevenLabs | `./generate_all_audio.sh` |
| Build all videos | ffmpeg | `./build_all_videos.sh` |
| Concatenate videos | ffmpeg | `./concat_videos.sh` |
| Transcribe recording | Whisper | `uv run python -m lecturer.transcribe recording.webm` |

## Architecture notes

- Code lives in `src/lecturer/` as a Python package; scripts are
  invoked via `uv run python -m lecturer.<module>`
- `transcribe.py` auto-detects platform: uses `mlx-whisper` (Metal
  GPU) on Apple Silicon, `faster-whisper` (CPU) elsewhere
- `generate_audio.py` parses Markdown narration scripts by heading
  pattern `## Slide N` or `## Слайд N`, splits into per-slide
  segments, calls ElevenLabs TTS API
- Generated audio files skip existing files to allow partial re-runs
  (use `--force` to regenerate)
- `build_video.py` assembles per-slide clips (PNG + MP3) via ffmpeg,
  then concatenates into a single MP4; uses 5fps for timing accuracy
  with still images; adds a configurable pause before each slide's
  narration (`--pause`, default 0.8s); intermediate clips cached in
  `.clips/` (use `--clean` to remove)
- `content/` holds lecture artifacts — one subdirectory per lecture,
  flat layout with prefix-based naming; slides live in
  `content/<lecture>/slides/`, narration scripts at
  `content/<lecture>/narration_script.md`
- Narration scripts are generated using the `lecture-script` skill
  (`.claude/skills/lecture-script/`)
- Lecture slides are generated using the `lecture-slides` skill
  (`.claude/skills/lecture-slides/`); Marp theme at
  `themes/graph_paper.css`

## Configuration

Course-specific paths and voice ID are configured in `lecturer.toml`
(gitignored, copy from `lecturer.toml.example`). Scripts accept either
full paths or lecture names resolved via config.

## Environment variables

- `ELEVENLABS_API_KEY` — required for audio generation
- `ELEVENLABS_VOICE_ID` — voice ID (overrides `voice_id` in
  `lecturer.toml`)

## Narration script format

Scripts follow a specific Markdown heading convention that
`generate_audio.py` parses:

```markdown
## Slide 1 — Title
Narration text for slide 1...

## Slide 2 — Title
Narration text for slide 2...
```

Headings must match: `## Slide N` or `## Слайд N` (case-sensitive).
The language of the heading prefix should match the lecture language.
