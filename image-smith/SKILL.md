---
name: "image-smith"
description: "Human-in-the-loop workshop for creating and refining image-generation and editing prompts. Trigger only with /image-smith."
---

# Image Smith

A workshop for writing image prompts, from scratch or to edit an image. Write each prompt as clear, descriptive, natural language that works in any image tool. Offer a few clearly different options, and say what works. The user decides what they want and when it is good enough. Keep handoffs cheap: if feedback takes effort, people stop giving it.

**Models.** Do not assume a model and do not ask which one to use. Write a general-purpose prompt. If the user names a model or tool (in the request, in their feedback, or by attaching its output), honor it for the rest of the session: follow that model's prompt style, length and settings as best you know them. Say when you are going from memory, and check current details if search is available.

## Flow

### 1. Intake

Ask in one `AskUserQuestion` call (plain text if it isn't available). Skip anything already answered. Three questions at most.

- **Create or edit?** Skip if an image is attached or they already said. An attached image means edit, unless they call it a style reference.
- **Gaps in the brief.** A full brief covers subject, style, mood, composition and camera, constraints (aspect ratio, brand, no-gos), and intended use. Ask only about what is missing, with concrete options ("four specific styles", not "what style?").

Take reference images if they offer them. Then restate the brief in two lines for correction. The corrected version is **the brief**.

**Edit mode.** Before writing any prompt, describe the image back in a few lines: subject, composition, lighting, palette, style, text, and fragile spots like hands, faces and small text. Send it in one message with the brief, a proposed **keep list** (what must not change), and a recommended edit type with a one-line reason (see **Reference: edit types**). They correct it once. Carry the keep list into every variant.

### 2. Two or three variants per round

Write 2 or 3 prompts that differ along real axes: style, camera, lighting, composition, how abstract or literal. Variants that differ only in adjectives give the user nothing to choose between.

List the axes you could vary and keep the set that differs most. Give three only if the third is clearly different from the other two. Otherwise give two. Never pad.

In edit mode, vary how strongly you protect the keep list, how specific the change is, or what fills the gap, and name the trade-off.

**Edit mode: preservation check before showing.** Every edit prompt must contain an explicit Keep clause that covers the whole keep list. Before you show a set, run the **before-sending check** in **Reference: preservation checks** on each prompt. Fix any prompt that fails, and never show one that does. Add a one-line "Preservation: passed" to each variant so the user can see it was done.

For each variant:
- **Label and the axis it explores**
- **Prompt** in a code block, in plain descriptive sentences
- **Settings** only when the brief or a named model needs them (aspect ratio, size, anything the model requires)
- **Why**, in one line, so they can fix the thinking and not just the output

End with one question: pick one, mix ("subject from A, lighting from C"), or hand-edit. Offer nothing else.

Once they pick, remind them in one line that they can generate it and upload the result here, so you can check it against the variant they chose.

### 3. Review the result, then revise

**Review an uploaded result.** When the user uploads a generated image, compare it against the variant they chose: its prompt and the brief. In edit mode, also run the **after-result check** in **Reference: preservation checks**, comparing the result with the original, and report its result before anything else. Keep it short:
- **Matches:** what came out as asked.
- **Misses:** what is missing, wrong or different from the prompt, such as subject, style, lighting, composition, text or the keep list. Be plain about it, and check the fragile spots (hands, faces, small text).
- **Likely cause:** one line on which words in the prompt may have caused each miss.

Then offer a revised prompt that fixes the misses, shown as a short diff, or ask which miss matters most if there are several. If it is close enough, say so and offer to close. If the user mentions what they think is wrong, treat that as feedback below.

**Turn feedback into changes.** Turn loose feedback ("too busy", "feels cold") into concrete changes, and show a short diff of what changed and why. If it could mean two things, ask first with a quick multiple choice ("too busy": fewer subjects, calmer background, or simpler lighting?). If it is clear, apply it. Never rewrite silently.

Then offer a new set of 2 or 3, or refine just one prompt if they are settling on it.

Also:
- When you add something to a prompt, cut something, so it stays short and focused.
- If feedback pulls away from the brief, say so plainly. Changing direction is fine if it is their choice.
- If a prompt names a living artist, trademark, franchise character or real person, flag it briefly. Say whether it matters for their use (personal vs. commercial) and offer a descriptive alternative, such as the visual traits instead of the name. Then let them decide. Use normal judgment for real people and harmful content.

### 4. Close

When they lock a prompt, or ask for a summary, post the session card as one code block they can copy (see **Reference: session card**). Then add one line: if they generate it and upload the result, you will review it against the card and suggest fixes. Then stop. A line on anything else needed at generation time is fine.

---

## Reference: writing the prompt

- **Write in full, plain sentences.** Describe the picture the way you would to an illustrator: what is in it, where, and how it looks. One short paragraph is usually enough.
- **Lead with the subject.** Then add setting, style, mood, lighting and camera, roughly in that order.
- **Be concrete.** "Low sun from camera left, long shadows" beats "dramatic lighting". Lens words ("35mm, shallow depth of field, eye level") help a lot for photoreal images.
- **Say what you want, not what you don't.** "An empty, uncluttered background" works better than "no clutter". Add a short "avoid" line only when something specific keeps showing up.
- **Quote any text that must appear.** Give the exact words, plus the lettering style and where it sits.
- **Say what the image is for** when it changes the layout (thumbnail, poster, header crop).

## Reference: edit types

An edit prompt says what changes and what must not. Protecting the rest matters more than the new content.

### Choosing a type
Recommend one with a one-line reason. The user can overrule you.
- Small local fix or swap, the rest untouched → **local change**
- Whole-image tweak (lighting, color, mood) → **overall change**
- New style, same layout → **restyle**
- More canvas needed → **extend**

### How to write the prompt
Shape: **Change** (one thing) + **Keep** (an explicit list) + optional **Match** (how to blend: lighting, perspective, grain).
- One change per prompt. With stacked changes, a failure is hard to trace.
- Write the keep list even when it seems obvious ("keep face, pose, clothing and background unchanged").
- Describe the end result, not the action ("a red jacket", not "make it more red").

### Notes by type
- **Local change:** describe only what appears in the changed area and how it blends in. Do not re-describe the whole image. If the tool uses a selection or mask, say what to select.
- **Extend:** describe the new area and how it continues ("beach continues right, same low sun, wet-sand reflections"). Say which edge and how much.
- **Restyle:** describe the target style, and which parts of the composition to keep.
- If the tool has a strength or similarity setting, suggest a starting point: higher to replace, lower to blend.

## Reference: preservation checks

Edits fail most often by changing things that were supposed to stay. Run both checks every time you edit an image. They are not optional.

### Before-sending check (on each prompt)
- **Keep clause present:** the prompt says what stays unchanged, in words.
- **Every keep item named:** each item on the keep list appears in the Keep clause. Add any that are missing.
- **One change only:** the prompt asks for a single change. Split it if it asks for more.
- **No conflicts:** nothing in the Change or Match parts contradicts the keep list. "Add a sunset" conflicts with "keep the lighting", so resolve it first.
- **Fragile spots covered:** if hands, faces or small text are in the image and are not being changed, they are on the keep list.

### After-result check (on an uploaded result)
Go through the original's keep list one item at a time and mark each as **kept**, **changed** or **can't tell**. Also scan for unrequested changes the keep list did not mention: shifted framing or crop, different colors or grain, altered faces, hands or text, objects added or removed. Report the result as a short list, naming every item that changed. If something changed, make fixing it the first thing the revised prompt does, by strengthening or narrowing the Keep clause, before adding anything new.

## Reference: session card

Post this once, as a single code block, so everything copies in one go. The final prompt and any settings should be enough to reproduce the result.

````
IMAGE SMITH CARD
Model: <only if the user named one> | Mode: create | edit (<type>)
Brief: <one line: subject, style, mood, camera, constraints, use, refs>
Keep (edit only): <what must not change>
Preservation (edit only): <before-sending check passed | result check: kept / changed items>

FINAL
Prompt: <final prompt>
Settings: <only if needed: aspect ratio, size, and so on>
Notes: <anything needed to reproduce>
````
