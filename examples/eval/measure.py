#!/usr/bin/env python3
"""Measure the saved eval texts with antislop_lint at one fixed ruler (level 80).
Usage: python3 examples/eval/measure.py
"""
import importlib.util, pathlib, re, statistics

here = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lint", here.parent.parent / "skills/antislop-writing/scripts/antislop_lint.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

ORDER = ["baseline", "level-100-before-fix", "level-100", "level-80", "level-60", "level-40"]
print(f"{'task':<18}{'condition':<21}{'words':>6}{'avg sent':>9}{'max sent':>9}{'headers':>8}{'bold':>5}{'warn@80':>8}{'per100w':>8}")
for task, mode in (("A-chat-reply", "reply"), ("B-readme-section", "document"), ("C-readme-intro", "document"), ("D-chat-adr", "reply")):
    for cond in ORDER:
        p = here / task / f"{cond}.md"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        r = m.lint(text, 80, mode)
        masked = m.mask_code(text)
        lens = []
        for kind, l, body in m.blocks(m.strip_emphasis(masked)):
            if kind == "heading":
                continue
            for s in m.sentences(body):
                lens.append(m.count_words(s)[0])
        headers = len(re.findall(r"^\s{0,3}#{1,6}\s", masked, re.M))
        bold = len(re.findall(r"\*\*[^*\n]+\*\*", masked))
        s = r["summary"]
        print(f"{task:<18}{cond:<21}{s['words']:>6}{(statistics.mean(lens) if lens else 0):>9.1f}{max(lens) if lens else 0:>9}{headers:>8}{bold:>5}{s['warnings']:>8}{s['warnings_per_100_words']:>8}")
