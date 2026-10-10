#!/usr/bin/env python3
"""Эвристический линтер нейрослопа для русского и английского текста.

Heuristic linter for LLM-style text in Russian and English. Python 3.8+, standard library only.

    python3 antislop_lint.py [--level 20|40|60|80|100] [--mode document|reply] [--skip-quoted] [--json] [--strict] [FILE ...]
    cat draft.md | python3 antislop_lint.py --level 80

Линтер ловит механические признаки: длину предложений, шаблонные обороты, декор.
Он не понимает смысл и не заменяет чтение текста. Номера правил (A1, D1, E1) смотри в references/levels.md.
Exit code: 0; с --strict — 1, если есть замечания уровня warn.
"""

import argparse
import json
import math
import re
import statistics
import sys

LEVELS = (20, 40, 60, 80, 100)
CAPS = {100: ("E1", 20), 80: ("D1", 25), 60: ("C6", 30), 40: ("B10", 40), 20: (None, None)}

FLAGS = re.IGNORECASE | re.UNICODE


def snap_level(n):
    """Round to the nearest step; a tie rounds down (90 -> 80)."""
    best = None
    for step in LEVELS:
        d = abs(step - n)
        if best is None or d < best[0]:
            best = (d, step)
    return best[1]


# --------------------------------------------------------------------------- text preparation

def _blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def _fill(m):
    # Digits count as one word and are neither Cyrillic nor Latin letters.
    return "0" * len(m.group(0))


def mask_code(text):
    """Blank out code and metadata. Offsets and newlines stay the same."""
    text = re.sub(r"\A---\n.*?\n---[ \t]*(?:\n|\Z)", _blank, text, flags=re.S)
    text = re.sub(r"```.*?```", _blank, text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", _blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", _blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]+`", _fill, text)
    text = re.sub(r"https?://[^\s)>\]]+", _fill, text)
    return text


def strip_emphasis(text):
    """Blank emphasis markers so that patterns match across them. Length stays the same."""
    text = re.sub(r"(\*\*|__)", "  ", text)
    text = re.sub(r"(?<![\w*])[*_](?=\S)|(?<=\S)[*_](?![\w*])", " ", text)
    return text


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
TABLE = re.compile(r"^\s*\|")
RULE_LINE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def blocks(plain):
    """Split into blocks: ('heading'|'item'|'para', first_line, text)."""
    out = []
    cur = None
    for i, line in enumerate(plain.split("\n"), start=1):
        if not line.strip() or RULE_LINE.match(line):
            if cur:
                out.append(cur)
                cur = None
            continue
        if TABLE.match(line):
            if cur:
                out.append(cur)
                cur = None
            continue
        if HEADING.match(line):
            if cur:
                out.append(cur)
                cur = None
            out.append(("heading", i, HEADING.sub("", line).strip()))
            continue
        m = LIST_ITEM.match(line)
        if m:
            if cur:
                out.append(cur)
            cur = ("item", i, line[m.end():])
            continue
        if cur and cur[0] == "item" and line.startswith((" ", "\t")):
            cur = ("item", cur[1], cur[2] + "\n" + line.strip())
            continue
        line = re.sub(r"^\s*>\s?", "", line)
        if cur and cur[0] == "para":
            cur = ("para", cur[1], cur[2] + "\n" + line.strip())
        else:
            if cur:
                out.append(cur)
            cur = ("para", i, line.strip())
    if cur:
        out.append(cur)
    return out


_ABBR = re.compile(
    r"\b(т\.\s?е|т\.\s?к|т\.\s?н|т\.\s?ч|см|рис|табл|гл|стр|ул|им|напр|"
    r"e\.g|i\.e|vs|Mr|Mrs|Ms|Dr|approx|No|Fig|Inc|Ltd)\.",
    FLAGS,
)
# These can also end a sentence: protect the dot only if no capital letter follows.
_ABBR_MAYBE_END = re.compile(
    r"\b(т\.\s?д|т\.\s?п|и\s?др|и\s?пр|тыс|млн|млрд|руб|etc)\.(?!\s+(?-i:[A-ZА-ЯЁ]))",
    FLAGS,
)
_INITIALS = re.compile(r"\b([A-ZА-ЯЁ])\.(?=\s?[A-ZА-ЯЁ]\b)")
_DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")
_SPLIT = re.compile(r"(?<=[.!?…])[\"»”)\]]*\s+(?=[\"«“(\[]?[A-ZА-ЯЁ0-9])")
_PH = "\u0001"


def sentences(text):
    t = text.replace("\n", " ")
    t = _ABBR.sub(lambda m: m.group(0)[:-1] + _PH, t)
    t = _ABBR_MAYBE_END.sub(lambda m: m.group(0)[:-1] + _PH, t)
    t = _INITIALS.sub(lambda m: m.group(1) + _PH, t)
    t = _DECIMAL.sub(_PH, t)
    parts = [p.replace(_PH, ".").strip() for p in _SPLIT.split(t)]
    return [p for p in parts if re.search(r"\w", p)]


_QUOTED = re.compile(r"«[^»]*»|“[^”]*”|\"[^\"]*\"")
_PAREN = re.compile(r"\([^()]*\)")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)+|[^\W_]+(?:[-'’/][^\W_]+)*")


def count_words(sentence):
    """Count like GOST R 58049-2017 8.2.5.1: a quote is one word, a number is one word,
    text in brackets is a separate sentence. Returns (words, [bracketed texts])."""
    s = _QUOTED.sub(" Q ", sentence)
    paren = _PAREN.findall(s)
    s = _PAREN.sub(" ", s)
    return len(_TOKEN.findall(s)), [p[1:-1] for p in paren]


def snippet(s, n=70):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def cyr_ratio(s):
    cyr = len(re.findall(r"[А-Яа-яЁё]", s))
    lat = len(re.findall(r"[A-Za-z]", s))
    tot = cyr + lat
    return cyr / tot if tot else 0.0


# --------------------------------------------------------------------------- patterns

PATTERNS = []  # (rule, min_level, severity, regex, message)


def add(rule, level, severity, pattern, message, flags=FLAGS):
    PATTERNS.append((rule, level, severity, re.compile(pattern, flags), message))


# A1: openers and closers
add("A1", 20, "warn", r"\b(?:отличный|хороший|интересный|классный)\s+вопрос\b", "ритуальное начало: начни с ответа")
add("A1", 20, "warn", r"\bдавайте\s+(?:разберёмся|разберемся|разберём|разберем|поговорим|погрузимся)\b", "ритуальное начало: начни с ответа")
add("A1", 20, "warn", r"\bнадеюсь,?\s+(?:это|ответ|информация|мой\s+ответ)?\s*(?:было\s+|будет\s+)?(?:помо|полез)\w*", "ритуальная концовка: убери")
add("A1", 20, "warn", r"\b(?:обращайтесь|дайте\s+знать|пишите,?\s+если)\b", "ритуальная концовка: убери")
add("A1", 20, "warn", r"\bесли\s+(?:у\s+вас\s+)?(?:возникнут|появятся|есть)\s+(?:ещё\s+|еще\s+)?вопросы\b", "ритуальная концовка: убери")
add("A1", 20, "warn", r"\bgreat question\b|\bi hope (?:this|that) helps\b|\blet me know if\b|\bfeel free to\b|\blet'?s dive (?:in|into)\b", "ritual opener or closer: delete")
add("A1", 20, "warn", r"^[ \t]*(?:certainly|absolutely|sure thing|of course)[!,.]", "ritual opener: start with the answer", FLAGS | re.M)

# A2: empty evaluation
add("A2", 20, "warn", r"\b(?:крайне|максимально|невероятно|поистине|исключительно|бесшовн\w+|революционн\w+|инновационн\w+|передов\w+)\b", "оценка вместо факта: дай число или пример")
add("A2", 20, "warn", r"\b(?:мощн(?:ый|ая|ое|ые|ого|ым|ых|ую)|ключев(?:ой|ая|ое|ые|ого|ым|ых|ую))\b", "оценка вместо факта")
add("A2", 20, "info", r"\b(?:очень|значительно|существенно|действительно|комплексн\w+|эффективн\w+|качественн\w+|уникальн\w+)\b", "возможная пустая оценка (в «уникальный ключ» это термин)")
add("A2", 20, "warn", r"\b(?:delve[sd]?|leverag(?:e|es|ed|ing)|seamless(?:ly)?|robust|crucial|pivotal|tapestry|testament|game[- ]changer|cutting[- ]edge|revolutioni[sz](?:e|es|ed|ing))\b", "slop word: state the fact")
add("A2", 20, "info", r"\b(?:simply|powerful|comprehensive|in order to|extremely|incredibly)\b", "possible empty word")

# A3: labels and pointers
add("A3", 20, "warn", r"\b(?:важный\s+нюанс|честная\s+оговорка|честно\s+говоря|неприятная\s+правда|хорошая\s+новость|ключевой\s+момент|простой\s+вывод|самое\s+интересное|и\s+вот\s+что\s+важно|но\s+главное(?:\s+даже\s+не\s+это)?)\b", "ярлык-анонс: оставь только содержание")
add("A3", 20, "warn", r"\bhere'?s the (?:thing|catch)\b|\bthe (?:real )?truth is\b|\bimportantly,|\bit'?s worth noting\b|\bit is worth noting\b|\bworth noting that\b|\bkey takeaway\b", "label: delete it and keep the content")

# A4: this one is always banned, the rest is counted in lint()
add("A4", 20, "warn", r"\bэто\s+не\s+про\b", "«это не про X» запрещено всегда")

# A5: chancellery and cliches
add("A5", 20, "warn", r"\b(?:является|являются|являлся|являлась|являлось|являлись)\b", "канцелярит: «это» или тире")
add("A5", 20, "warn", r"\bосуществля\w+|\bосуществит\w+|\bосуществлен\w+", "канцелярит: простой глагол")
# Plural «данные» is the noun "data": not flagged.
add("A5", 20, "warn", r"\bданн(?:ый|ая|ое|ого|ому|ом|ой|ую)\b", "канцелярит: «этот»")
add("A5", 20, "warn", r"\bв\s+рамках\b|\bв\s+целях\b|\bна\s+сегодняшний\s+день\b|\bв\s+современном\s+мире\b|\bв\s+эпоху\b|\bпредставляет\s+собой\b|\bв\s+связи\s+с\s+тем,?\s+что\b", "штамп: перепиши проще")
add("A5", 20, "warn", r"\bиграет\s+(?:важную|ключевую|огромную|значительную|большую)\s+роль\b|\bширок(?:ий|ого|им)\s+спектр\b|\bкомплексн\w+\s+подход\b", "штамп: назови конкретику")
add("A5", 20, "warn", r"\bin today'?s (?:fast[- ]paced|digital|ever[- ]changing)\b|\bever[- ]evolving\b|\bin the realm of\b", "cliché: delete")

# A6: hedges (cascade is checked per sentence in lint())
HEDGE = re.compile(r"\b(?:может\s+быть|возможно|как\s+правило|в\s+определ[её]нной\s+степени|в\s+некоторой\s+степени|во\s+многом|в\s+какой-то\s+степени|вероятно|скорее\s+всего|perhaps|arguably|possibly|potentially|might|could\s+potentially)\b", FLAGS)

# A7: formulaic endings
add("A7", 20, "warn", r"\bв\s+заключение\b|\bподводя\s+итог\w*|\bв\s+конечном\s+итоге\b|\bглавное\s+—\s+начать\b|\bin conclusion\b|\bto sum up\b|\bat the end of the day\b|\bultimately,?\s+it comes down to\b", "формульная концовка: закончи фактом")
add("A7", 20, "info", r"\bтаким\s+образом\b|\bв\s+итоге\b", "возможная формульная концовка")

# A8: decor
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\u2705\u274C\uFE0F]+")
BOLD_LEAD = re.compile(r"^[ \t]*(?:(?:[-*+]|\d+[.)])\s+)?\*\*[^*\n]{1,60}?(?:[:.\-—–]\*\*|\*\*\s*[:.\-—–])", re.M)
add("A8", 20, "info", r"\b[а-яё]{3,}о,\s+[а-яё]{3,}о\s+и\s+[а-яё]{3,}о\b", "тройка наречий по шаблону: оставь один точный признак")

# B9: parasite intro words
add("B9", 40, "info", r"\b(?:кстати|собственно|как\s+известно|стоит\s+отметить|следует\s+отметить|необходимо\s+отметить|если\s+честно|по\s+сути|в\s+принципе|важно\s+(?:понимать|отметить|помнить))\b", "вводное слово-паразит: убери, если смысл цел")

# B2: chancellery passive
add("B2", 60, "info", r"\b(?:производится|проводится|выполняется|подготавливается|осуществляется)\b", "страдательная форма: назови, кто действует, или используй неопределённо-личную")

# D2: modal + infinitive in instructions
add("D2", 80, "info", r"\b(?:необходимо|следует|нужно|рекомендуется|желательно)\s+[а-яё]+(?:ть|ти|чь)(?:ся)?\b", "если это инструкция: императив во мн. числе, глагол первым")

# D6: loan words
add("D6", 80, "info", r"\b(?:имплементир\w+|имплементаци\w+|ресёрч\w*|ресерч\w*|инсайт\w*)\b", "иностранное слово: есть русское равнозначное?")

# English D rules
add("EN", 80, "warn", r"\b(?:should|would|may|might|could)\b", "modal: use can, will, or must; delete an optional one")
add("EN", 80, "warn", r"\b(?:\w+n't|\w+'re|\w+'ve|\w+'ll|\w+'d|\w+'m|it's|that's|there's|here's|let's|what's)\b", "contraction: write the full form")
add("EN", 80, "warn", r",\s+(?:making|allowing|enabling|ensuring|providing|helping|leading|resulting|creating)\b", "-ing verb after a comma: start a new sentence")

# Noun-chain candidates (Russian)
_GEN = r"[а-яё]{4,}(?:ния|ние|ости|ость|ия|ии|ий|ов|ев|ей|ых|их|ств|ства|ки|ка|ты|ны)"
CHAIN = re.compile(r"\b" + _GEN + r"(?:\s+" + _GEN + r"){2,}\b", FLAGS)

# Antithesis candidates
ANTI = [
    re.compile(r"(?<![\w])не\s+просто\b[^.!?\n]{0,80}?,?\s+а\b", FLAGS),
    re.compile(r"(?<![\w])не\s+(?:[\w«»\-]+\s+){0,4}[\w«»\-]+,\s+а\s+[\w«»\-]+", FLAGS),
    re.compile(r"(?:^|[.!?]\s+)Не\s+(?:[\w«»\-]+\s*){1,3}\.\s+[А-ЯЁ]"),
    re.compile(r"\bnot\s+(?:just|only|merely|simply)\b[^.!?\n]{0,80}?\bbut\b", FLAGS),
    re.compile(r"\b(?:it'?s|it is|this is|that'?s)\s+not\s+(?:just\s+|only\s+)?(?:about\s+)?[^.!?\n]{1,60}?(?:,|;|—|\.)\s*(?:it'?s|it is|this is|but)\b", FLAGS),
]


def antithesis_limit(words):
    if words <= 1000:
        return 1
    if words <= 3000:
        return 2
    return 2 + math.ceil((words - 3000) / 1500)


# --------------------------------------------------------------------------- main lint


def make_finding(rule, severity, line, text, message):
    return {"rule": rule, "severity": severity, "line": line, "text": snippet(text), "message": message}


_QUOTE_SPANS = re.compile(r"«[^»\n]{1,120}»|“[^”\n]{1,120}”|\"[^\"\n]{1,120}\"")


def mask_quoted(text):
    """Blank quoted spans. Documents about slop quote the patterns as examples."""
    return _QUOTE_SPANS.sub(_blank, text)


def lint(text, level=80, mode="document", skip_quoted=False):
    level = snap_level(level)
    masked = mask_code(text)
    if skip_quoted:
        masked = mask_quoted(masked)
    plain = strip_emphasis(masked)
    findings = []

    blks = blocks(plain)
    all_sents = []  # (line, sentence, kind)
    for kind, line0, body in blks:
        if kind == "heading":
            continue
        for s in sentences(body):
            all_sents.append((line0, s, kind))

    word_total = 0
    sent_lens = []
    for line0, s, kind in all_sents:
        n, paren = count_words(s)
        word_total += n + sum(count_words(p)[0] for p in paren)
        sent_lens.append((line0, s, n, paren, kind))

    # Sentence length (E1, D1, C6, B10)
    rule, cap = CAPS[level]
    if cap:
        for line0, s, n, paren, kind in sent_lens:
            if n > cap:
                findings.append(make_finding(rule, "warn", line0, s, f"{n} слов, предел {cap}: раздели предложение"))
            for p in paren:
                pn = count_words(p)[0]
                if pn > cap:
                    findings.append(make_finding(rule, "warn", line0, p, f"{pn} слов в скобках, предел {cap}"))

    # Pattern rules
    for rule_id, min_level, severity, rx, message in PATTERNS:
        if level < min_level:
            continue
        for m in rx.finditer(plain):
            findings.append(make_finding(rule_id, severity, line_of(plain, m.start()), m.group(0), message))

    # Hedge cascade: two or more in a sentence
    if level >= 20:
        for line0, s, n, paren, kind in sent_lens:
            hits = HEDGE.findall(s)
            if len(hits) >= 2:
                findings.append(make_finding("A6", "warn", line0, s, f"{len(hits)} оговорок в одном предложении: оставь одну настоящую"))

    # Em-dash in English sentences (Russian keeps the dash)
    en_sents = [(l, s, n) for l, s, n, p, k in sent_lens if cyr_ratio(s) < 0.3]
    if level >= 40 and any("—" in s for l, s, n in en_sents):
        en_words = sum(n for l, s, n in en_sents)
        quota = 0 if level >= 80 else en_words // 200
        used = 0
        for l, s, n in en_sents:
            c = s.count("—")
            if not c:
                continue
            used += c
            if used > quota:
                findings.append(make_finding("EN", "warn", l, s, "em-dash in English: write two sentences or name the relation"))
    # Semicolon in English sentences
    if level >= 80:
        for l, s, n, p, k in sent_lens:
            if ";" in s and cyr_ratio(s) < 0.3:
                findings.append(make_finding("EN", "warn", l, s, "semicolon: write two sentences"))

    # Antithesis density
    anti = {}
    for rx in ANTI:
        for m in rx.finditer(plain):
            start = m.start() + (len(m.group(0)) - len(m.group(0).lstrip(". !?\n")))
            if start not in anti or len(m.group(0)) < len(anti[start][1]):
                anti[start] = (line_of(plain, start), m.group(0).strip(" .!?\n"))
    uniq = [anti[k] for k in sorted(anti)]
    limit = antithesis_limit(word_total)
    if len(uniq) > limit:
        for l, t in uniq:
            findings.append(make_finding("A4", "warn", l, t, f"кандидат в антитезы «не X, а Y»: {len(uniq)} при допустимых {limit} на {word_total} слов; проверь, риторические ли они"))
    elif uniq and level >= 80:
        for l, t in uniq:
            findings.append(make_finding("A4", "info", l, t, "антитеза в пределах нормы: проверь, нет ли прямого утверждения"))

    # Decor
    for m in EMOJI.finditer(masked):
        findings.append(make_finding("A8", "warn", line_of(masked, m.start()), m.group(0), "эмодзи: убери"))
    for m in BOLD_LEAD.finditer(masked):
        findings.append(make_finding("A8", "warn", line_of(masked, m.start()), m.group(0), "жирный лид-ин: убери выделение"))

    # Heading over two sentences or fewer
    if level >= 20:
        for i, (kind, line0, body) in enumerate(blks):
            if kind != "heading":
                continue
            j = i + 1
            sect = []
            while j < len(blks) and blks[j][0] != "heading":
                sect.append(blks[j])
                j += 1
            if len(sect) == 1 and sect[0][0] == "para" and len(sentences(sect[0][2])) <= 2:
                findings.append(make_finding("A8", "info", line0, body, "заголовок над двумя предложениями или меньше"))

    # Noun chains
    if level >= 60:
        for m in CHAIN.finditer(plain):
            findings.append(make_finding("C3", "info", line_of(plain, m.start()), m.group(0), "цепочка существительных: глагол или сокращение"))

    # Paragraph rules
    paras = [(l, body) for kind, l, body in blks if kind == "para"]
    if level >= 80:
        for l, body in paras:
            ns = len(sentences(body))
            if ns > 6:
                findings.append(make_finding("D7", "warn", l, body, f"{ns} предложений в абзаце, предел 6"))
    if level >= 100 and len(paras) >= 10:
        singles = sum(1 for l, body in paras if len(sentences(body)) == 1)
        if singles > len(paras) // 10:
            findings.append(make_finding("E3", "info", paras[0][0], "", f"абзацев из одного предложения: {singles} из {len(paras)}, допустимо {len(paras) // 10}"))

    # Rhythm (levels 40 to 80)
    if 40 <= level <= 80:
        for l, body in paras:
            lens = [count_words(s)[0] for s in sentences(body)]
            if len(lens) >= 5 and statistics.mean(lens) > 0:
                cv = statistics.pstdev(lens) / statistics.mean(lens)
                if cv < 0.2:
                    findings.append(make_finding("B8", "info", l, body, "ровный ритм: предложения почти одной длины"))
            run = 0
            for n in lens:
                run = run + 1 if n <= 5 else 0
                if run == 3:
                    findings.append(make_finding("B8", "info", l, body, "три коротких предложения подряд: склей или разверни"))
                    break

    # Possible repetition
    norm = []
    for line0, s, n, p, k in sent_lens:
        ws = set(w.lower() for w in _TOKEN.findall(s))
        if len(ws) >= 5:
            norm.append((line0, s, ws))
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            a, b = norm[i][2], norm[j][2]
            if len(a & b) / len(a | b) >= 0.8:
                findings.append(make_finding("A11", "info", norm[j][0], norm[j][1], f"похоже на повтор предложения со строки {norm[i][0]}"))
                break

    # Reply format
    if mode == "reply" and level >= 80:
        sev = "warn" if level >= 100 else "info"
        for m in re.finditer(r"^[ \t]{0,3}#{1,6}[ \t].*$", masked, re.M):
            findings.append(make_finding("D9", "warn", line_of(masked, m.start()), m.group(0), "заголовок в ответе чата"))
        lead_lines = {line_of(masked, m.start()) for m in BOLD_LEAD.finditer(masked)}
        for m in re.finditer(r"\*\*[^*\n]+\*\*", masked):
            if line_of(masked, m.start()) in lead_lines:
                continue
            findings.append(make_finding("D9", "warn", line_of(masked, m.start()), m.group(0), "жирный текст в ответе чата"))
        for m in re.finditer(r"^[ \t]*\|.*\|[ \t]*$", masked, re.M):
            findings.append(make_finding("D9", "warn", line_of(masked, m.start()), m.group(0), "таблица в ответе чата"))
        items = [m for m in re.finditer(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+.*$", masked, re.M)]
        if items and (level >= 100 or len(items) < 3):
            for m in items:
                findings.append(make_finding("D9" if level < 100 else "E6", sev, line_of(masked, m.start()), m.group(0), "список в ответе: только для шагов и трёх и более однородных пунктов"))

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    warn = sum(1 for f in findings if f["severity"] == "warn")
    info = len(findings) - warn
    ru = sum(1 for l, s, n, p, k in sent_lens if cyr_ratio(s) >= 0.3)
    summary = {
        "level": level,
        "mode": mode,
        "language": "ru" if ru * 2 >= max(len(sent_lens), 1) else "en",
        "words": word_total,
        "sentences": len(sent_lens),
        "warnings": warn,
        "hints": info,
        "warnings_per_100_words": round(warn * 100 / word_total, 2) if word_total else 0.0,
        "sentence_cap": cap,
    }
    return {"summary": summary, "findings": findings}


def render(result, name):
    s = result["summary"]
    lines = [
        f"antislop-lint {name}: уровень {s['level']}, {s['language']}, {s['words']} слов, {s['sentences']} предложений"
    ]
    for f in result["findings"]:
        mark = "!" if f["severity"] == "warn" else "·"
        lines.append(f"  {mark} L{f['line']:<4} {f['rule']:<4} {f['message']}: «{f['text']}»")
    lines.append(
        f"Замечаний: {s['warnings']}. Подсказок: {s['hints']}. Замечаний на 100 слов: {s['warnings_per_100_words']}."
    )
    if s["warnings"] == 0:
        lines.append("Механические проверки пройдены. Смысл и факты линтер не проверяет.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Эвристический линтер нейрослопа (ru/en).")
    ap.add_argument("files", nargs="*", help="файлы; без аргументов читает stdin")
    ap.add_argument("--level", type=int, default=80, help="20, 40, 60, 80 или 100 (по умолчанию 80)")
    ap.add_argument("--mode", choices=("document", "reply"), default="document", help="reply добавляет проверку формата ответа в чате")
    ap.add_argument("--skip-quoted", action="store_true", help="не искать шаблоны внутри кавычек (для текстов, которые цитируют примеры)")
    ap.add_argument("--json", action="store_true", help="вывод в JSON")
    ap.add_argument("--strict", action="store_true", help="exit code 1, если есть замечания warn")
    args = ap.parse_args(argv)

    sources = []
    if args.files:
        for p in args.files:
            with open(p, encoding="utf-8") as fh:
                sources.append((p, fh.read()))
    else:
        sources.append(("<stdin>", sys.stdin.read()))

    results = []
    for name, text in sources:
        r = lint(text, args.level, args.mode, args.skip_quoted)
        r["file"] = name
        results.append(r)

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(render(r, r["file"]) for r in results))

    if args.strict and any(r["summary"]["warnings"] for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
