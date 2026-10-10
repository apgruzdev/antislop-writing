# Первоисточники и лицензии

Этот репозиторий ничего не изобретает с нуля. Он собирает чужие работы в один набор и добавляет связующий навык с ползунком строгости. Ниже, что откуда взято, под какой лицензией и что изменено.

*This repository builds on the work below. English summary at the end.*

## Идея

| Источник | Что взято |
|---|---|
| [Andrej Karpathy, пост в X, 2 октября 2026](https://x.com/karpathy/status/2105819303471976479) | Идея просить у модели текст в духе ASD-STE100 и смягчать её: «80% of the way to ASD-STE100», потому что стандарт очень жёсткий. Из неё выросли ступени уровня 20–100. Сами ступени и числа на них придумал автор этого репозитория. Карпати о них не говорил. |

## Стандарты

| Источник | Что взято | Замечания |
|---|---|---|
| [ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/) | Принципы контролируемого языка: короткие предложения, один термин на понятие, действительный залог, условие перед командой. Через навык `simple-english`. | ASD-STE100 — зарегистрированный товарный знак ASD. Репозиторий не связан с ASD и STEMG и не одобрен ими. Текст стандарта и словарь не воспроизводятся. Никакой инструмент не подтверждает соответствие. Стандарт бесплатен на asd-ste100.org. |
| ГОСТ Р 58049-2017 «Перевод эксплуатационной документации на изделия авиационной техники с/на иностранные языки. Общие положения», раздел 8.2 «Упрощённый технический русский язык» ([копия на meganorm.ru](https://meganorm.ru/Data/661/66114.pdf)) | Требования к тексту: порядок слов, залог, императив, длина предложения, абзац, предупреждения, термины. См. `skills/antislop-writing/references/ru.md`. | Издатель — Стандартинформ, 2018. Стандарт защищён авторским правом, поэтому правила пересказаны своими словами, примеры свои, пункты названы номерами. ГОСТ описывает перевод авиационной документации и не задаёт закрытого словаря. Это ближайший русский аналог STE, а не его эквивалент. Репозиторий не подтверждает соответствие ГОСТ. |

## Навыки, скопированные в `skills/`

Каждая копия **неизменна**: в папку добавлены только `LICENSE` (текст лицензии оригинала) и `NOTICE.md` (откуда копия). Хеши коммитов закреплены в [`upstream.json`](upstream.json). Проверка, что копии совпадают с оригиналом: `node scripts/sync-upstream.mjs --check`.

| Навык | Автор | Лицензия | Оригинал | Коммит |
|---|---|---|---|---|
| `simple-english` | AminBlg | MIT | [AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish) | `a6fcb4f` |
| `redpolitika`, `redaktura`, `statya`, `post`, `promo`, `ux-copy` | Людмила Сарычева ([gladlax.ru](https://gladlax.ru)), Никита Архипов ([niar42.com](https://niar42.com)) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [N1arko/redaktura-skills](https://github.com/N1arko/redaktura-skills) | `d1ebaff` |
| `lossless-doc-compress` | Valerii Babushkin, Arseny Kravchenko | MIT | [ML-SystemDesign/MLSystemDesign](https://github.com/ML-SystemDesign/MLSystemDesign/tree/main/skills/lossless-doc-compress) (книга: [arseny.info/ml_design_book](https://arseny.info/ml_design_book)) | `8dd0d88` |

Почему копия, а не ссылка: `statya`, `post`, `promo` и `ux-copy` читают файлы `../redaktura/references/*`. Папки должны лежать рядом, и одна установка должна ставить всё сразу. Если вы уже поставили эти навыки из оригинала, наша установка заменит их копиями того же содержания. Для обновления у оригинала смотрите его репозиторий.

### Как выполнены условия лицензий

- MIT (`simple-english`, `lossless-doc-compress`): уведомление об авторском праве и текст лицензии лежат в `LICENSE` каждой копии.
- CC BY 4.0 (шесть навыков redaktura-skills): указаны авторы (Людмила Сарычева, Никита Архипов, [gladlax.ru](https://gladlax.ru)), дана ссылка на оригинал и на лицензию, текст лицензии лежит рядом. Изменений в содержании нет, это указано в `NOTICE.md`. Дополнительных ограничений мы не вводим.
- Лицензия MIT этого репозитория (`LICENSE`) относится только к оригинальному вкладу: навыку `antislop-writing`, установщику, хукам, промптам, скриптам, тестам и документации.

## Что мы взяли из оригиналов в навык `antislop-writing`

Копий текста здесь нет. Это пересказ правил и ссылки. Источник каждого правила назван в таблице `references/levels.md`:

- из `simple-english`: правила ответа в чате и документа, режимы Plain и Strict;
- из `redaktura-skills`: каталог следов нейросети, шкала допустимых антитез «не X, а Y», правила слова, предложения, ритма и тональности;
- из `lossless-doc-compress`: контракт «сомневаешься — пометь, не режь», категории удаляемого, список неприкосновенного;
- из ГОСТ Р 58049-2017: правила раздела 8.2 (пункты названы в таблицах).

## Инструменты, на которые опирается репозиторий

- [Agent Skills](https://agentskills.io) — формат `SKILL.md`.
- [vercel-labs/skills](https://github.com/vercel-labs/skills) (MIT) — установка навыков в 70 с лишним агентов. Установщик вызывает `npx skills`.
- [Claude Code](https://code.claude.com/docs): формат плагина и хуков.

## Чего здесь нет

Нет утверждений, что текст «соответствует» ASD-STE100 или ГОСТ. Нет обхода детекторов ИИ. Нет сборника чужих текстов сверх перечисленного.

---

## English summary

This repository bundles third-party work and adds one glue skill, `antislop-writing`, with a strictness dial (20–100%).

- Idea: [Andrej Karpathy's post](https://x.com/karpathy/status/2105819303471976479) suggests asking an LLM for "80% of the way to ASD-STE100". The dial steps are this repository's own design.
- Standards: [ASD-STE100](https://www.asd-ste100.org/) and the Russian GOST R 58049-2017 section 8.2. ASD-STE100 is a trademark of ASD. We have no affiliation, and we do not reproduce the standard or its dictionary. GOST is copyright Standartinform. Its rules are paraphrased and the examples are original.
- Vendored skills are unmodified and pinned to commits. `simple-english` is by AminBlg (MIT). `redpolitika`, `redaktura`, `statya`, `post`, `promo`, and `ux-copy` are by Lyudmila Sarycheva and Nikita Arkhipov (CC BY 4.0). `lossless-doc-compress` is by Valerii Babushkin and Arseny Kravchenko (MIT). Each directory holds the upstream `LICENSE` and a `NOTICE.md`.
- Own work (MIT): the skill `antislop-writing`, installer, hooks, prompts, linter, tests, docs.
