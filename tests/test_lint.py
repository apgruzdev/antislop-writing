import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "antislop-writing" / "scripts" / "antislop_lint.py"
spec = importlib.util.spec_from_file_location("antislop_lint", SCRIPT)
lint_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint_mod)
lint = lint_mod.lint


def rules(text, level=80, mode="document", severity=None):
    res = lint(text, level, mode)["findings"]
    if severity:
        res = [f for f in res if f["severity"] == severity]
    return [f["rule"] for f in res]


class Levels(unittest.TestCase):
    def test_snap(self):
        self.assertEqual(lint_mod.snap_level(90), 80)
        self.assertEqual(lint_mod.snap_level(70), 60)
        self.assertEqual(lint_mod.snap_level(80), 80)
        self.assertEqual(lint_mod.snap_level(0), 20)
        self.assertEqual(lint_mod.snap_level(500), 100)
        self.assertEqual(lint_mod.snap_level(99), 100)


class Words(unittest.TestCase):
    def test_number_is_one_word(self):
        self.assertEqual(lint_mod.count_words("Проверка занимает 3.5 секунды")[0], 4)

    def test_quote_is_one_word(self):
        self.assertEqual(lint_mod.count_words("Нажмите «Сохранить изменения и выйти»")[0], 2)

    def test_parentheses_are_separate(self):
        n, paren = lint_mod.count_words("Откройте файл (он лежит в корне проекта)")
        self.assertEqual(n, 2)
        self.assertEqual(paren, ["он лежит в корне проекта"])

    def test_alphanumeric_id_is_one_word(self):
        self.assertEqual(lint_mod.count_words("Батарея 15-СЦС-45 готова")[0], 3)

    def test_abbreviation_does_not_split_sentence(self):
        self.assertEqual(len(lint_mod.sentences("Мы используем Docker, Kubernetes и т. д. Это просто.")), 2)

    def test_decimal_does_not_split_sentence(self):
        self.assertEqual(len(lint_mod.sentences("Версия 2.1 вышла вчера. Всё работает.")), 2)


class Length(unittest.TestCase):
    S26 = " ".join(["слово"] * 26) + "."
    S21 = " ".join(["слово"] * 21) + "."

    def test_cap_80(self):
        self.assertIn("D1", rules(self.S26, 80))
        self.assertNotIn("D1", rules(self.S21, 80))

    def test_cap_100(self):
        self.assertIn("E1", rules(self.S21, 100))
        self.assertNotIn("E1", rules(self.S21, 60))

    def test_cap_60_and_40(self):
        s31 = " ".join(["слово"] * 31) + "."
        s41 = " ".join(["слово"] * 41) + "."
        self.assertIn("C6", rules(s31, 60))
        self.assertNotIn("C6", rules(self.S26, 60))
        self.assertIn("B10", rules(s41, 40))
        self.assertNotIn("B10", rules(s31, 40))

    def test_no_cap_at_20(self):
        s = " ".join(["слово"] * 80) + "."
        self.assertEqual([r for r in rules(s, 20) if r in {"E1", "D1", "C6", "B10"}], [])


class Patterns(unittest.TestCase):
    def test_slop_is_caught(self):
        text = "Отличный вопрос! В современном мире данный сервис является ключевым. Это не про скорость, это про контроль. Надеюсь, это поможет!"
        got = set(rules(text, 80, severity="warn"))
        self.assertTrue({"A1", "A2", "A4", "A5"} <= got, got)

    def test_clean_text_has_no_warnings(self):
        text = "Сервис проверяет конфигурацию. Проверка занимает около 40 секунд. Если проверка упала, откройте журнал."
        self.assertEqual(rules(text, 80, severity="warn"), [])

    def test_data_noun_is_not_chancellery(self):
        self.assertEqual(rules("Сервер хранит данные в базе. Данные шифруются.", 80, severity="warn"), [])
        self.assertIn("A5", rules("В данный момент сервис недоступен.", 80, severity="warn"))

    def test_inline_code_does_not_make_a_russian_sentence_english(self):
        text = "Ключ задаёт `timeout` в файле `config.yaml`; значение — число секунд."
        self.assertNotIn("EN", rules(text, 80))

    def test_by_data_is_not_chancellery(self):
        self.assertEqual(rules("По данным отчёта, сервис работает.", 80, severity="warn"), [])

    def test_skip_quoted(self):
        text = "Не пишите «в современном мире» и «является»."
        self.assertIn("A5", rules(text, 80, severity="warn"))
        res = lint(text, 80, "document", skip_quoted=True)["findings"]
        self.assertEqual([f for f in res if f["severity"] == "warn"], [])

    def test_unique_is_a_hint_not_a_warning(self):
        self.assertEqual(rules("Клиент создаёт уникальный ключ.", 80, severity="warn"), [])
        self.assertIn("A2", rules("Клиент создаёт уникальный ключ.", 80, severity="info"))

    def test_labels(self):
        self.assertIn("A3", rules("Важный нюанс: файл удаляется.", 80))

    def test_hedge_cascade(self):
        self.assertIn("A6", rules("Возможно, это, как правило, работает.", 80))
        self.assertNotIn("A6", rules("Возможно, это работает.", 80))

    def test_emoji_and_bold_leadin(self):
        got = rules("- **Скорость:** выше ⚡\n", 20)
        self.assertEqual(got.count("A8"), 2)

    def test_pattern_respects_level(self):
        text = "Кстати, это работает."
        self.assertIn("B9", rules(text, 40))
        self.assertNotIn("B9", rules(text, 20))

    def test_code_is_masked(self):
        text = "Запустите команду:\n\n```\nданный является осуществляет\n```\n\nИ проверьте `в рамках` вывод."
        self.assertEqual(rules(text, 80, severity="warn"), [])

    def test_frontmatter_is_masked(self):
        text = "---\ndescription: данный является\n---\n\nСервис работает."
        self.assertEqual(rules(text, 80, severity="warn"), [])

    def test_line_numbers(self):
        res = lint("Первая строка.\n\nВторая строка. В современном мире всё иначе.", 80)["findings"]
        self.assertEqual([f["line"] for f in res if f["rule"] == "A5"], [3])


class English(unittest.TestCase):
    def test_modals_and_contractions(self):
        got = rules("You should restart it. Don't wait.", 80, severity="warn")
        self.assertEqual(got.count("EN"), 2)

    def test_modals_off_below_80(self):
        self.assertNotIn("EN", rules("You should restart it.", 60))

    def test_em_dash_banned_in_english_from_80(self):
        self.assertIn("EN", rules("The service restarts — it takes a minute.", 80))

    def test_em_dash_allowed_in_russian(self):
        self.assertEqual(rules("Москва — столица России.", 80, severity="warn"), [])

    def test_em_dash_allowance_at_60(self):
        half = " ".join(["word"] * 120)
        one_dash = half + ". " + half + " — end."
        two_dash = half + " — one. " + half + " — two."
        self.assertNotIn("EN", rules(one_dash, 60))
        self.assertIn("EN", rules(two_dash, 60))

    def test_semicolon(self):
        self.assertIn("EN", rules("Stop the service; start it again.", 80))

    def test_ing_after_comma(self):
        self.assertIn("EN", rules("The tool reads the file, making it fast.", 80))

    def test_slop_words(self):
        self.assertIn("A2", rules("We leverage a robust, seamless pipeline.", 80))


class Antithesis(unittest.TestCase):
    def test_density_limit(self):
        text = "Это не просто сервис, а платформа. Это не просто отчёт, а решение."
        self.assertIn("A4", rules(text, 80, severity="warn"))

    def test_single_within_limit_is_hint_only(self):
        text = "Это не просто задержка, а сигнал."
        self.assertEqual(rules(text, 80, severity="warn"), [])
        self.assertIn("A4", rules(text, 80, severity="info"))

    def test_limit_function(self):
        self.assertEqual(lint_mod.antithesis_limit(500), 1)
        self.assertEqual(lint_mod.antithesis_limit(2000), 2)
        self.assertEqual(lint_mod.antithesis_limit(4500), 3)

    def test_factual_negation_is_fine(self):
        self.assertEqual(rules("Сервис не хранит пароли.", 80, severity="warn"), [])


class Structure(unittest.TestCase):
    def test_long_paragraph(self):
        para = " ".join(f"Предложение номер {i}." for i in range(1, 9))
        self.assertIn("D7", rules(para, 80))
        self.assertNotIn("D7", rules(para, 60))

    def test_reply_mode_formatting(self):
        text = "# Заголовок\n\nОтвет с **жирным**.\n"
        got = rules(text, 80, mode="reply", severity="warn")
        self.assertEqual(got.count("D9"), 2)
        self.assertEqual(rules(text, 80, mode="document", severity="warn").count("D9"), 0)

    def test_bold_lead_in_is_counted_once_in_reply_mode(self):
        got = rules("**Контекст.** Решение записано.\n", 80, mode="reply", severity="warn")
        self.assertEqual(got.count("A8") + got.count("D9"), 1)

    def test_reply_mode_line_numbers_are_exact(self):
        text = "Ответ.\n\n- один пункт\n- второй пункт\n\n**Итог.** Готово.\n"
        res = lint(text, 80, "reply")["findings"]
        self.assertEqual(sorted((f["rule"], f["line"]) for f in res if f["rule"] in {"D9", "A8"}),
                         [("A8", 6), ("D9", 3), ("D9", 4)])

    def test_reply_list_rules(self):
        three = "Шаги:\n\n1. Откройте файл.\n2. Измените параметр.\n3. Сохраните файл.\n"
        self.assertNotIn("D9", rules(three, 80, mode="reply"))
        self.assertIn("E6", rules(three, 100, mode="reply"))
        two = "- один пункт\n- второй пункт\n"
        self.assertIn("D9", rules(two, 80, mode="reply"))

    def test_repetition(self):
        text = "Сервис проверяет конфигурацию перед запуском. Потом идёт другое. Сервис проверяет конфигурацию перед запуском."
        self.assertIn("A11", rules(text, 80))

    def test_rhythm_run_of_short_sentences(self):
        text = "Мы запустили. Были сроки. Команда работала. Мы успели вовремя."
        self.assertIn("B8", rules(text, 60))
        self.assertNotIn("B8", rules(text, 100))


class Cli(unittest.TestCase):
    def run_cli(self, *args, stdin=""):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=stdin, capture_output=True, text=True, encoding="utf-8",
        )

    def test_json_output(self):
        r = self.run_cli("--json", "--level", "80", stdin="В современном мире всё иначе.")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["summary"]["level"], 80)
        self.assertEqual(data["findings"][0]["rule"], "A5")

    def test_strict_exit_code(self):
        bad = self.run_cli("--strict", stdin="В современном мире всё иначе.")
        good = self.run_cli("--strict", stdin="Сервис работает.")
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(good.returncode, 0)

    def test_level_is_snapped(self):
        r = self.run_cli("--json", "--level", "90", stdin="Сервис работает.")
        self.assertEqual(json.loads(r.stdout)["summary"]["level"], 80)


if __name__ == "__main__":
    unittest.main()
