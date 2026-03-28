#!/usr/bin/env python3
"""Generate per-slide MP3 audio files from a narration script using ElevenLabs.

Reads a Markdown narration script (as produced by Claude), splits it into
per-slide segments, and calls the ElevenLabs TTS API for each one.

Output files are named slide_01.mp3, slide_02.mp3, … and are ready to be
combined with PNG slide exports by the video assembly step.

Install:
    pip install elevenlabs

Usage:
    python generate_audio.py <script.md> --voice-id <id> [options]

Examples:
    # Dry run — show what would be generated, no API calls
    python generate_audio.py ai4docs_narration_script.md --dry-run

    # Generate all slides
    python generate_audio.py ai4docs_narration_script.md --voice-id abc123

    # Generate only slides 3–5 (useful for testing or re-runs)
    python generate_audio.py ai4docs_narration_script.md --voice-id abc123 --slides 3-5

    # List voice IDs available on your account
    python generate_audio.py --list-voices

Finding your voice ID:
    Run with --list-voices, or go to ElevenLabs → Voices → click your voice
    → the ID is in the URL: elevenlabs.io/app/voice-lab/edit/<voice-id>

Environment:
    ELEVENLABS_API_KEY  — your API key (required, or use --api-key)
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path


# ── slide parsing ─────────────────────────────────────────────────────────────

def parse_slides(script_path: Path) -> list[dict]:
    """Parse narration script into a list of slide dicts with number and text."""
    text = script_path.read_text(encoding="utf-8")

    # Match headings like: ## Слайд 1 — Title  or  ## Slide 01 — Title
    # Capture everything up to the next ## heading or end of file
    pattern = re.compile(
        r"^##\s+(?:Слайд|Slide)\s+(\d+)[^\n]*\n(.*?)(?=^##\s+(?:Слайд|Slide)\s+\d+|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    slides = []
    for match in pattern.finditer(text):
        number = int(match.group(1))
        raw_body = match.group(2)

        # Clean up: remove HR separators, collapse whitespace
        body = re.sub(r"^---\s*$", "", raw_body, flags=re.MULTILINE)
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = body.strip()

        if body:
            slides.append({"number": number, "text": body})

    return slides


def estimate_cost(slides: list[dict], price_per_1k: float = 0.06) -> tuple[int, float]:
    total_chars = sum(len(s["text"]) for s in slides)
    cost = total_chars / 1000 * price_per_1k
    return total_chars, cost


# ── audio generation ──────────────────────────────────────────────────────────

def generate_audio(
    slides: list[dict],
    output_dir: Path,
    voice_id: str,
    api_key: str,
    model: str,
    stability: float,
    similarity_boost: float,
    style: float,
    speed: float,
    force: bool = False,
    pause_between_retries: float = 3.0,
    max_retries: int = 3,
) -> None:
    from elevenlabs import ElevenLabs, VoiceSettings
    from lecturer.pronunciation import apply_pronunciation

    client = ElevenLabs(api_key=api_key)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        number = slide["number"]
        text = apply_pronunciation(slide["text"])
        out_path = output_dir / f"slide_{number:02d}.mp3"

        # Skip if already generated (allows partial re-runs)
        if out_path.exists() and not force:
            print(f"  [{i}/{total}] slide {number:02d} — skipped (already exists)")
            continue

        char_count = len(text)
        print(f"  [{i}/{total}] slide {number:02d} — {char_count} chars → {out_path.name}")

        for attempt in range(1, max_retries + 1):
            try:
                audio_iter = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id=model,
                    voice_settings=VoiceSettings(
                        stability=stability,
                        similarity_boost=similarity_boost,
                        style=style,
                        speed=speed,
                    ),
                    output_format="mp3_44100_128",
                )
                # SDK returns a generator of bytes chunks
                with open(out_path, "wb") as f:
                    for chunk in audio_iter:
                        f.write(chunk)
                break  # success

            except Exception as exc:
                print(f"    attempt {attempt}/{max_retries} failed: {exc}")
                if attempt < max_retries:
                    time.sleep(pause_between_retries)
                else:
                    print(f"    ERROR: giving up on slide {number:02d}")
                    # Write a marker file so we know this one failed
                    out_path.with_suffix(".FAILED").touch()


# ── voice listing ─────────────────────────────────────────────────────────────

def list_voices(api_key: str) -> None:
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    voices = client.voices.get_all()
    print(f"{'Name':<30} {'Voice ID':<32} Category")
    print("-" * 75)
    for v in voices.voices:
        category = getattr(v, "category", "")
        print(f"{v.name:<30} {v.voice_id:<32} {category}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_slide_range(spec: str, total: int) -> list[int]:
    """Parse '3-5' or '2,4,7' or '3' into a list of slide numbers."""
    numbers = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            numbers.update(range(int(start), int(end) + 1))
        else:
            numbers.add(int(part))
    return sorted(numbers)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate per-slide MP3 files from a narration script.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "script",
        type=Path,
        nargs="?",
        help="Path to narration script, or lecture name (resolved via lecturer.toml)",
    )
    parser.add_argument(
        "--voice-id",
        help="ElevenLabs voice ID (required unless --dry-run or --list-voices)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for MP3 output files (default: ./audio/)",
    )
    parser.add_argument(
        "--model",
        default="eleven_multilingual_v2",
        help="ElevenLabs model ID (default: eleven_multilingual_v2)",
    )
    parser.add_argument(
        "--stability",
        type=float,
        default=0.5,
        help="Voice stability 0.0–1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--similarity-boost",
        type=float,
        default=0.8,
        help="Similarity to original voice 0.0–1.0 (default: 0.8)",
    )
    parser.add_argument(
        "--style",
        type=float,
        default=0.0,
        help="Style exaggeration 0.0–1.0 (default: 0.0)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speaking speed 0.7–1.2 (default: 1.0)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate existing MP3 files instead of skipping them",
    )
    parser.add_argument(
        "--slides",
        default=None,
        help="Slide range to generate, e.g. '1-3' or '2,5,7' (default: all)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="ElevenLabs API key (overrides ELEVENLABS_API_KEY env var)",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse script and show what would be generated, no API calls",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = args.api_key or os.environ.get("ELEVENLABS_API_KEY")

    if args.list_voices:
        if not api_key:
            print("Error: ELEVENLABS_API_KEY not set.", file=sys.stderr)
            sys.exit(1)
        list_voices(api_key)
        return

    if not args.script:
        print("Error: script path or lecture name is required.", file=sys.stderr)
        sys.exit(1)

    # Resolve: if the argument is not an existing file, treat it as a lecture name
    script_path = args.script.resolve()
    if not script_path.exists():
        from lecturer.config import get_content_dir
        candidate = get_content_dir() / str(args.script) / "narration_script.md"
        if candidate.exists():
            script_path = candidate
        else:
            print(f"Error: file not found: {script_path}", file=sys.stderr)
            print(f"  Also tried: {candidate}", file=sys.stderr)
            sys.exit(1)

    # Parse slides
    slides = parse_slides(script_path)
    if not slides:
        print("Error: no slides found in script. Check heading format.", file=sys.stderr)
        print("  Expected: ## Слайд N — Title  or  ## Slide N — Title", file=sys.stderr)
        sys.exit(1)

    # Filter by range if requested
    if args.slides:
        requested = parse_slide_range(args.slides, len(slides))
        slides = [s for s in slides if s["number"] in requested]

    total_chars, cost = estimate_cost(slides)

    print(f"Script:  {script_path.name}")
    print(f"Slides:  {len(slides)}")
    print(f"Chars:   {total_chars:,}")
    print(f"Cost:    ~${cost:.2f} at $0.06/1K chars")
    print()

    if args.dry_run:
        print("Dry run — slides that would be generated:")
        for s in slides:
            print(f"  slide_{s['number']:02d}.mp3  ({len(s['text'])} chars)")
            # Show first 80 chars of text as preview
            preview = s["text"][:80].replace("\n", " ")
            print(f"    {preview}…")
        return

    if not api_key:
        print("Error: ELEVENLABS_API_KEY is not set.", file=sys.stderr)
        print("  Set it with:  export ELEVENLABS_API_KEY=your_key", file=sys.stderr)
        sys.exit(1)

    if not args.voice_id:
        print("Error: --voice-id is required.", file=sys.stderr)
        print("  Run with --list-voices to see available voices.", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output_dir or script_path.parent / "audio"

    print(f"Voice:   {args.voice_id}")
    print(f"Model:   {args.model}")
    print(f"Output:  {output_dir}")
    print()

    generate_audio(
        slides=slides,
        output_dir=output_dir,
        voice_id=args.voice_id,
        api_key=api_key,
        model=args.model,
        stability=args.stability,
        similarity_boost=args.similarity_boost,
        style=args.style,
        speed=args.speed,
        force=args.force,
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
