# Hyperframes Composition Brief: Neuro Web

## Objective
Create a short launch-style brag video for Neuro Web.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 23.4 seconds

## Source Material
- Project root: `/home/haaris786/dev/Neuro-Web`
- Primary files read: `README.md`, `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/components/url-input.tsx`, `frontend/components/progress-tracker.tsx`, `frontend/components/results/report-card.tsx`, `frontend/lib/types.ts`
- Product name: **Neuro Web**
- Tagline / strongest claim: "See how websites affect your brain." — backed by TRIBE v2 predicting activation across ~20,484 cortical vertices per second, locally.
- Key UI or visual moments to recreate:
  - The `fsaverage5` 3D cortical mesh lit by activation (the hero visual, used twice — dark in Scene 1, lit in Scene 5)
  - The `UrlInput` panel: `#111827`/80 rounded-2xl, cyan-ringed globe glyph, gradient Analyze button, cyan focus glow
  - The `ProgressTracker` vertical rail: Validating → Capturing → Analyzing → Scoring → Ready with the emerald→cyan completed connector
  - The `CircularGauge` rings from `report-card.tsx`: r=54, stroke=7, `-rotate-90`, mono numerals, `/ 10` caption
- Copy that must appear verbatim:
  - "This is a visual cortex reading a landing page."
  - "Neuro Web"
  - "See how websites affect your brain."
  - "Powered by Meta TRIBE v2 · Local GPU Inference"
  - "Validating" / "Capturing" / "Analyzing" / "Scoring" / "Ready"
  - "3 dark patterns found"
  - "Urgency" / "Confirmshaming" / "Pre-checked consent"
  - "No cloud. No upload. It ran on your GPU."

## Creative Direction
- Tone preset: **polished**
- Creative direction: *a research instrument that happens to be beautiful*
- Interpretation: Confidence through restraint. No punch-ins, no flashing, no exclamation energy. Long settled holds, soft crossfades, generous negative space on near-black. Motion decelerates rather than springs (except the gauges, which use the project's own `cubic-bezier(0.34, 1.56, 0.64, 1)` overshoot). Seven scenes, but each holds ≥2.4s — the extra scenes buy the full user flow, not faster cutting.
- Angle: Not "analytics for your website." The premise is that a webpage is doing something to a visual cortex, and this thing shows you what — down to 20,484 vertices, once per second. The video earns its claim by being precise instead of loud: real model, real numbers, real dark patterns caught, and the honest framing the README insists on — these are *predictions*, not measurements from a person. The specificity is the brag.
- Hook: A dark cortical mesh flares cyan region by region under the line "This is a visual cortex reading a landing page." No logo, no product name for the first 3 seconds.
- Outro / punchline: "No cloud. No upload. It ran on your GPU." — lands precisely because the preceding 18 seconds look like they must have been a cloud service.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign
  - **Any claim of measuring a real person's brain.** The README is explicit that these are model predictions, z-scored and page-relative — not measurements, not clinical. Copy and motion must not editorialize past that.
  - **Any real brand name as the analyzed URL.** Scene 6 accuses the on-screen URL of three dark patterns; it must stay `https://shop.example.com/checkout` (IANA-reserved).

## Visual Identity
- Direction: *lab instrument documentation* — neutral graphite, one accent, colour reserved for data.
- Background `#0B0B0C`; surfaces `#151517`/`#1C1C1F`; borders `#26262A`/`#33333A`
- Text `#EDEDEF` / `#B4B4BB` / `#9A9AA3`
- Accent, one only: `#FF5A1F` signal orange
- Fonts: Inter (display + body), JetBrains Mono (all numerals)
- Viridis is used **only** for the cortical heatmap and its legend — it is the project's real colormap, so the only non-neutral colour besides the accent is actual data.

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. **Cortex hook** — 3.0s — dark mesh, three cyan flares building to an occipital flood; "This is a visual cortex reading a landing page." holds ~2.0s
2. **Reveal** — 2.6s — Neuro Web gradient wordmark, "See how websites affect your brain.", the TRIBE v2 pill badge
3. **Paste the URL** — 3.4s — `shop.example.com/checkout` types in, cyan focus glow, simulated click on Analyze
4. **The pipeline** — 3.6s — five stages tick in on consecutive beats, completed set holds ~1.1s
5. **The brain answers** — 4.4s — lit rotating mesh + three gauges counting to Impact 7.4 / Attention 8.1 / Emotion 6.2
6. **The receipts** — 3.4s — "3 dark patterns found" + three rose chips arriving ~1.09s apart
7. **Local** — 3.0s — "No cloud. No upload. It ran on your GPU." then the wordmark

## Audio
- Audio role: **cinematic support** — a low, unobtrusive bed that gives the piece shape without narrating it.
- Audio arc: Almost silent under the hook → warms at the wordmark → mechanical and sparse through the paste and pipeline → fullest at the brain reveal → pulls back for the dark-pattern chips → ducks and fades under the final line.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (109.96 BPM — slowest of the five bundled tracks, chosen for the polished tone)
- Music treatment: Start 0.0s well under the visuals. Lift at the wordmark (~3.3s). Settle under the pipeline. Fullest at the brain reveal (~13.1s). Duck for the outro line and fade out across the final 1.2s. No riser into the outro.
- Music cue guidance: Bundled preset read from `~/.claude/skills/brag/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`. Beat grid ~0.54s. Strong cues to target: **8.74s** (Analyze click), **13.11s** (brain reveal — the primary lock), **17.47 / 18.56 / 19.66s** (three dark-pattern chips), **22.93s** (wordmark landing). Lock no more than 3; the brain reveal is the one that matters most.
- Audio-reactive treatment: **subtle** — music RMS/bass may modulate the brain mesh glow intensity and the violet background bloom's presence, and nothing else. No waveform bars, no equalizers, no pumping on type. If extraction is unavailable (ffmpeg missing), skip it and note the skip — do not block.
- Audio-coupled moments:
  - Scene 1 occipital flood — low sub-swell, no hit on the text
  - Scene 3 URL typing — sparse key ticks, roughly every third character, not per-character
  - Scene 3 Analyze press — one soft interface click, beat-locked to 8.74s
  - Scene 4 stage completions — one quiet ascending tick per stage; the fifth (Ready) slightly warmer
  - Scene 5 mesh lighting — low swell at 13.11s; soft tick as each gauge number settles
  - Scene 6 chip arrivals — one light dry chip sound per arrival, identical each time, no escalation
  - Scene 7 wordmark — **no sound at all**
- SFX selection guidance: Sparse and motion-matched — 19 cues across 23.4s (6 cue types; the typing, stage and gauge ticks repeat). Every cue must line up with something that visibly moves. Sequential SFX fire on the same timestamp as their visual. Prefer `interface/` and `keyboard/` families over `impact/` and `casino/`; this edit has no place for a casino sound.
- SFX analysis guidance: `~/.claude/skills/brag/assets/sfx/sfx-analysis.md` — prefer low high-frequency-risk files throughout, since the tone is polished and several cues repeat (stage ticks, chip arrivals).
- Exact SFX choice: Hyperframes chooses filenames, timestamps, density, and volume after the visual animation exists.
- Audio files: copy the chosen music and any selected SFX into `brag-output/composition/assets/`.
- Restraint rule: No whooshes on crossfades. No riser into the outro. **No impact hit on the logo.** If a cue is not matched to visible motion, cut it.

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions over anything in `/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project. (This brief specifies four.)
- Keep all text readable in the final render. The hook line is the longest read — give it ~2.0s settled. Short labels need ~0.8s settled.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer.
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Ignore cues that hurt readability, scene pacing, or the product story.
- Major reveals may move toward nearby strong cues within ±0.15s; smaller entrances within ±0.10s of a beat. Use 1-3 strong cue locks total.
- Scene 4's five stage labels are the one place beat-rate reveal (~0.54s) is acceptable: the labels accumulate rather than replace, and the completed set holds ~1.1s afterward, so the viewer reads the finished list. Scene 6's three chips must use every *other* beat (~1.09s) to clear the reading floor.
- Honor the planned music treatment: fade-out across the final 1.2s, duck under the outro line, no hit on the logo.
- Use the audio-reactive workflow for the mesh glow and background bloom only, subtly.
- Use local assets for audio and any required runtime/media dependencies.
- Run `hyperframes check` before render — it is brag's single gate.

## Known environment blocker
`npx hyperframes doctor` on this machine reports missing **ffmpeg**, **ffprobe**, **unzip**, and **Chrome Headless Shell**. `hyperframes check` needs Chrome and the render needs ffmpeg, so both the gate and the render are blocked until those are installed (`sudo apt-get install -y ffmpeg unzip` then `npx hyperframes browser ensure`). Build the composition regardless; validate and render once the dependencies land. Audio-reactive extraction also depends on ffmpeg — skip and document if still unavailable at composition time.
