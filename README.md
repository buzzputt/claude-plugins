# claude-plugins

A small Claude Code plugin marketplace. Each skill is its own plugin, so you can install just the ones you want.

## Install

Add the marketplace once:

```
/plugin marketplace add buzzputt/claude-plugins
```

Then install any plugin:

```
/plugin install elicit@buzzputt-plugins
```

## Plugins

| Plugin | What it does | How to use it |
|---|---|---|
| `elicit` | Asks a few short questions to find out what you really want before starting. | `/elicit`, or "ask me questions" |
| `image-smith` | A workshop for writing and refining image-generation and image-editing prompts. | `/image-smith` |
| `sift-the-web` | Turns your question into better searches, skips junk domains, and tells you how solid the answer is. | `/sift-the-web <your question>` (command only) |
| `osu-pattern-lab` | Builds a personal osu!standard pattern library from your beatmaps and suggests patterns from a plain-language vibe. | Upload beatmaps, then describe the feel you want |

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json      the list of plugins
├── elicit/
│   └── SKILL.md
├── image-smith/
│   └── SKILL.md
├── sift-the-web/
│   ├── SKILL.md
│   └── blocklist.txt
├── osu-pattern-lab/
│   ├── SKILL.md
│   ├── references/
│   │   ├── schema.md
│   │   └── vibe-to-features.md
│   └── scripts/
│       ├── card.py
│       ├── ingest.py
│       ├── library.py
│       ├── mutate.py
│       ├── osu_lib.py
│       └── search.py
├── LICENSE
└── README.md
```

## License

[MIT](LICENSE)
