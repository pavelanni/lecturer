---
name: lecture-script
description: >
  Generates clean, concise narration scripts for short video lectures from
  slide content. Use this skill whenever the user wants to turn slides,
  outlines, or lecture transcripts into a per-slide narration script suitable
  for text-to-speech synthesis and video production. Triggers on requests like
  "write a narration script", "generate audio script for my slides", "turn
  this transcript into a clean script", "prepare lecture narration", or
  "create a script for my video lecture". Also use when the user provides
  slides in any format (PDF text, Markdown, plain text export) and asks for
  narration, voiceover text, or spoken content for each slide.
---

# Lecture script generation

## Purpose

Generate a narration script for a video lecture: one clearly delimited text
block per slide, written for spoken delivery, concise enough to fit within
45–90 seconds per slide, and free of live-lecture habits that don't translate
to video.

The script is the direct input to a TTS pipeline (ElevenLabs), so the writing
must sound natural when read aloud by a synthetic voice.

## Inputs

The user may provide any combination of:

- **Slides** — exported text, Markdown, or PDF content (primary source of
  structure and examples)
- **Transcript** — raw Whisper output from a live lecture recording (use as
  a signal for emphasis, personal examples, and which topics the lecturer
  considers important; do NOT copy wording verbatim)
- **Outline or notes** — informal bullet points or a lecture plan
- **Annotations** — short personal notes the user added to indicate where
  they want their own voice or stories woven in

When a transcript is provided, extract intent and emphasis from it, then
discard the structure and rewrite from scratch. The transcript is a priority
signal, not a content source.

When only slides are provided, generate the script from slide content alone.
This produces a slightly more generic but still effective result.

## Output format

Produce a single Markdown file. Use this exact structure:

```
# Narration script: [lecture title]

---

## Слайд N — [slide title]

[narration text]

---

## Слайд N+1 — [slide title]

[narration text]

---
```

- Number slides sequentially starting from 1
- Use Russian slide heading prefix "Слайд" for Russian-language content,
  "Slide" for English
- Separate every slide with a `---` HR line — the pipeline splits on these
- Do not include the slide heading text inside the narration body; the heading
  is just a label for the pipeline

## Writing principles

### Length
- Target 45–90 seconds of spoken audio per slide (roughly 90–180 words at
  a natural Russian/English lecture pace)
- Title and agenda slides: 20–40 seconds — at minimum two sentences: one
  naming the topic, one framing what the lecture will cover
- Slides that are pure examples or code: 30–60 seconds of framing
- If a slide's content requires more than 90 seconds, flag it with a comment:
  `<!-- Consider splitting this slide -->`

### Tone and register
- Write for spoken delivery, not reading: shorter sentences, no parenthetical
  asides, no footnote-style qualifiers
- Use the second person ("you") to address students directly
- Academic but not stiff — the register of a clear, well-prepared lecturer,
  not a textbook
- Avoid throat-clearing openers: do NOT start with "So today we will...",
  "In this slide we see...", or "As I mentioned..." — go straight to content

### Content discipline
- One core idea per slide; if the slide has two ideas, address both briefly
  but don't expand both equally
- No biographical detours: personal anecdotes are allowed ONLY if the user
  explicitly annotated a place for one, and even then keep it to one sentence
- No historical retrospectives ("back in our day...", "when I was a student...")
  unless the user specifically requests it
- No filler transitions between slides — the edit handles pacing
- Examples before explanations: state the concrete case first, then generalize

### What to preserve from a transcript
When a transcript is available, extract and preserve:
- Specific examples the lecturer chose (especially ones not on the slides)
- Personal analogies that illuminate a concept
- Emphasis signals: topics the lecturer spent disproportionate time on
- Warnings or caveats the lecturer stressed ("always check this", "this is
  where students commonly make mistakes")

Discard: repetition, detours, meta-commentary about the lecture itself,
references to live demo navigation, filler phrases.

### Numbers and technical content
- Read numbers as words where natural in speech ("forty-two percent", not
  "42%") — TTS handles this better
- For formulas or code, describe what they do rather than reading syntax aloud
- Keep technical terms exact — do not paraphrase terminology

### Abbreviation pronunciation
Abbreviations must be written as they should be pronounced aloud. TTS
engines read them literally, so spell out anything that would sound wrong
in the target language.

Check `src/lecturer/pronunciation.py` for the current replacement rules.
If the file exists, the pipeline applies these automatically — you do not
need to expand abbreviations manually in the script. If the file does not
cover a term you need, expand it inline in the narration text.

**Example (Russian):**

| Written | Spoken form | Context |
|---|---|---|
| ИИ (standalone) | искусственный интеллект | «работа с искусственным интеллектом» |
| ИИ- (compound) | эй-ай | «эй-ай агент» |
| LLM | эл-эл-эм | |
| CLI | си-эл-ай | |

**Example (English):**

| Written | Spoken form | Context |
|---|---|---|
| SQL | sequel or S-Q-L | depends on convention |
| CLI | C-L-I | |
| IoT | I-o-T | |

Alternatively, use an ElevenLabs pronunciation dictionary (PLS file)
to handle abbreviations at the TTS level — see `util/russian.pls` for
an example.

NOTE: do NOT change abbreviations inside `## Slide N — Title` or
`## Слайд N — Title` headings — those are pipeline labels, not spoken
text.

## Handling lectures without recordings

When there is no transcript, generate the script from slides alone. Use the
slide structure, bullet points, and examples as the content source. If a slide
is sparse (a title, a single bullet, or a pure diagram label), add one
concrete example or practical implication to give the narration substance —
do not simply read the slide text back. The result will be clean and coherent
but more generic in voice. Note this at the top of the output:

```
<!-- Generated from slides only — consider annotating personal examples
     before final review -->
```

## Handling user annotations

If the user provides inline annotations (e.g. "← add story about X here" or
notes in brackets), honour them: weave the indicated content into the narration
at that point. Keep annotated personal content to one or two sentences — just
enough to feel human.

## Self-check before output

Before returning the script, verify:

- [ ] Every slide has a heading in the correct format
- [ ] Every slide block ends with `---`
- [ ] No slide narration starts with a throat-clearing opener
- [ ] No slide exceeds ~180 words without a split comment
- [ ] Slide numbers are sequential and match the source material
- [ ] The script reads naturally aloud (scan for unpronounceable constructs)

## Example

**Input slide content:**
```
Статистический анализ
Промпт: Проанализируй эти данные статистически.
Рекомендуемые метрики: среднее 34.0°C, стандартное отклонение 6.8°C
Для проверки линейности — линейная регрессия (0–15 мин)
```

**Good narration:**
```
ИИ может также подсказать, какие статистические методы применить к вашим
данным, и выполнить базовые расчёты. Достаточно попросить: «проанализируй
эти данные статистически, предложи подходящие метрики и тесты».

Здесь важно помнить об ограничении: языковые модели — языковые, не
численные. Они дают разумные советы по методологии, но конкретные числа
стоит проверять. Среднее тридцать четыре градуса при данных от двадцати
пяти до сорока трёх — выглядит правдоподобно. Если бы модель написала
семьдесят восемь — вы бы сразу заметили ошибку.
```

**Bad narration (what to avoid):**
```
На этом слайде мы видим статистический анализ. Как я уже говорил на
прошлом занятии, искусственный интеллект может помочь с числами. Вы знаете,
когда я сам учился, у нас не было таких инструментов, и приходилось всё
делать вручную... Но вернёмся к теме. Итак, искусственный интеллект.
```
