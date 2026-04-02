# Lecturer — video lecture generation toolkit

A pipeline for generating short video lectures from slide content,
using the instructor's cloned voice.

```text
Slides (Marp Markdown) → PNG images → Narration script → Audio (MP3) → Video (MP4)
```

## Who is this for?

Instructors who want to produce pre-recorded video lectures
efficiently. You write (or co-create with AI) the slide content and
narration script; the pipeline handles audio synthesis and video
assembly. The toolkit is language-agnostic — it has been used for
courses in Russian and English, and supports any language that
ElevenLabs TTS can synthesize.

## Quick start with Docker

The easiest way to use Lecturer — no need to install Python, Node.js,
or ffmpeg:

```shell
# Pull the image (supports amd64 and arm64)
docker pull ghcr.io/pavelanni/lecturer

# See available commands
docker run --rm ghcr.io/pavelanni/lecturer help

# Generate slide images from your course directory
docker run --rm -v ./my-course:/course ghcr.io/pavelanni/lecturer generate-slides

# Generate audio (requires ElevenLabs API key)
docker run --rm -v ./my-course:/course \
    -e ELEVENLABS_API_KEY=sk_... \
    ghcr.io/pavelanni/lecturer generate-audio

# Build videos
docker run --rm -v ./my-course:/course ghcr.io/pavelanni/lecturer build-videos --clean

# Concatenate all lecture videos into one
docker run --rm -v ./my-course:/course ghcr.io/pavelanni/lecturer concat
```

Your course directory should contain `lecturer.toml` (see
Configuration below) and a `content/` subdirectory with your lectures.

Works with Docker and Podman on Linux, macOS, and Windows.

## Setup (without Docker)

If you prefer to run the tools directly:

```shell
# Python dependencies
uv sync

# Marp CLI for slide export (one-time)
npm install -g @marp-team/marp-cli

# ffmpeg for video assembly (one-time)
brew install ffmpeg   # macOS
```

### Voice cloning

The pipeline uses ElevenLabs for text-to-speech. To lecture in your
own voice:

1. Go to [ElevenLabs](https://elevenlabs.io) and create an account
2. Navigate to **Voices → Add Voice → Instant Voice Clone**
3. Upload a clean recording of your voice (1-5 minutes of speech)
4. Copy the Voice ID from the voice settings page
5. Add the Voice ID to your `lecturer.toml` (see Configuration below)

## Configuration

Copy `lecturer.toml.example` to `lecturer.toml` and adjust for your
course:

```toml
[course]
name = "My Course"
content_dir = "/path/to/my-course/content"
output_dir = "/path/to/my-course/output"
voice_id = "your-elevenlabs-voice-id"
lectures = [
    "lecture-01-intro",
    "lecture-02-basics",
]
```

The `lectures` list defines the canonical order used by all batch
scripts. Content and output directories are kept separate from the
tooling so each instructor can maintain their own course materials.

## Creating lectures with Claude Code skills

The toolkit includes two Claude Code skills that guide you through
lecture creation interactively. You don't need to write Marp Markdown
or narration scripts from scratch — the skills do it through
conversation.

### Creating slides (`lecture-slides` skill)

Start a conversation with Claude Code in this repo and describe what
you want to teach. The skill walks through four phases:

1. **Topic exploration** — Claude asks 2-5 questions: What should the
   lecture cover? Who is the audience? What language? What to exclude?
   Answer one question at a time.
2. **Outline proposal** — Claude generates a numbered slide outline
   with duration estimates. Review it and suggest changes.
3. **Outline review** — Iterate until you approve. Say "looks good" or
   "go ahead" to proceed.
4. **Slide generation** — Claude writes the Marp Markdown file and
   saves it to the content directory.

**Tips for good results:**

- Be specific about examples you want on slides — "use a smart
  greenhouse as the running example"
- Mention what students already know — "they've built REST API
  servers"
- Specify the language upfront — "slides should be in Russian"
- If a lecture is too long (>15 slides), the skill will suggest
  splitting it into parts
- Image placeholders are marked with `<!-- TODO: ... -->` — you add
  real images later

### Creating narration scripts (`lecture-script` skill)

After slides are ready, use this skill to generate the narration
script. Provide the slides and optionally a transcript from a live
recording. The skill produces one text block per slide, optimized for
TTS delivery.

**What the skill handles:**

- Appropriate length per slide (45-90 seconds of speech)
- Spoken delivery style — short sentences, no parenthetical asides
- Abbreviation pronunciation for TTS (configurable per language)
- No throat-clearing openers ("So today we will..." is avoided)

**You can annotate the slides** before generating the script — add
comments like `<!-- add story about X here -->` and the skill will
weave them into the narration.

### Recommended companion skills

If you use [Superpowers](https://github.com/anthropics/superpowers)
with Claude Code, these skills complement the lecture workflow:

| Skill | When to use |
|---|---|
| `brainstorming` | Planning a new lecture series — exploring topics, structure, audience |
| `writing-plans` | Breaking a multi-lecture series into an implementation plan |
| `executing-plans` | Working through the plan lecture by lecture |

## Batch scripts

All scripts take the course directory as the first argument:

| Script | What it does |
|---|---|
| `./generate_slides.sh <course>` | Export all slides to PNG + PDF via Marp |
| `./generate_all_audio.sh <course>` | Generate MP3 audio for all lectures via ElevenLabs |
| `./build_all_videos.sh <course>` | Assemble per-lecture MP4 videos from PNGs + MP3s |
| `./concat_videos.sh <course>` | Concatenate all lecture videos into a single MP4 |

Each script reads `lecturer.toml` from the course directory and
processes lectures in the configured order. Pass a lecture name after
the course directory to process just one:

```shell
./generate_slides.sh /path/to/my-course
./generate_slides.sh /path/to/my-course lecture-01-intro
./generate_all_audio.sh /path/to/my-course lecture-02-basics
```

### Useful flags

```shell
# Regenerate audio even if MP3s already exist
./generate_all_audio.sh /path/to/my-course --force

# Preview what videos would be built without building them
./build_all_videos.sh /path/to/my-course --dry-run

# Remove intermediate clips after building
./build_all_videos.sh /path/to/my-course --clean

# Generate only PDFs (skip PNGs)
./generate_slides.sh /path/to/my-course --pdf-only
```

## Individual commands

| Step | Command |
|---|---|
| Generate PNGs + PDFs | `./generate_slides.sh` |
| Generate audio (one) | `uv run python -m lecturer.generate_audio <lecture> --voice-id ID` |
| Assemble video (one) | `uv run python -m lecturer.build_video <lecture>` |
| Merge PDFs | `uv run python -m lecturer.concat_pdf` |
| Transcribe recording | `uv run python -m lecturer.transcribe recording.webm` |

## Video tuning

The video assembly has two parameters for pacing:

- `--pause 0.8` — seconds of silence before narration starts on each
  slide (default: 0.8). Simulates a presenter pausing after advancing
  to a new slide. Set to 0 to disable.
- `--speed 0.9` — pass to `generate_audio` to slow down TTS speech
  slightly (ElevenLabs range: 0.7-1.2, default: 1.0).

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key for audio generation |
| `ELEVENLABS_VOICE_ID` | No | Voice ID (overrides `voice_id` in `lecturer.toml`) |

## Full workflow

```shell
COURSE=/path/to/my-course

# 1. Create slides interactively with Claude Code
#    (use the lecture-slides skill)
#    Output: content/<lecture>/slides/slides.md

# 2. Export slide PNGs and PDFs
./generate_slides.sh $COURSE

# 3. Create narration scripts with Claude Code
#    (use the lecture-script skill)
#    Output: content/<lecture>/narration_script.md

# 4. Generate audio from narration scripts
export ELEVENLABS_API_KEY=your_key_here
./generate_all_audio.sh $COURSE

# 5. Assemble videos
./build_all_videos.sh $COURSE --clean

# 6. Concatenate into a single video (optional)
./concat_videos.sh $COURSE

# 7. Merge all slide PDFs into one handout (optional)
LECTURER_COURSE_DIR=$COURSE uv run python -m lecturer.concat_pdf \
    -o $COURSE/output/course-slides.pdf
```

## Pronunciation

For non-English lectures, TTS engines may mispronounce abbreviations.
Two approaches:

1. **In-pipeline replacement** — edit `src/lecturer/pronunciation.py`
   to map abbreviations to their spoken forms (e.g., `LLM` →
   `эл-эл-эм`). Applied automatically before TTS.
2. **ElevenLabs dictionary** — upload a PLS file via the ElevenLabs
   API or dashboard. See `util/russian.pls` for an example.

## Related projects

- **[Examiner](https://github.com/pavelanni/examiner)** — automated
  knowledge testing tool. The slides and narration scripts produced by
  Lecturer can serve as source material for generating quiz questions
  in Examiner's JSON format. Use the lecture content to create
  multiple-choice or open-ended questions that test student
  understanding of the material.

## Project structure

```text
src/lecturer/         Python package (pipeline modules)
.claude/skills/       Claude Code skills (lecture-slides, lecture-script)
themes/               Marp CSS themes
content/              Lecture artifacts (gitignored, per-course)
output/               Generated videos (gitignored)
```
