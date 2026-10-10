# antislop-writing

A bundle of agent skills against LLM slop. Your agent writes Russian (and English) shorter, clearer, and without stock phrases. One dial, 20 to 100%, sets how strict it is.

[Русский](README.md) · [Sources and licenses](THIRD_PARTY.md) · [Test results](examples/eval/README.md)

The idea comes from [Andrej Karpathy's post](https://x.com/karpathy/status/2105819303471976479): ask an LLM to write in ASD-STE100, and soften it ("80% of the way to ASD-STE100") because the standard is strict. This repository wraps that idea around four sources:

| What | From |
|---|---|
| Controlled English (ASD-STE100) | skill `simple-english` by [AminBlg](https://github.com/AminBlg/SimpleEnglish) |
| Simplified Technical Russian | [GOST R 58049-2017](https://meganorm.ru/Data/661/66114.pdf), section 8.2 |
| Russian editing and LLM tells | [redaktura-skills](https://github.com/N1arko/redaktura-skills) by Lyudmila Sarycheva and Nikita Arkhipov |
| Lossless compression of documents | [lossless-doc-compress](https://github.com/ML-SystemDesign/MLSystemDesign/tree/main/skills/lossless-doc-compress) by Babushkin and Kravchenko |

The skill `antislop-writing` adds the glue and the dial. The other eight skills sit in this repository as unmodified copies, so one install brings everything.

## Install

```bash
npx github:apgruzdev/antislop-writing
```

It does two things.

1. Installs nine skills into each agent it finds on your machine. Supported: Claude Code, Codex, OpenCode, Gemini CLI, Cursor, GitHub Copilot, Windsurf, and 70+ more through [`skills`](https://github.com/vercel-labs/skills).
2. Adds a short always-on rule (1.8k characters) to the global instruction file of each agent. The rule tells the agent to call the skill for any text. It also carries the most important rules when the skill does not load.

The block sits between `antislop-writing:begin` and `antislop-writing:end` comments. Your own text in those files stays untouched. Restart the agent after the install.

You need Node.js 18+ and git. The `npx skills` tool sends anonymous telemetry. Set `DISABLE_TELEMETRY=1` to turn it off.

```bash
npx github:apgruzdev/antislop-writing --level 60       # another level (default 80)
npx github:apgruzdev/antislop-writing --project        # this project only: ./AGENTS.md and project skills
npx github:apgruzdev/antislop-writing --skills-only
npx github:apgruzdev/antislop-writing --dry-run
npx github:apgruzdev/antislop-writing status
npx github:apgruzdev/antislop-writing uninstall
```

Skills only: `npx skills add apgruzdev/antislop-writing`. Do not use `--all`: it creates directories for all 79 agents, installed or not.

Claude Code plugin. A `SessionStart` hook loads the rule, and updates come through the marketplace:

```bash
claude plugin marketplace add apgruzdev/antislop-writing
claude plugin install antislop-writing@antislop-writing
```

Set the level with `ANTISLOP_LEVEL=60` or the file `~/.config/antislop-writing/level`. Pick the plugin or `npx skills`, not both. Together they list each skill twice.

No skill support (ChatGPT, web Claude, web Gemini): paste [`prompts/mini.md`](prompts/mini.md) into your custom instructions. It has 817 characters, which fits the ChatGPT Free limit of 1,500. The full version is [`prompts/kernel.md`](prompts/kernel.md).

## The dial

| Level | Name | For | Sentence |
|---:|---|---|---:|
| 100 | Strict | Procedures, runbooks, safety, text for translation | 20 words |
| **80** | **Almost strict** | Answers, explanations, READMEs, docs (default) | 25 |
| 60 | Clear | Emails, reports, articles | 30 |
| 40 | Lively | Posts, newsletters, promo | 40 |
| 20 | Minimum | Fiction and personal prose: remove clichés only | no limit |

Rules A to E switch on at their own level and stay on above it.

- A (from 20): answer first, fact instead of praise, no labels like "an important nuance", no "not X but Y" more than once per 1,000 words, no filler, no moral at the end.
- B (from 40): a person acts, not a process. Define a term at first use.
- C (from 60): one word per meaning, condition before command.
- D (from 80): imperative steps, warning command first, no contractions, no em-dash, `can/will/must`.
- E (at 100): 20-word limit, strict STE vocabulary.

The numbers 25, 30, and 40 words are the author's calibration. The standards do not give them. Full ladder with sources: [`levels.md`](skills/antislop-writing/references/levels.md). Where the sources disagree, and how the conflicts are resolved: [`conflicts.md`](skills/antislop-writing/references/conflicts.md).

## What the first test run showed

Four tasks, one run per condition ([`examples/eval`](examples/eval/README.md)). With the skill, a chat answer lost its headings (8 to 0) and bold text (10 to 0), and got 17 to 32% shorter. In one task the baseline invented a benefit the prompt never gave ("easy to search by date"). The skill version did not.

Limits of the test: one run per condition, a linter written from the same rules as the skill, no human readers, one model family. The dial changes register and format more than sentence length.

## Platforms

Tested live: OpenCode. It finds the skills and reads the level in `AGENTS.md`. Tested offline: Claude Code. Skills and plugin install into an isolated config, strict plugin validation passes, and the hook runs by hand. The live Claude session was not tested because the login expired. File layout checked against the docs but not run: Codex, Gemini CLI, Windsurf, Cursor, GitHub Copilot.

## Limits

- This is not certification. No tool certifies ASD-STE100 or GOST compliance. Russian has no closed dictionary. GOST R 58049-2017 covers translation of aviation documentation. Its section 8.2 is the nearest analogue of STE, not an equivalent.
- This does not defeat AI detectors. They are unreliable. The goal is readable text.
- A model can break a rule. The skill raises the odds, not the guarantee.
- If you already installed `redaktura` or the other skills from upstream, this install replaces them with copies of the same content.

## Sources

Full list with licenses, commits, and what was taken: [THIRD_PARTY.md](THIRD_PARTY.md). ASD-STE100 is a trademark of ASD. This repository is not affiliated with or endorsed by ASD. GOST R 58049-2017 is © Standartinform. Its rules are paraphrased here, not copied.

## Development

```bash
npm test
node scripts/sync-upstream.mjs --check    # vendored skills equal the pinned upstream commits
node scripts/sync-upstream.mjs --update   # move the pins to the current upstream heads
```

## License

MIT for the original work. Each vendored skill keeps its own license in its directory. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md).
