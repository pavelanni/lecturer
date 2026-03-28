#!/usr/bin/env python3
"""Transcribe a lecture recording using Whisper.

On Apple Silicon (M1/M2/M3/M4) uses mlx-whisper for Metal GPU acceleration.
On other platforms uses faster-whisper (CPU).

Install dependencies:
    # Apple Silicon
    pip install mlx-whisper

    # Other platforms
    pip install faster-whisper

Outputs three files next to the source audio (or in --output-dir):
    <n>.txt  — plain text, one paragraph per segment (editing / Claude)
    <n>.srt  — subtitles with timestamps (video pipeline)
    <n>.md   — Markdown with timestamps as headings (navigation)

Usage:
    python transcribe.py <audio_or_video_file> [options]

Examples:
    python transcribe.py lecture1.webm
    python transcribe.py lecture1.webm --model large-v3
    python transcribe.py lecture1.webm --output-dir ./transcripts
    python transcribe.py lecture1.webm --backend faster-whisper  # force CPU
"""

import argparse
import platform
import sys
from datetime import timedelta
from pathlib import Path


# ── platform detection ────────────────────────────────────────────────────────

def is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def choose_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    return "mlx" if is_apple_silicon() else "faster-whisper"


# ── helpers ───────────────────────────────────────────────────────────────────

def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_mm_ss(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


# ── transcription backends ────────────────────────────────────────────────────

def transcribe_mlx(input_path: Path, model_size: str, language: str) -> list[dict]:
    """Transcribe using mlx-whisper (Apple Silicon, Metal GPU)."""
    try:
        import mlx_whisper
    except ImportError:
        print("Error: mlx-whisper is not installed.", file=sys.stderr)
        print("Install it with:  pip install mlx-whisper", file=sys.stderr)
        sys.exit(1)

    # mlx-whisper uses Hugging Face model names
    model_map = {
        "tiny":     "mlx-community/whisper-tiny-mlx",
        "base":     "mlx-community/whisper-base-mlx",
        "small":    "mlx-community/whisper-small-mlx",
        "medium":   "mlx-community/whisper-medium-mlx",
        "large-v2": "mlx-community/whisper-large-v2-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
        "turbo":    "mlx-community/whisper-large-v3-turbo",
    }
    hf_model = model_map.get(model_size, model_size)
    print(f"Backend: mlx-whisper (Apple Silicon Metal GPU)")
    print(f"Model:   {hf_model}")

    result = mlx_whisper.transcribe(
        str(input_path),
        path_or_hf_repo=hf_model,
        language=language,
        verbose=False,
    )

    segments = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            segments.append({
                "start": seg["start"],
                "end":   seg["end"],
                "text":  text,
            })
    return segments


def transcribe_faster_whisper(
    input_path: Path, model_size: str, language: str
) -> list[dict]:
    """Transcribe using faster-whisper (CPU, cross-platform)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Error: faster-whisper is not installed.", file=sys.stderr)
        print("Install it with:  pip install faster-whisper", file=sys.stderr)
        sys.exit(1)

    print(f"Backend: faster-whisper (CPU)")
    print(f"Model:   {model_size}")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    raw_segments, info = model.transcribe(
        str(input_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    print(f"Detected language: {info.language} ({info.language_probability:.1%})")

    segments = []
    for seg in raw_segments:
        text = seg.text.strip()
        if text:
            segments.append({
                "start": seg.start,
                "end":   seg.end,
                "text":  text,
            })
    return segments


# ── output writing ────────────────────────────────────────────────────────────

def write_outputs(
    segments: list[dict],
    stem: str,
    output_dir: Path,
    model_size: str,
    language: str,
    source_name: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{stem}.txt"
    srt_path = output_dir / f"{stem}.srt"
    md_path  = output_dir / f"{stem}.md"

    total = len(segments)

    with (
        open(txt_path, "w", encoding="utf-8") as txt_f,
        open(srt_path, "w", encoding="utf-8") as srt_f,
        open(md_path,  "w", encoding="utf-8") as md_f,
    ):
        md_f.write(f"# Transcript: {stem}\n\n")
        md_f.write(f"- Source: `{source_name}`\n")
        md_f.write(f"- Model: `{model_size}`\n")
        md_f.write(f"- Language: `{language}`\n\n")
        md_f.write("---\n\n")

        for i, seg in enumerate(segments, start=1):
            text = seg["text"]

            # Progress every 20 segments
            if i % 20 == 0 or i == total:
                print(f"  [{i / total * 100:5.1f}%] segment {i}/{total}"
                      f" — {format_mm_ss(seg['end'])}")

            # plain text: paragraphs every 5 segments
            txt_f.write(text + " ")
            if i % 5 == 0:
                txt_f.write("\n\n")

            # SRT
            srt_f.write(f"{i}\n")
            srt_f.write(
                f"{format_srt_timestamp(seg['start'])} --> "
                f"{format_srt_timestamp(seg['end'])}\n"
            )
            srt_f.write(f"{text}\n\n")

            # Markdown: heading every 10 segments
            if i == 1 or i % 10 == 1:
                md_f.write(f"\n## [{format_mm_ss(seg['start'])}]\n\n")
            md_f.write(text + " ")
            if i % 5 == 0:
                md_f.write("\n\n")

    # Trailing newline
    for path in (txt_path, md_path):
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")

    print()
    print("Output files:")
    print(f"  Plain text : {txt_path}")
    print(f"  SRT        : {srt_path}")
    print(f"  Markdown   : {md_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a lecture recording with Whisper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to audio or video file (WebM, MP4, WAV, MP3, …)",
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"],
        help="Whisper model size (default: large-v3)",
    )
    parser.add_argument(
        "--language",
        default="ru",
        help="Language code (default: ru)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: same directory as input)",
    )
    parser.add_argument(
        "--backend",
        default="auto",
        choices=["auto", "mlx", "faster-whisper"],
        help="Whisper backend (default: auto — mlx on Apple Silicon, "
             "faster-whisper elsewhere)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = (
        args.output_dir.resolve() if args.output_dir else input_path.parent
    )

    backend = choose_backend(args.backend)
    print(f"Transcribing: {input_path.name}")

    if backend == "mlx":
        segments = transcribe_mlx(input_path, args.model, args.language)
    else:
        segments = transcribe_faster_whisper(input_path, args.model, args.language)

    print(f"Segments found: {len(segments)}")
    print("Writing output...")

    write_outputs(
        segments=segments,
        stem=input_path.stem,
        output_dir=output_dir,
        model_size=args.model,
        language=args.language,
        source_name=input_path.name,
    )


if __name__ == "__main__":
    main()
