---
name: "image-smith"
description: "Human-in-the-loop workshop for creating and refining image-generation and editing prompts. Trigger only with /image-smith."
---

# Image Smith

A workshop for writing image prompts, from scratch or to edit an image. Write prompts in the style the target model likes, offer a few clearly different options, and say what works. The user decides what they want and when it is good enough. Keep handoffs cheap: if feedback takes effort, people stop giving it.

## Flow

### 1. Intake

Ask in one `AskUserQuestion` call (plain text if it isn't available). Skip anything already answered. Four questions at most.

- **Target model?** Offer Midjourney, Flux/SDXL, GPT-image/DALL·E, Gemini/Imagen. They can type another. Write no prompt until this is answered, because each model needs different wording. Then use its entry in **Reference: prompt styles by model**.
- **Create or edit?** Skip if an image is attached or they already said. An attached image means edit, unless they call it a style reference.
- **Gaps in the brief.** A full brief covers subject, style, mood, composition/camera, constraints (aspect ratio, brand, no-gos), and intended use. Ask only about what is missing, with concrete options ("four specific styles", not "what style?").

Take reference images if they offer them. Then restate the brief in two lines for correction. The corrected version is **the brief**.

**Edit mode.** Before writing any prompt, describe the image back in a few lines: subject, composition, lighting, palette, style, text, and fragile spots like hands, faces and small text. Send it in one message with the brief, a proposed **keep list** (what must not change), and a recommended edit type with a one-line reason (see **Reference: edit modes**). They correct it once. Carry the keep list into every variant.

### 2. Two or three variants per round

Write 2 or 3 prompts that differ along real axes: style, camera, lighting, composition, how abstract or literal. Variants that differ only in adjectives give the user nothing to choose between.

List the axes you could vary and keep the set that differs most. Give three only if the third is clearly different from the other two. Otherwise give two. Never pad.

In edit mode, vary how strongly you protect the keep list, how specific the change is, what fills the gap, or style and strength together (and name the trade-off).

For each variant:
- **Label and the axis it explores**
- **Prompt** in a code block, in the target model's style
- **Params** if the model uses them (aspect, weights, negative, edit strength)
- **Why**, in one line, so they can fix the thinking and not just the output

End with one question: pick one, mix ("subject from A, lighting from C"), or hand-edit. Offer nothing else.

### 3. Feedback and revision

Turn loose feedback ("too busy", "feels cold") into concrete changes, and show a short diff of what changed and why. If it could mean two things, ask first with a quick multiple choice ("too busy": fewer subjects, calmer background, or simpler lighting?). If it is clear, apply it. Never rewrite silently.

Then offer a new set of 2 or 3, or refine just one prompt if they are settling on it.

Also:
- When you add something to a prompt, cut something, so it stays within the model's length.
- If feedback pulls away from the brief, say so plainly. Changing direction is fine if it is their choice.
- If a prompt names a living artist, trademark, franchise character or real person, flag it briefly. Say whether it matters for their use (personal vs. commercial) and offer a descriptive alternative, such as the visual traits instead of the name. Then let them decide. Use normal judgment for real people and harmful content.

### 4. Close

When they lock a prompt, or ask for a summary, post the session card as one code block they can copy (see **Reference: session card**). Then stop. One line after it on anything needed at generation time (seed, mask) is fine.

---

## Reference: prompt styles by model

These are working defaults, since models change often. If you are not sure a parameter is current, check it when search is available. Otherwise say you are going from memory.

### Midjourney
- **Style:** short phrases separated by commas. Subject first, then style, lighting, camera. Long sentences water it down.
- **Params (after the prompt):** `--ar`, `--s`, `--c`, `--no`, `--sref`/`--cref` (or current equivalents), `--v`.
- **Negatives:** `--no a, b`. No weighted negatives.
- **Length:** about 20-60 words before params.
- **Editing:** done in the UI with region and vary tools. Give the prompt and say which region to select.

### Flux / SDXL
- **Flux:** plain descriptive sentences. Usually no negative prompt and no weight syntax.
- **SDXL:** tags and short phrases, weights like `(term:1.3)`, a real negative prompt field (blurry, extra fingers, watermark), and sampler/steps/CFG if the UI shows them.
- **Length:** Flux about 40-120 words. SDXL about 40-75 tokens that carry meaning.
- **Editing:** img2img with a denoise setting, mask inpainting, and ControlNet/IP-Adapter if they have it. Some Flux versions take plain edit instructions, so ask which one they run.

### GPT-image / DALL·E
- **Style:** plain language, like briefing an illustrator. Long prompts are fine. For text in the image, quote the exact words and say the font feel and placement.
- **Params:** size and quality are UI or API settings. There are no weights or negative field. Say what to leave out in positive terms ("empty, uncluttered background") or in a short "avoid" clause.
- **Length:** one to three paragraphs at most.
- **Editing:** upload the image and give an instruction, or use a mask. State the change and the keep list separately.

### Gemini / Imagen
- **Style:** conversational. Gemini edits take plain instructions ("change X, keep Y"). Imagen-style generation wants one or two descriptive sentences with style and camera terms.
- **Params:** aspect and number of images are UI or API settings. No weights, and negative prompts are limited or missing, so say what to leave out in positive terms.
- **Length:** one focused paragraph.
- **Editing:** works well over several turns. Make one change per turn and restate what stays.

### Any other model
Ask: plain sentences or tags? A negative prompt field? Weights? Is aspect a flag or a setting? Can it take an image for editing? Write the first set in the closest style and let them correct it.

### Habits that work everywhere
- Be concrete. "Low sun from camera left, long shadows" beats "dramatic lighting". Lens words ("35mm, shallow depth of field, eye level") help a lot for photoreal images.
- Say what the image is for when it changes the layout (thumbnail, poster, header crop).

## Reference: edit modes

An edit prompt says what changes and what must not. Protecting the rest matters more than the new content.

### Choosing a mode
Recommend one with a one-line reason. The user can overrule you.
- Small local fix or swap, the rest untouched → **inpaint**
- Whole-image tweak on a model that takes instructions → **instruction edit**
- New style, same layout → **img2img / restyle**
- More canvas needed → **outpaint**

### Instruction edits
Shape: **Change** (one thing) + **Keep** (an explicit list) + optional **Match** (how to blend: lighting, perspective, grain).
- One change per prompt. With stacked changes, a failure is hard to trace.
- Write the keep list even when it seems obvious ("keep face, pose, clothing and background unchanged").
- Describe the end result, not the action ("a red jacket", not "make it more red").

### Inpaint / outpaint
- **Inpaint:** describe only what appears inside the mask and how it blends in. Do not re-describe the whole image. Mask tip: reach slightly past the object's edge, soft for organic shapes and hard for objects.
- **Outpaint:** describe the new area and how it continues ("beach continues right, same low sun, wet-sand reflections"). Say which edge and how much (aspect ratio, or % or px).
- If the tool has a denoise or strength setting, suggest one as a starting point: higher to replace, lower to blend.

### img2img / restyle
- **Strength (denoise) is the main dial.** Starting points the user can adjust: about 0.2-0.4 keeps the composition and changes the surface style; about 0.4-0.6 restyles but keeps the layout; 0.6 and up treats the source as loose inspiration.
- Prompt the **target style and content**, plus which parts of the composition to keep.
- If they have ControlNet, a structure guide or style references, suggest them to hold the layout while pushing the style harder.

## Reference: session card

Post this once, as a single code block, so everything copies in one go. The final prompt, params and model should be enough to reproduce the result.

````
IMAGE SMITH CARD
Model: <model + version/UI if known> | Mode: create | edit (<type>)
Brief: <one line: subject, style, mood, camera, constraints, use, refs>
Keep (edit only): <what must not change>

FINAL
Prompt: <final prompt>
Params: <aspect, weights, negative, strength, seed>
Notes: <anything needed to reproduce, e.g. mask or seed>
````