# Brag Plan: Neuro Web

## What is this app?
Paste any public URL and Neuro Web records the page scrolling in headless Chromium, runs Meta's TRIBE v2 brain-encoding model on your own GPU, and turns the predicted cortical response into attention/emotion scores, a 3D brain heatmap, a page overlay, and a dark-pattern report — entirely on your machine.

## The angle
Not "analytics for your website." The premise is that **a webpage is doing something to a visual cortex, and this thing shows you what** — down to 20,484 vertices, once per second. The video earns its claim by being precise instead of loud: real model (V-JEPA 2 + Llama 3.2-3B fused onto the cortical surface), real numbers, real dark patterns caught, and the honest framing the README insists on — these are *predictions*, not measurements from a person.

The specificity IS the brag. Any project can say "AI-powered insights." Only this one can put a glowing `fsaverage5` mesh on screen and say "this is the part of the brain that lit up for the pricing section."

## Hook (first 2-3 seconds)
Near-black. A dark cortical mesh sits still. One region flares cyan — then a second, then the occipital pole floods.

Line: **"This is a visual cortex reading a landing page."**

No logo, no product name yet. The image is strange enough to hold someone for 20 more seconds, and the line tells them exactly what they're looking at. It is the single claim no other project on their feed can make.

## Key moments (the middle)
- **The paste.** A real URL types into the actual `UrlInput` — cyan focus ring blooming, the gradient "Analyze" button depressing on click. The entry point is one field; show that it's one field.
- **The pipeline ticking.** Validating → Capturing → Analyzing → Scoring → Ready, ticking down the real `ProgressTracker` rail with the emerald-to-cyan completed line filling behind it. During "Capturing," a page thumbnail scrolls inside the stage. This is the moment the product stops being a form and becomes a machine.
- **The brain answering.** The mesh from the hook returns — now fully lit, rotating — while three `CircularGauge` rings sweep and their mono numbers count up: Impact 7.4, Attention 8.1, Emotion 6.2.
- **The receipts.** "3 dark patterns found" with three chips arriving one at a time: Urgency, Confirmshaming, Pre-checked consent — each with its real evidence-text treatment.

## Outro / punchline
The gauges and mesh compress down to a single line on black:

**"No cloud. No upload. It ran on your GPU."**

Then the wordmark. The punchline is the privacy claim precisely *because* the preceding 18 seconds looked like something that must have been a cloud service. The twist is that it wasn't.

## User flow worth showing
Three beats, straight from `app/page.tsx` → `app/analysis/[id]/page.tsx` → `app/results/[id]/page.tsx`:
1. **Entry** — paste a URL into the one input on the home page, hit Analyze.
2. **Key action** — the job runs its five pipeline stages live over SSE, capture through scoring.
3. **Result** — the results page: report-card gauges, the interactive brain heatmap, the dark-pattern summary.

Scenes 3, 4, 5 and 6 are the centerpiece and all four come from the working app. The landing-page hero appears only as the frame in Scene 2.

## Tone
- Preset: **polished**
- Creative direction: *a research instrument that happens to be beautiful*
- Interpretation: Confidence through restraint. No punch-ins, no flashing, no exclamation energy. Long settled holds, soft crossfades, generous negative space on near-black. Motion is smooth and decelerating rather than springy. The product is genuinely technical and the README is scrupulous about what it does and doesn't claim — the video matches that register. Seven scenes is above the polished default of 3-4, but every scene holds 2.4s or longer, so the pacing stays unhurried; the extra scenes buy the full user flow rather than faster cutting.

## Format: landscape — 1920x1080
## Duration: 23.4s

## Visual identity
Revised direction (v2) — the first cut's cyan/blue/violet gradient stack read as generic AI-product styling. Replaced with a **neutral graphite ground, one accent, and colour reserved for data**.

- Direction: *lab instrument documentation* — Vercel/Geist monochrome structure with the typographic restraint of a Nature methods figure.
- Background: `#0B0B0C` (neutral graphite, deliberately no blue cast; the old `#0a0e1a` was blue-tinted)
- Surfaces: `#151517` / `#1C1C1F`; borders `#26262A` / `#33333A`
- Text: `#EDEDEF` bone / `#B4B4BB` / `#9A9AA3`
- **Accent (one only): `#FF5A1F` signal orange.** Used for: the logo mark, the pill dot, the Analyze button, pipeline ticks and rail, the Impact gauge, dark-pattern rules and confidence figures, and the two accented words in the hook line. Nothing else.
- Hierarchy through restraint: Impact is accent; Attention and Emotion are neutral bone/grey, so the eye lands on the headline metric.
- Display + body font: **Inter**; all numerals **JetBrains Mono**
- **Viridis appears only as data** — the cortical heatmap and its legend. This is the project's real default colormap (`frontend/lib/colormaps.ts`), so the one non-neutral, non-accent colour in the frame is genuine measurement, exactly as a real neuroimaging tool would present it.

## The cortical surface
Rendered offline (`scripts` in scratch, output committed to `composition/assets/brain/`) rather than drawn as decorative blobs:
- A left-lateral cortical silhouette with temporal lobe, Sylvian fissure, central sulcus and intraparietal sulcus as shaded grooves.
- Procedural gyral relief, normals from a blurred height field, Lambert shading and rim falloff for volume.
- Activation is **thresholded** at 0.18 — sub-threshold cortex stays neutral grey tissue and only supra-threshold vertices take viridis, which is how a real statistical surface map reads. Full state covers ~15% of frame.
- Three states (`brain-a/b/c.png`) cross-fade so activation visibly *resolves* rather than appearing at once.
- No cerebellum or brainstem: TRIBE v2 predicts on `fsaverage5`, a cortical surface mesh, so including them would be both a visual defect and anatomically wrong for this project.

## Share copy (draft)
Paste a URL. Neuro Web records the page, runs Meta's TRIBE v2 on your own GPU, and shows you which parts of a visual cortex a website actually lights up — plus every dark pattern it caught. All of it local.

## Audio direction
- Role: **Cinematic support** — a low, unobtrusive bed that gives the piece shape without narrating it.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (109.96 BPM — the slowest of the five bundled tracks, which is why it fits `polished`).
- Music treatment: Start at 0.0s well under the visuals. Hold low through the hook, lift slightly at the wordmark, settle under the pipeline, reach its fullest at the brain reveal, then duck for the outro line and fade out over the final 1.2s.
- Music cue guidance: Preset cue file read from `assets/music/cues/`. Tempo 109.96 BPM, beat grid ~0.54s. Target strong cues: **8.74s** (the Analyze click), **13.11s** (the brain reveal), **17.47s / 18.56s / 19.66s** (the three dark-pattern chips), **22.93s** (the wordmark landing). Sequential reveals snap to *every other* beat (~1.09s) so short labels clear the 0.8s reading floor.
- Audio-reactive treatment: **subtle** — let music RMS/bass modulate the brain mesh's glow intensity and the violet background bloom's presence only. No waveform bars, no pumping on the type.
- SFX posture: **sparse**, motion-matched. Roughly six cues in 23 seconds. Every one lines up with something that actually moves.
- Audio-coupled moments: key ticks as the URL types; one soft interface click on Analyze; a quiet ascending tick per pipeline stage completing; a low swell under the brain reveal; a soft tick per gauge as its number settles; three light chips for the dark-pattern arrivals.
- Restraint rule: No whooshes on crossfades, no riser into the outro, no impact hit on the logo. Nothing may imply "measurement of a real person" — this is predicted response, and the audio must not editorialize it into drama. If a cue isn't matched to visible motion, cut it.

## Storyboard

### Scene 1 — Cortex hook — 3.0s
Near-black `#0a0e1a` with the noise overlay. A dark, desaturated cortical mesh (three-quarter view, left hemisphere) sits still and unlit. At ~0.5s one region flares cyan, at ~1.0s a second, then the occipital pole floods cyan-to-violet and holds lit. Line settles bottom-left in Inter semibold slate-100: **"This is a visual cortex reading a landing page."** (8 words → holds ~2.0s settled, the longest read in the video.)
Sequential/interaction: yes — three activation flares arrive one after another, each brighter than the last.
Audio intent: Almost silent, then presence. The viewer should lean in, not be pushed back.
Audio-coupled idea: a low sub-swell under the occipital flood; no hit on the text.
Music: low bed, barely present.
Transition mood: soft crossfade → Scene 2

### Scene 2 — Reveal — 2.6s
The mesh dims back and recedes. The violet radial bloom rises from the top edge exactly as it does on the real home page. The wordmark **Neuro Web** scales in at 0.94 → 1.0 with the cyan-300 → blue-400 → violet-500 gradient clipped to the text. Beneath it, the project's own line in slate-300: **"See how websites affect your brain."** Below that, the real pill badge from the hero: a cyan dot + "Powered by Meta TRIBE v2 · Local GPU Inference".
Sequential/interaction: yes — wordmark, then tagline, then pill badge, ~0.5s apart.
Audio intent: The bed opens up. First moment of warmth.
Audio-coupled idea: none — let the music carry it.
Music: lift at the wordmark, near strong cue 3.27s.
Transition mood: soft crossfade → Scene 3

### Scene 3 — Paste the URL — 3.4s
Recreate the real `UrlInput`: `#111827`/80 rounded-2xl panel, the cyan-ringed globe glyph at left, the gradient Analyze button at right. A URL types into the field character by character: **`https://shop.example.com/checkout`**. This must stay an IANA-reserved `example.com` host and must never be a real brand — Scene 6 accuses this URL of three dark patterns, and naming a real business there would publish a fabricated accusation. The border transitions to `border-cyan-400/50` with the `0_0_40px_-8px` cyan glow as focus lands. At ~2.9s a cursor moves to Analyze, the button depresses to `scale(0.98)`, and the label swaps to the spinner + "Analyzing…".
Sequential/interaction: yes — simulated typing, then a simulated click on the Analyze button.
Audio intent: Tactile and quiet. The sound of someone doing one small thing.
Audio-coupled idea: sparse key ticks on the typing (not one per character — every third or so), one soft interface click on the button press at strong cue **8.74s**.
Music: steady under.
Transition mood: clean wipe → Scene 4

### Scene 4 — The pipeline — 3.6s
The real `ProgressTracker` rail, vertical, five stages: Validating, Capturing, Analyzing, Scoring, Ready. Stages complete top to bottom, the connector line filling `bg-gradient-to-b from-emerald-500 to-cyan-500/50` behind each completed node. As "Capturing" goes active, a small page thumbnail scrolls inside that row. As "Analyzing" goes active, a faint vertex scatter flickers in its row.
Sequential/interaction: yes — five stages tick in on consecutive beats (~0.54s apart, 9.29 → 11.46), then **the completed set holds on screen ~1.1s**. Labels are short and accumulate rather than replace, so the viewer reads the finished list, not each label in isolation — this is the one place beat-rate reveal is safe.
Audio intent: Mechanical progress, understated. A machine working, not a race.
Audio-coupled idea: one quiet ascending interface tick per stage completing; the fifth (Ready) slightly warmer than the rest.
Music: settle under; let the ticks sit on top.
Transition mood: soft crossfade → Scene 5

### Scene 5 — The brain answers — 4.4s
The centerpiece. The mesh from Scene 1 returns — now fully lit with the activation colormap, slowly rotating — occupying the left two-thirds. On the right, three `CircularGauge` rings sweep their `gauge-fill` arc and their mono numbers count up: **Impact 7.4**, **Attention 8.1**, **Emotion 6.2**, each with its `/ 10` caption. Gauges are cyan, blue and violet respectively.
Sequential/interaction: yes — the three gauges sweep and settle staggered ~0.6s apart; numbers count rather than cut in.
Audio intent: The payoff. The one moment the bed is allowed to be full.
Audio-coupled idea: a low swell as the mesh lights at strong cue **13.11s**; a soft tick as each gauge number settles.
Music: fullest point of the track; audio-reactive glow on the mesh permitted here, subtle.
Transition mood: soft crossfade → Scene 6

### Scene 6 — The receipts — 3.4s
Cut to the dark-pattern summary. Header in slate-200: **"3 dark patterns found"**. Three chips arrive one at a time in rose `#fb7185` on `#111827` surfaces: **Urgency**, **Confirmshaming**, **Pre-checked consent** — each with a short italic evidence line beneath it in slate-500 and a confidence percentage in mono at the right.
Sequential/interaction: yes — three chips at strong cues **17.47s / 18.56s / 19.66s**, ~1.09s apart, each clearing the 0.8s short-label reading floor.
Audio intent: Evidentiary. Each one lands like a item being placed on a table.
Audio-coupled idea: one light, dry chip sound per arrival — same sound each time, no escalation.
Music: pull back slightly to let the chips read.
Transition mood: soft crossfade → Scene 7

### Scene 7 — Local — 3.0s
Everything clears to near-black. One line, centered, Inter semibold slate-100: **"No cloud. No upload. It ran on your GPU."** It holds ~1.4s. Then it steps aside for the **Neuro Web** gradient wordmark, which settles and holds to the end.
Sequential/interaction: yes — line first, wordmark second.
Audio intent: Resolution, not triumph. The bed lets go.
Audio-coupled idea: none. No impact on the logo — this is the restraint rule's headline case.
Music: duck under the line, fade out across the final 1.2s; wordmark lands near strong cue **22.93s**.
Transition mood: hold to end.

**Music mood for this video:** cinematic
**Audio summary:** A low bed opens almost silent under the cortex hook, warms at the wordmark, stays mechanical and sparse through the paste and the pipeline ticks, swells to its fullest as the brain lights and the gauges count, pulls back to let three dark-pattern chips land dry, then ducks and fades under the final privacy line — six motion-matched SFX total, no whooshes, and no hit on the logo.

## Scene duration check
3.0 + 2.6 + 3.4 + 3.6 + 4.4 + 3.4 + 3.0 = **23.4s** (within 15-25s; sits just outside the 18-22 sweet spot to buy the full user flow). Scene 7 runs 3.0s rather than 2.4s so the wordmark lands on strong cue 22.93s and holds to the end.
