---
name: lecture-slides
description: >
  Develops lecture content through conversation and generates
  Marp-compatible Markdown slides. Use this skill whenever the user
  wants to create a new lecture, build a presentation, develop slides
  for a topic, or prepare visual content for a video lecture. Triggers
  on requests like "create slides for", "build a lecture about",
  "prepare a presentation on", "develop slides", or "make a lecture".
---

# Lecture slide generation

## Purpose

Develop lecture content collaboratively and produce a Marp-compatible
Markdown file that renders to a set of slides. The output is the first
stage of the video lecture pipeline: slides → narration script → audio
→ video.

The skill guides the conversation from a rough topic idea to a
polished slide deck, ensuring the lecture stays focused and fits the
target duration.

## Context

This skill is part of the Lecturer video lecture pipeline. The
instructor uses Claude Code to develop content, ElevenLabs for voice
synthesis, and ffmpeg for video assembly. Slides are rendered to PNG
by Marp CLI and combined with per-slide audio into MP4 video lectures.

The skill is course-agnostic. Course name and language are determined
during Phase 1 (topic exploration). The footer text is set based on
the course name from the conversation.

## Workflow

The skill has four phases. Complete each before moving to the next.

### Phase 1: Topic exploration

Ask 2-5 questions to understand the lecture scope. Ask one question at
a time.

1. **Topic and coverage** — what should the lecture cover? What
   specific subtopics, examples, or demos to include?
2. **Audience** — graduate or undergraduate? What do students already
   know about this topic?
3. **Language** — should the slides be in Russian or English?
4. **Exclusions** — anything to explicitly leave out or defer to
   another lecture?
5. **Course context** — which course is this for? (determines the
   header text)

If the topic is too broad for a 6-10 minute lecture, suggest how to
split it before proceeding.

### Phase 2: Outline proposal

Generate a numbered outline in this format:

```
Slide 1 — Title Slide [short]
  Lecture title, course name, date

Slide 2 — Agenda [short]
  Numbered list of topics

Slide 3 — <Topic> [medium]
  Key points to cover on this slide

...

Slide N — Summary [short]
  3-5 key takeaways
```

Duration markers: short (~45s), medium (~60s), long (~90s).

Show the total estimated time at the bottom. If the outline exceeds
15 slides, flag it and suggest splitting into two lectures.

### Phase 3: Outline review

Present the outline and ask: "Does this outline look right? You can
add, remove, reorder, split, or merge slides."

Iterate until the user explicitly approves (e.g., "looks good",
"approved", "go ahead").

Do NOT generate slides until the outline is approved.

### Phase 4: Slide generation

Generate the Marp Markdown file and save it using the Write tool.

Before writing, propose the lecture directory name (lowercase,
hyphenated, e.g., `iot-deploying-mcus`) and confirm with the user.

Save to: `content/<lecture-name>/slides/slides.md`

After saving, output:

> Slides saved to `content/<name>/slides/slides.md`.
>
> Next steps:
> 1. Review the slides — fill in any `<!-- TODO -->` image
>    placeholders
> 2. Generate PNGs:
>    `marp content/<name>/slides/slides.md --images png --theme-set themes/graph_paper.css`
> 3. Generate narration script: use the `lecture-script` skill with
>    the slides

## Marp output format

### Frontmatter

Every generated file starts with:

```yaml
---
marp: true
theme: graph_paper
paginate: true
header: ""
footer: "<Institution> — <Course Name>"
---
```

Replace `<Institution>` and `<Course Name>` with the values from
Phase 1 (e.g., `"MIT — Machine Learning"` or `"МИФИ — IoT"`).
The course name goes in the **footer** (not header) to avoid
crowding the slide title. If no institution is specified, use just
the course name.

### Slide types

| Type | Usage | Marp directive |
| --- | --- | --- |
| Title | Lecture title, course, date | `<!-- _class: section-title -->` |
| Agenda | Numbered topic list | (none) |
| Content | Heading + bullets | (none) |
| Example | Concrete scenario, code snippet | (none) |
| Summary | 3-5 key takeaways | (none) |
| References | Sources, links | `<!-- _class: tinytext -->` |

### Slide structure

- Use `---` to separate slides
- Use `#` (H1) for slide titles
- Use `<!-- _class: section-title -->` before the title slide
- Use `<!-- _class: tinytext -->` for reference/attribution slides
- Use `<!-- TODO: add diagram of X -->` for image placeholders
- When the instructor replaces a `<!-- TODO -->` with an actual image,
  use `<img src="image.png" class="fit-image">` for consistent sizing

### Content rules

- **One idea per slide** — if a topic needs two slides, split it
- **3-5 bullet points max** — slides are visual aids, not scripts
- **Examples before theory** — state the concrete case first, then
  generalize
- **No filler slides** — no "Questions?", "Thank you", or
  "Introduction" slides without content. These are for video lectures,
  not live presentations
- **Code and commands** — use fenced code blocks with language tags
  for syntax highlighting
- **No embedded images** — use `<!-- TODO -->` placeholders only; the
  instructor adds actual images
- **Language consistency** — all content (titles, bullets, header) in
  the language chosen in Phase 1
- **No abbreviation expansion on slides** — keep abbreviations in
  their written form (LLM, CLI, API, etc.). Pronunciation rules
  (e.g., LLM → эл-эл-эм) apply only to narration scripts, not
  slides. Slides are visual aids read by the audience, not spoken text

## Scope

This skill:
- Does NOT generate narration scripts — that is the `lecture-script`
  skill, used after slides are ready
- Does NOT embed actual images — only `<!-- TODO -->` placeholders
- Does NOT run Marp — only outputs the CLI command for the user to run

## Target parameters

- **Total duration:** 6-10 minutes
- **Slide count:** 8-15 slides
- **Per-slide narration:** 45-90 seconds (roughly 90-180 words)
- If content exceeds ~15 slides, suggest splitting into multiple
  lectures before generating

## Self-check before output

Before returning the generated Markdown, verify:

- [ ] Every slide has an H1 (`#`) title
- [ ] Slides are separated by `---`
- [ ] Frontmatter includes `marp: true` and `theme: graph_paper`
- [ ] Total slide count is within 8-15
- [ ] No slide has more than 5 bullet points
- [ ] Image placeholders use `<!-- TODO: ... -->` format
- [ ] Title slide uses `<!-- _class: section-title -->`
- [ ] All content is in the language chosen in Phase 1
- [ ] Slide titles match the approved outline

## Example

**Good slide:**

```markdown
---

# ESP32 vs STM32: Choosing the Right MCU

- **ESP32** — built-in Wi-Fi/BLE, low cost, ideal for prototyping
- **STM32** — industrial-grade, lower power, broader peripherals
- Selection depends on connectivity, power budget, and volume

<!-- TODO: add comparison table or photo of both boards -->
```

**Bad slide (what to avoid):**

```markdown
---

# Microcontrollers

So today we are going to talk about microcontrollers. There are many
different types of microcontrollers available on the market today.
Some of them are better for IoT applications while others are more
suited for industrial use. Let's take a look at the most popular
ones and discuss their pros and cons in detail. First, we need to
understand what a microcontroller is and how it differs from a
microprocessor.
```

Problems: wall of text, throat-clearing opener, no bullet points,
tries to be a narration script instead of a visual aid.
