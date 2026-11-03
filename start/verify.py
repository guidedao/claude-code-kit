"""Проверка стартовых папок start/NN: пути из уроков, скрипты, тесты, пересборка страницы.

Запуск из корня набора: python3 start/verify.py
Каждая папка копируется во временный launch-kit рядом с набором, там создаётся
репозиторий и запускаются скрипты, тесты и проверки набора. Сам набор не меняется.
"""
import csv
import filecmp
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
START = KIT / "start"
FAILS = []


def ok(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def run(args, cwd, expect_ok=True):
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=300)
    if expect_ok and res.returncode:
        print(res.stdout, res.stderr)
    return res


# Модуль урока → папка старта, которой он пользуется, и пути, которые читают его видимые уроки.
MODULES = {
    1: ("01", ["notes.md", "brief.md"]),
    2: ("01", ["notes.md", "brief.md"]),
    3: ("03", ["outputs/update.md", "outputs/update.html", "brief-client.md", "outputs/status.html",
               "work/acceptance.md", "inputs/tasks.csv", "inputs/notes.md", "CLAUDE.md", "style.md"]),
    4: ("04", ["outputs/update.md", "inputs/notes.md", "drafts/invite.md", "inputs/webinar-notes.md",
               "inputs/contract.docx", "outputs/contract-memo.md", "outputs/status.html", "style.md",
               "CLAUDE.md", "inputs/risks.md", "letter.md"]),
    5: ("05", ["inputs/tasks.csv", "outputs/competitors.md", "inputs/sources.md", "brief-research.md",
               "templates/memo.md", ".claude/skills/memo/SKILL.md", "letter.md", "decisions.md"]),
    6: ("05", []),
    7: ("07", ["inputs/weekly-leads.csv", "inputs/invites.csv"]),
    8: ("08", ["scripts/reconcile.py", "work/reconcile-plan.md", "outputs/reconcile.xlsx", "inputs/tasks.csv",
               "work/acceptance.md", "style.md", "outputs/status.html", "inputs/campaigns.csv",
               "scripts/report.py", "outputs/channel-summary.csv", "outputs/channels.svg", "outputs/method.md",
               "CLAUDE.md", "inputs/crm-leads-oct.xlsx"]),
    9: ("08", []),
    10: ("08", ["scripts/report.py", "outputs/method.md", "inputs/campaigns.csv"]),
    11: ("11", ["scripts/build_status.py", "CLAUDE.md", "tests/test_report.py", ".claude/settings.json",
                "outputs/status.html", "scripts/report.py", "inputs/tasks.csv", ".github/workflows/checks.yml"]),
    12: ("11", []),
    13: ("13", [".claude/skills/weekly-status/SKILL.md", ".claude/skills/weekly-status/scripts/check_status.py",
                ".claude/agents/status-reviewer.md", "work/acceptance.md", "outputs/status.html",
                "inputs/tasks.csv", ".claude/settings.json", "CLAUDE.md", "scripts/report.py",
                "scripts/build_status.py", "outputs/method.md"]),
    14: ("13", ["style.md", ".claude/settings.json", "outputs/update.md"]),
    15: ("13", ["scripts/build_status.py", "inputs/tasks.csv", "outputs/status.html",
                ".github/workflows/checks.yml", "CLAUDE.md", ".claude/settings.json", "tests/test_report.py"]),
    16: ("13", ["scripts/report.py"]),
    17: ("13", ["CLAUDE.md", ".claude/settings.json", "scripts/build_status.py", "inputs/risks.md",
                ".claude/skills/weekly-status/scripts/check_status.py", ".claude/agents/status-reviewer.md"]),
    18: ("13", ["outputs/channel-summary.csv", "inputs/campaigns.csv"]),
    19: ("13", ["CLAUDE.md", ".claude/settings.json", "inputs/tasks.csv", "outputs/status.html",
                "scripts/build_status.py", "tests/test_report.py", "work/acceptance.md"]),
}


def files(nn):
    root = START / nn
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def check_paths():
    print("Пути из уроков")
    for n, (nn, paths) in MODULES.items():
        have = files(nn)
        missing = [p for p in paths if p not in have]
        ok(not missing, f"модуль {n} → start/{nn}: {len(paths)} путей" + (f", нет: {missing}" if missing else ""))


def check_cumulative():
    print("Накопление: каждый следующий старт содержит пути предыдущего")
    order = sorted(p.name for p in START.iterdir() if p.is_dir())
    for a, b in zip(order, order[1:]):
        lost = files(a) - files(b)
        allowed = {"notes.md"} if a == "01" else set()  # заметки переехали в inputs/ по карте папки
        ok(lost <= allowed, f"start/{a} ⊂ start/{b}" + (f", пропало: {sorted(lost - allowed)}" if lost - allowed else ""))


def line_lengths():
    print("Длина строк в notes.md и brief.md модуля 1 (текст урока, ≤ 64)")
    for name in ("notes.md", "brief.md"):
        longest = max(len(l) for l in (START / "01" / name).read_text(encoding="utf-8").splitlines())
        ok(longest <= 64, f"{name}: самая длинная строка {longest}")


def check_tasks(nn):
    with open(START / nn / "inputs/tasks.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ok(len(rows) == 6, f"start/{nn}: в tasks.csv 6 задач")
    ok(sum(r["status"] == "блокер" for r in rows) == 1, f"start/{nn}: один блокер")
    ok(sum(r["status"] != "готово" and r["due"] < "2026-05-15" for r in rows) == 1, f"start/{nn}: одна просрочка")
    ok(sum(not r["owner"] for r in rows) == 1, f"start/{nn}: одна задача без ответственного")
    ok(any(r["task"] == "Юридические формулировки" and r["status"] == "готово" for r in rows),
       f"start/{nn}: «Юридические формулировки» — готово")


def in_copy(nn):
    tmp = Path(tempfile.mkdtemp())
    work = tmp / "launch-kit"
    shutil.copytree(START / nn, work)
    (tmp / "claude-code-kit").symlink_to(KIT)
    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                ["git", "-c", "user.name=guidedao", "-c", "user.email=7037569+guidedao@users.noreply.github.com", "commit", "-qm", f"Старт модуля {int(nn)}"]):
        run(cmd, work)
    return tmp, work


def check_scripts(nn):
    have = files(nn)
    tmp, work = in_copy(nn)
    try:
        if "scripts/reconcile.py" in have:
            out = run([sys.executable, "scripts/reconcile.py"], work).stdout
            ok("Совпали 114, пропали 6, новые 14, изменили статус 23" in out, f"start/{nn}: reconcile.py — {out.splitlines()[1] if out else out}")
            ok("сентябрь 1384738.50, октябрь 1590183.50" in out, f"start/{nn}: суммы amount сверки")
        if "scripts/report.py" in have:
            out = run([sys.executable, "scripts/report.py"], work).stdout.strip()
            ok(out == "Каналов: 7. spend 34700, revenue 180000. Без CPL: organic, unknown.", f"start/{nn}: report.py — {out}")
            with open(work / "outputs/channel-summary.csv", encoding="utf-8", newline="") as f:
                cpl = {r["channel"]: r["cpl"] for r in csv.DictReader(f)}
            ok(cpl == {"email": "112.5", "organic": "", "partners": "357.14", "search": "333.96", "social": "270.27",
                       "unknown": "", "video": "400.0"}, f"start/{nn}: CPL по каналам как в method.md")
            src = (work / "scripts/report.py").read_text(encoding="utf-8").splitlines()
            ok(src[11] == '"""' and src[13:16] == ["import csv", "from pathlib import Path",
               "from xml.sax.saxutils import escape"] and src[17].startswith("INPUT =") and src[20].startswith("PERIOD ="),
               f"start/{nn}: report.py — шапка 1–12, импорты 14–16, константы 18–21")
            ok(sum(l.startswith("def ") for l in src) == 6, f"start/{nn}: report.py — шесть функций")
            ok("int(t[\"cpl\"] + 0.5)" in "\n".join(src), f"start/{nn}: подписи графика округлены до целых (урок «Чтение скрипта»)")
            alien = Path(tempfile.mkdtemp())
            res = run([sys.executable, str(work / "scripts/report.py")], alien, expect_ok=False)
            ok(res.returncode != 0 and "FileNotFoundError" in res.stderr and "inputs/campaigns.csv" in res.stderr,
               f"start/{nn}: из другой папки report.py падает с FileNotFoundError (урок «Ошибка и traceback»)")
        gen = ["outputs/reconcile.xlsx", "outputs/channel-summary.csv", "outputs/channels.svg"]
        if "scripts/build_status.py" in have:
            out = run([sys.executable, "scripts/build_status.py"], work).stdout
            ok("Запуск под риском, задач 6" in out, f"start/{nn}: build_status.py — {out.strip()}")
            gen.append("outputs/status.html")
            page = (work / "outputs/status.html").read_text(encoding="utf-8")
            ok('SUBTITLE = "Лендинг сервиса еженедельных отчётов · запуск 20 мая"' in
               (work / "scripts/build_status.py").read_text(encoding="utf-8").splitlines(), f"start/{nn}: строка SUBTITLE")
            blockers = page.split("<h2>Блокеры и просрочки</h2>")[1].split("</section>")[0].count("<tr>")
            ok(blockers == 2, f"start/{nn}: в «Блокерах и просрочках» две задачи (урок «Issues»)")
            ok("Рекламные каналы, 1–3 мая" in page, f"start/{nn}: раздел с графиком каналов на странице")
        for rel in gen:
            if rel in have:
                ok(filecmp.cmp(work / rel, START / nn / rel, shallow=False), f"start/{nn}: пересборка совпала с {rel}")
        st = run(["git", "status", "--short"], work).stdout.strip()
        ok(st == "", f"start/{nn}: после запуска скриптов git status пуст" + (f": {st}" if st else ""))
        res = run([sys.executable, "-m", "unittest"], work, expect_ok=False)
        if "tests/test_report.py" in have:
            ok(res.returncode == 0 and "Ran 7 tests" in res.stderr, f"start/{nn}: python3 -m unittest — {res.stderr.strip().splitlines()[-3:]}")
        else:
            ok("Ran 0 tests" in res.stderr, f"start/{nn}: python3 -m unittest — Ran 0 tests (урок «Тесты и критерий готовности»)")
        if ".claude/skills/weekly-status/scripts/check_status.py" in have:
            res = run([sys.executable, ".claude/skills/weekly-status/scripts/check_status.py"], work)
            ok(res.returncode == 0 and res.stdout.startswith("OK"), f"start/{nn}: check_status.py — {res.stdout.strip()}")
        st = run(["git", "status", "--short", "--ignored"], work).stdout.strip()
        ok(all(l.startswith("!!") for l in st.splitlines()), f"start/{nn}: тесты не оставили неигнорируемых файлов")
        # контрольные скрипты набора по практикам, чьи результаты лежат в старте
        if "scripts/reconcile.py" in have:
            res = run([sys.executable, "../claude-code-kit/crm-reconcile/checks/check_reconcile.py"], work, expect_ok=False)
            ok(res.returncode == 0, f"start/{nn}: check_reconcile.py — {res.stdout.strip().splitlines()[-1]}")
        if "scripts/build_status.py" in have:
            res = run([sys.executable, "../claude-code-kit/channels-report/checks/check_channels.py"], work, expect_ok=False)
            print(res.stdout)
            ok(res.returncode == 0, f"start/{nn}: check_channels.py — {res.stdout.strip().splitlines()[-1]}")
            res = run([sys.executable, "../claude-code-kit/ci/checks/check_repo.py"], work, expect_ok=False)
            ok(res.returncode == 0 and "Итог: 4 из 4" in res.stdout,
               f"start/{nn}: check_repo.py — {res.stdout.strip().splitlines()[-1]} (урок «/loop и цели»)")
    finally:
        shutil.rmtree(tmp)


def check_texts():
    print("Тексты")
    c3 = (START / "03/CLAUDE.md").read_text(encoding="utf-8")
    ok(all(s in c3 for s in ("## Карта папки", "## Стиль", "## Запреты", "## Проверки", "Ничего не отправлять")),
       "start/03 CLAUDE.md: карта, стиль, запреты, проверки, «ничего не отправлять»")
    ok(len(c3.splitlines()) < 200, "CLAUDE.md короче 200 строк")
    c5 = (START / "05/CLAUDE.md").read_text(encoding="utf-8")
    ok("Правила стиля — в style.md" in c5, "start/05 CLAUDE.md: строка со ссылкой на style.md")
    c11 = (START / "11/CLAUDE.md").read_text(encoding="utf-8")
    ok("ось от нуля; не больше одной шкалы на графике; период из method.md; размер — длиной, не площадью" in c11.lower(),
       "start/11 CLAUDE.md: правило графиков")
    ok("## Ветки" not in c11 and "Ничего не отправлять" in c11, "start/11 CLAUDE.md: раздела «Ветки» ещё нет, запрет отправки из модуля 2")
    c13 = (START / "13/CLAUDE.md").read_text(encoding="utf-8")
    ok("## Ветки" in c13 and "git push в закрытый репозиторий" in c13, "start/13 CLAUDE.md: «Ветки» и уточнённый запрет")
    s3 = (START / "03/style.md").read_text(encoding="utf-8")
    s5 = (START / "05/style.md").read_text(encoding="utf-8")
    ok("## Вид страниц" in s3 and "## Тексты" not in s3, "start/03 style.md: только вид страниц")
    ok(s5.startswith(s3) and "## Тексты" in s5, "start/05 style.md: раздел «Тексты» дописан в конец")
    src = (START / "05/inputs/sources.md").read_text(encoding="utf-8").splitlines()
    ok(src[2] == "На первом экране: «Еженедельный клиентский отчёт из CSV за 10 минут»." and "коннектора к Google Drive нет" in src[4],
       "inputs/sources.md: S1 в строке 3, S2 в строке 5")
    comp = (START / "05/outputs/competitors.md").read_text(encoding="utf-8")
    ok("ReportFlow обещает отчёт из CSV за 10 минут, но коннектора к Google Drive у него нет, поэтому агентствам с данными в Drive он не подходит." in comp,
       "competitors.md: абзац о ReportFlow из урока «Цитата, факт и вывод»")
    ok("BriefPilot обещает быстрый черновик на первом экране" in comp and "нет подтверждения" in comp,
       "competitors.md: вывод о BriefPilot для урока «Перекрёстная проверка» и метка «нет подтверждения»")
    camp = (START / "08/inputs/campaigns.csv").read_text(encoding="utf-8")
    ok("2026-05-03,yandex_direct,competitors,search,4200,260,6,9000" in camp, "campaigns.csv: поиск по конкурентам 4200 / 6 лидов = 700 ₽")
    inv = (START / "04/drafts/invite.md").read_text(encoding="utf-8")
    ok("Вебинар пройдёт 21 мая в 19:00 по Москве.\nЗапись пришлём участникам по запросу." in inv and "мест ограничено" not in inv,
       "drafts/invite.md: строки из пословного диффа урока, без «мест ограничено»")
    for a, b in (("04/inputs/contract.docx", "contract-redline/inputs/contract.docx"),
                 ("07/inputs/crm-leads-oct.xlsx", "crm-reconcile/inputs/crm-leads-oct.xlsx"),
                 ("07/inputs/crm-leads-sept.csv", "crm-reconcile/inputs/crm-leads-sept.csv")):
        ok(hashlib.sha256((START / a).read_bytes()).digest() == hashlib.sha256((KIT / b).read_bytes()).digest(),
           f"{a} совпадает с {b}")
    v1 = (START / "04/letter.md").read_text(encoding="utf-8")
    ok("пришлём до\n20 мая. Марина проверит юридические формулировки до\nзапуска. Рекламу запустим после её проверки." in v1,
       "start/04 letter.md: версия Ильи, правку Никиты урок «Версии документа в Git» вносит сам")
    dec = "Илья, 17 мая: тексты — до 24 мая; проверка Марины до запуска остаётся; бесплатную доработку не обещаем."
    for nn in sorted(p.name for p in START.iterdir() if p.is_dir() and p.name >= "05"):
        fin = (START / nn / "letter.md").read_text(encoding="utf-8")
        ok(fin == v1.replace("до\n20 мая", "до\n24 мая") and dec in (START / nn / "decisions.md").read_text(encoding="utf-8"),
           f"start/{nn}: letter.md по решению Ильи из decisions.md (урок «Хэндоф»)")
    legal = KIT / "team-pack/lessons/marketplace/launch-kit-plugins/plugins/launch-legal/skills/legal-wording"
    ok((legal / "SKILL.md").is_file() and (legal / "legal-rules.md").is_file(),
       "team-pack: скил legal-wording, на который ссылается урок «Командные скилы и плагины»")
    sk = (START / "13/.claude/skills/weekly-status/SKILL.md").read_text(encoding="utf-8")
    ok("disable-model-invocation: true" in sk and "${CLAUDE_SKILL_DIR}/scripts/check_status.py" in sk, "SKILL.md weekly-status как в уроке")
    st = (START / "13/.claude/settings.json").read_text(encoding="utf-8")
    ok('"Edit(/tests/**)"' in st and "inputs" not in st, "settings.json: запрет на tests/, запрет на inputs/ — упражнение модуля 13")


def main():
    check_paths()
    check_cumulative()
    line_lengths()
    for nn in ("03", "08", "11", "13"):
        check_tasks(nn)
    for nn in sorted(p.name for p in START.iterdir() if p.is_dir()):
        print(f"Скрипты в start/{nn}")
        check_scripts(nn)
    check_texts()
    print("\nИтог:", "всё сходится" if not FAILS else f"{len(FAILS)} расхождений")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
