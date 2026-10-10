# English text

Read this file when you write or edit English. Rule IDs (A1, D2, E1) come from `levels.md`.

## Source

The English rules come from ASD-STE100 Simplified Technical English through the `simple-english` skill by AminBlg (MIT). That skill paraphrases Issue 9 of the standard. This repository does not copy the standard or its dictionary. ASD-STE100 is a trademark of ASD. No tool can certify compliance.

## Level to `simple-english` mode

| Level | What to do |
|---:|---|
| 100 | Load `simple-english`, mode **Strict**. Read its `references/strict-vocabulary.md`. Limits: 20 words for an instruction, 25 for a description. |
| 80 | Load `simple-english`, mode **Plain** (its default). Limit: 25 words. |
| 60 | Use rules A, B, C of `levels.md`. Load `simple-english` only for a runbook or a procedure. Limit: 30 words. |
| 40 | Use rules A and B. Limit: 40 words. |
| 20 | Use rules A only. |

Without `simple-english` installed, use the compact rules below.

## Compact rules

From level 20 (A):

- Answer in the first sentence. No "Great question", no "I hope this helps".
- State the fact, not its importance. Delete: crucial, robust, seamless, powerful, comprehensive, leverage, "it is worth noting", "in order to".
- No "not just X, but Y". No "Let's dive in". No "In conclusion".
- No stacked hedges (might, could, perhaps, arguably). Keep one real caveat.
- No bold lead-ins, no emoji bullets, no decorative triplets.
- Do not invent facts, numbers, links, or quotes. Do not touch code, commands, names, or quoted errors.

From level 60 (C):

- One word, one meaning, for the whole text. Use `make sure` for check, verify, confirm, ensure. Do not rotate synonyms.
- No noun chain of three or more nouns. Use a preposition or a verb.
- Condition before command, with a comma: "If the build fails, read the log."
- Name the host, the flag, or the file. Do not write "configure the system".

From level 80 (D):

- Active voice. Name the actor: "You run the migration."
- Simple tenses. No present perfect ("has completed" → "completed"). No "-ing" verb after a comma.
- Modals: `can`, `will`, `must`. No `should`, `would`, `may`, `might`, `could`. A required "should" becomes "must". An optional one goes away.
- Keep articles and "that". No contractions.
- No semicolons. No em-dashes. Write two sentences or name the relation ("because", "but").
- Warnings: command or condition first, then the risk.
- Chat answer: prose; a list only for steps or three or more parallel items.

From level 100 (E):

- Strict STE vocabulary from `simple-english`.
- 20 words per instruction, 25 per description.
- No lists in a chat answer except steps. No headings. No bold.

## English points that differ from Russian

- The em-dash is a slop signal in English and normal punctuation in Russian. In English text, apply the ban from level 80. At levels 40 and 60, allow at most one per 200 words. At level 20, do not check.
- English needs articles. Telegraph style ("Restart service") is not Simplified English.
- Use American spelling unless the user names another.
