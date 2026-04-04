#!/usr/bin/env python3
"""Assemble a lecture video from slide PNGs and per-slide MP3 audio files.

Combines slide images (from Marp export) with narration audio (from
ElevenLabs TTS) into a single MP4 video using ffmpeg.

Usage:
    python -m lecturer.build_video content/ai-agents-why

    # Dry run — show what would be assembled
    python -m lecturer.build_video content/ai-agents-why --dry-run

    # Custom output path
    python -m lecturer.build_video content/ai-agents-why -o output/lecture.mp4

Requirements:
    ffmpeg must be installed and available on PATH.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def find_slides(content_dir: Path) -> list[tuple[int, Path, Path]]:
    """Find matched pairs of slide PNG + audio MP3.

    Returns list of (slide_number, png_path, mp3_path) sorted by number.
    """
    slides_dir = content_dir / "slides"
    audio_dir = content_dir / "audio"

    if not slides_dir.is_dir():
        print(f"Error: slides directory not found: {slides_dir}", file=sys.stderr)
        sys.exit(1)
    if not audio_dir.is_dir():
        print(f"Error: audio directory not found: {audio_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect PNGs: slides.001.png -> number 1
    pngs = {}
    for p in sorted(slides_dir.glob("slides.*.png")):
        try:
            num = int(p.stem.split(".")[-1])
            pngs[num] = p
        except ValueError:
            continue

    # Collect MP3s: slide_01.mp3 -> number 1
    mp3s = {}
    for p in sorted(audio_dir.glob("slide_*.mp3")):
        try:
            num = int(p.stem.split("_")[-1])
            mp3s[num] = p
        except ValueError:
            continue

    # Match pairs
    matched = []
    all_nums = sorted(pngs.keys() | mp3s.keys())
    for n in all_nums:
        if n in pngs and n in mp3s:
            matched.append((n, pngs[n], mp3s[n]))
        elif n in pngs:
            print(f"  Warning: slide {n} has PNG but no audio — skipping")
        else:
            print(f"  Warning: slide {n} has audio but no PNG — skipping")

    return matched


def get_audio_duration(mp3_path: Path) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(mp3_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"    ffprobe error for {mp3_path.name}: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return float(result.stdout.strip())


def build_slide_clip(
    png_path: Path,
    mp3_path: Path,
    output_path: Path,
    duration: float,
    pause: float = 0.0,
) -> None:
    """Create a video clip from one slide image + its audio.

    If pause > 0, the slide image is shown for that many seconds
    before the audio begins, simulating a presenter pausing after
    advancing to a new slide.
    """
    total_duration = duration + pause
    scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"

    if pause > 0:
        # Delay the audio by 'pause' seconds using the adelay filter
        delay_ms = int(pause * 1000)
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-framerate", "1",
            "-t", str(total_duration),
            "-i", str(png_path),
            "-i", str(mp3_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", "5",
            "-vf", scale_filter,
            "-af", f"adelay={delay_ms}|{delay_ms}",
            "-t", str(total_duration),
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-framerate", "1",
            "-i", str(png_path),
            "-i", str(mp3_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", "5",
            "-vf", scale_filter,
            "-shortest",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ffmpeg error: {result.stderr[-500:]}", file=sys.stderr)
        sys.exit(1)


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> None:
    """Concatenate video clips using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as concat_file:
        for clip in clip_paths:
            concat_file.write(f"file '{clip}'\n")
        concat_path = concat_file.name

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ffmpeg concat error: {result.stderr[-500:]}", file=sys.stderr)
            sys.exit(1)
    finally:
        Path(concat_path).unlink(missing_ok=True)


def build_video(content_dir: Path, output_path: Path, dry_run: bool = False, pause: float = 0.0) -> None:
    """Main entry point: assemble lecture video from slides + audio."""
    content_dir = content_dir.resolve()
    slides = find_slides(content_dir)

    if not slides:
        print("Error: no matched slide/audio pairs found.", file=sys.stderr)
        sys.exit(1)

    total_duration = 0.0
    print(f"Lecture:  {content_dir.name}")
    print(f"Slides:  {len(slides)}")
    if pause > 0:
        print(f"Pause:   {pause}s before each slide")
    print()

    for num, png, mp3 in slides:
        duration = get_audio_duration(mp3)
        total_duration += duration
        print(f"  slide {num:02d}  {duration:5.1f}s  {png.name} + {mp3.name}")

    minutes = int(total_duration // 60)
    seconds = total_duration % 60
    print(f"\nTotal duration: {minutes}m {seconds:.0f}s")
    print(f"Output: {output_path}")

    if dry_run:
        print("\nDry run — no video created.")
        return

    print("\nBuilding per-slide clips...")
    clips_dir = content_dir / ".clips"
    clips_dir.mkdir(exist_ok=True)

    # Pre-compute durations (already done above for display, redo for build)
    durations = {num: get_audio_duration(mp3) for num, _, mp3 in slides}

    clip_paths = []
    for i, (num, png, mp3) in enumerate(slides, start=1):
        clip_path = clips_dir / f"clip_{num:02d}.mp4"
        clip_paths.append(clip_path)

        if clip_path.exists():
            print(f"  [{i}/{len(slides)}] slide {num:02d} — skipped (clip exists)")
            continue

        print(f"  [{i}/{len(slides)}] slide {num:02d} — encoding...")
        build_slide_clip(png, mp3, clip_path, durations[num], pause=pause)

    print("\nConcatenating clips...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concatenate_clips(clip_paths, output_path)

    print(f"\nDone: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble lecture video from slide PNGs and audio MP3s.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "content_dir",
        type=Path,
        help="Path to lecture content directory, or lecture name (resolved via lecturer.toml)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: content/<lecture>/<lecture>.mp4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be assembled without creating video",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=1.0,
        help="Seconds of silence before narration on each slide (default: 0.8)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove intermediate clip files after successful assembly",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    content_dir = args.content_dir.resolve()
    if not content_dir.is_dir():
        # Try as lecture name via config
        from lecturer.config import get_content_dir
        candidate = get_content_dir() / str(args.content_dir)
        if candidate.is_dir():
            content_dir = candidate
        else:
            print(f"Error: not a directory: {content_dir}", file=sys.stderr)
            print(f"  Also tried: {candidate}", file=sys.stderr)
            sys.exit(1)

    output_path = args.output or content_dir / f"{content_dir.name}.mp4"
    output_path = output_path.resolve()

    build_video(content_dir, output_path, dry_run=args.dry_run, pause=args.pause)

    if args.clean and not args.dry_run:
        clips_dir = content_dir / ".clips"
        if clips_dir.exists():
            import shutil
            shutil.rmtree(clips_dir)
            print("Cleaned up intermediate clips.")


if __name__ == "__main__":
    main()
