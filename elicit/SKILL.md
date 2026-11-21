---
name: elicit
description: Ask a few focused questions about the person's core intent via the question widgets. Use on /elicit, on "ask me questions", "interview me", "clarify what I want", or when a request is too vague to start or costly to guess. Skip when the request is clear.
---

# /elicit

Get to the person's intent with a few focused questions. Ask about the core, not the edges.

Many questions from many angles tire people out. They answer the first few well, then start clicking anything. Four good questions beat fourteen mediocre ones.

## The ten words

Every question set should be all of these:

| Word | In practice |
|---|---|
| Focused | One intent per set. Everything asked serves it. |
| Essential | Ask only what would change what you build. |
| Targeted | Each question hits one specific unknown. |
| Core | Go for goal, audience, and shape. Skip trivia. |
| Concise | Short question. Short options. No preamble. |
| Purposeful | You can say why each question exists. |
| Pointed | Closed choices with a clear fork, not open mush. |
| Lean | 1 to 4 questions. Usually 3. |
| Central | Start with the one that matters most. |
| Distilled | Boil the request down first, then ask. |

## Steps

### 1. Infer first

Read the conversation, attachments, and anything already said. Throw out every question you can answer yourself. If nothing is left, skip asking and start the work. Say in one line what you assumed.

### 2. Distill the intent

Name the request in one sentence. Then find the core areas where a wrong guess would ruin the result. Most intents have three:

- **Outcome**: what should exist at the end?
- **Use**: who or what is it for?
- **Shape**: the one constraint that bounds it (length, format, tone, budget, deadline).

Pick the areas that are actually unknown. Drop the rest. One question per area. Never ask two questions about the same area from different angles.

### 3. Pick the widget

Match the widget to the answer type. Use the strongest one that fits, and no more than one per round.

**AskUserQuestion** is the default. Use it for any choice among 2 to 4 options.
- Put the recommended option first and tag it `(Recommended)`. This lets the person say yes quickly.
- Keep `header` to a word or two. It is a chip, so it should name the core area (Outcome, Audience, Format).
- Add a short `description` to an option only when the label alone is ambiguous.
- Use `multiSelect: true` only when options truly stack, like "which of these matter".
- Use `preview` when options are easier to judge by seeing them: a layout sketch, a code shape, a sample sentence in each tone. Show, don't explain.
- Never add an "Other" option. The widget adds it.
- Ask up to 4 questions in one call. One call, one round.

**Visualizer elicitation form** is for answers that are not just choices: a date, a slider, a file upload, free text next to choices, or a picker where cards or preview tiles beat chips.
- Load the `elicitation` module of `mcp__visualize__read_me` first, silently, then call `mcp__visualize__show_widget`.
- Follow the module's rules: header title is "[subject] details", questions are phrased as questions, zero scripts, no restyled chrome.
- Vary the formats. With three or more choice groups, make at least one cards or tiles. Use a slider instead of "1 to 5" pills. Use a dropzone with a textarea fallback when a file could help.
- Keep it to the same 1 to 4 groups. A bigger form is not a better form.
- The answers come back as your next message. Parse them and go.

**Display widgets** (comparison card, product carousel, places map, image search) are not input widgets. Use one only when the person cannot choose well without seeing real options. Show the options first, then ask the single deciding question with AskUserQuestion. Skip them when words will do.

Not relevant here: the quiz widget (it grades knowledge, it doesn't collect preferences), the options card (health topics only), and the message composer.

### 4. Write the questions

- Phrase each as a question from you, not a field label. "Who is this for?" beats "Audience:".
- Options are real forks. Two options that mean the same thing is one option.
- Make the recommended option a good guess, so a lazy yes still lands somewhere useful.
- No question that restates what the person already said.
- No "anything else?" catch-all. The "Other" path covers it.

### 5. Act on the answers

Proceed right away. Don't ask a second round unless an answer opens a fork that changes the work, and then ask one question, not a new list. If the person skips, take the recommended options, say so in one line, and go.

## Unattended runs

If nobody is watching (scheduled run, person stepped away), don't ask. Take the most reasonable reading, say which one at the top of the work, and carry on.

## Quick example

Request: "help me with a launch announcement"

Inferred: nothing about product, channel, or tone is known.

Distilled intent: write a launch announcement. Core unknowns are audience, channel, and tone. Product details can come from a quick follow-up or the person's files.

AskUserQuestion with 3 questions:
1. Audience: Customers (Recommended) / Internal team / Press / Investors
2. Channel: Email / Blog post / Social / Slack
3. Tone, with a `preview` of one sample opening line per option: Warm / Direct / Playful

Three questions, three core areas, one round. Then write it.
