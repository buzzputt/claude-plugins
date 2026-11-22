---
name: elicit
description: Ask a few short questions to find out what the person really wants, using the question widgets. Use on /elicit, on "ask me questions", "interview me", "clarify what I want", or when a request is too vague to start or too costly to guess. Skip it when the request is clear.
---

# /elicit

Find out what the person really wants by asking a few short questions. Ask about the big things, not the small ones.

Too many questions wear people out. They answer the first few with care, then click anything to get done. Four good questions beat fourteen weak ones. Keep it short: 1 to 4 questions, usually 3.

## Steps

### 1. Work out what you can first

Read the chat, any attached files, and everything the person already said. Cross off every question you can answer yourself. Only ask what would change what you make. If nothing is left, skip the questions and start the work. Say in one line what you assumed.

### 2. Boil the request down

Say what the person wants in one sentence. Everything you ask should help with that one thing.

Then look for the big gaps, the places where a wrong guess would ruin the result. Most requests have three:

- **Outcome**: what should exist when you are done?
- **Use**: who is it for, or what is it for?
- **Shape**: the one limit that matters most (length, format, tone, budget, deadline).

Only ask about gaps that are really open. Skip the rest. Ask one question per gap, and never ask about the same gap twice in different words. For each question, you should be able to say why you are asking it. If you can't, drop it.

### 3. Pick the widget

Pick the widget that fits the kind of answer. Use one widget per round.

**AskUserQuestion** is the one to use most of the time. Use it when the person is choosing between 2 to 4 options.
- Put the option you recommend first and add `(Recommended)` to it. That way the person can just say yes.
- Keep `header` to one or two words. It shows as a small tag, so name the gap (Outcome, Audience, Format).
- Add a short `description` to an option only when the label alone is unclear.
- Use `multiSelect: true` only when people can pick more than one, like "which of these matter".
- Use `preview` when it is easier to choose by looking: a rough layout, a bit of code, a sample sentence in each tone. Show it, don't explain it.
- Don't add an "Other" option. The widget adds one for you.
- You can ask up to 4 questions in one call. One call is one round.

**Visualizer elicitation form** is for answers that are more than a pick from a list: a date, a slider, a file upload, free text next to choices, or cards that work better than tags.
- Before you use it, quietly load the `elicitation` module of `mcp__visualize__read_me`, then call `mcp__visualize__show_widget`.
- Follow the module's rules: the title is "[subject] details", each item is worded as a question, no scripts, and no custom styling on the frame.
- Mix up the formats. If there are three or more groups of choices, make at least one of them cards or tiles. Use a slider instead of "1 to 5" buttons. Use a file drop box with a text box as a backup when a file could help.
- Keep it to 1 to 4 groups. A longer form is not a better form.
- The answers come back as the next message. Read them and carry on.

**Display widgets** (comparison card, product carousel, places map, image search) don't collect answers. Use one only when the person can't choose well without seeing real options. Show the options first, then ask the one question that decides it with AskUserQuestion. If words are enough, skip them.

Don't use these here: the quiz widget (it tests what people know, it doesn't collect what they want), the options card (health topics only), and the message composer.

### 4. Write the questions

- Word each one as a question from you, not a label on a form. "Who is this for?" is better than "Audience:".
- Keep each question and option short. No long intro.
- Give real choices with a clear difference. If two options mean the same thing, they are one option.
- Put the most important question first.
- Make the recommended option a good guess, so a quick "yes" still gets a useful result.
- Don't ask about something the person already told you.
- Don't end with "anything else?". The "Other" choice already covers it.

### 5. Use the answers

Get to work right away. Don't ask a second round unless an answer opens a new fork that changes the work. If it does, ask one question, not a new list. If the person skips the questions, go with the recommended options, say so in one line, and get started.

## When nobody is there

If no one is watching (a scheduled run, or the person has stepped away), don't ask. Pick the most likely meaning, say which one you picked at the top of your work, and keep going.

## Example

Request: "help me with a launch announcement"

What you can tell: nothing about the product, where it will go, or the tone.

What it boils down to: write a launch announcement. The big gaps are the audience, the channel, and the tone. You can get product details later, from a quick follow-up or the person's files.

Ask with AskUserQuestion, 3 questions:
1. Audience: Customers (Recommended) / Internal team / Press / Investors
2. Channel: Email / Blog post / Social / Slack
3. Tone, with a `preview` of one sample opening line for each option: Warm / Direct / Playful

Three questions, three big gaps, one round. Then write it.
