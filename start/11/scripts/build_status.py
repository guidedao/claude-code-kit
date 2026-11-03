#!/usr/bin/env python3
"""Страница статуса запуска лендинга.

Вход: inputs/tasks.csv (task, owner, due, status, note).
Правила — по work/acceptance.md:
1. Статус «блокер» — в «Блокеры и просрочки» с причиной из note.
2. Срок раньше даты статуса и статус не «готово» — туда же, с пометкой «просрочено».
3. Срок, равный дате статуса, — не просрочка.
4. Статус «готово» — в «Готово», остальные задачи — в «В работе».
5. Нет ответственного — задача в своём блоке с пометкой «ответственный не назначен».
Вывод сверху: «Запуск под риском», если в первом блоке есть задачи, иначе «Запуск по плану».
Если есть outputs/channels.svg, под «Готово» стоит раздел «Рекламные каналы, 1–3 мая».
Вид — по style.md. Выход: outputs/status.html.

Запуск из корня launch-kit: python3 scripts/build_status.py
"""
import csv
import html
from datetime import date
from pathlib import Path

INPUT = Path("inputs/tasks.csv")
OUTPUT = Path("outputs/status.html")
CHART = Path("outputs/channels.svg")
STATUS_DATE = date(2026, 5, 15)
SUBTITLE = "Лендинг сервиса еженедельных отчётов · запуск 20 мая"

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]

STYLE = """\
  body { margin: 0; background: #ffffff; color: #1a1a1a;
         font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }
  main { max-width: 760px; margin: 0 auto; padding: 32px 24px 48px; }
  .subtitle, .meta { color: #6b6b6b; margin: 0; }
  .verdict { font-size: 32px; font-weight: 600; line-height: 1.25; margin: 8px 0; }
  .risk, .accent { color: #b42318; }
  h2 { font-size: 20px; font-weight: 600; margin: 40px 0 8px; }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  td { padding: 8px 12px 8px 0; border-bottom: 1px solid #e5e5e5; vertical-align: top; }
  tr:first-child td { border-top: 1px solid #e5e5e5; }
  .owner, .mark { color: #6b6b6b; }
  .mark { font-size: 14px; }
  .num, .due { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .due { white-space: nowrap; }
  .empty { color: #6b6b6b; margin: 0; }
  img { display: block; max-width: 100%; height: auto; margin-top: 8px; }
  @media (max-width: 600px) {
    table, tbody, tr, td { display: block; }
    col { display: none; }
    tr { padding: 8px 0; border-bottom: 1px solid #e5e5e5; }
    tr:first-child { border-top: 1px solid #e5e5e5; }
    td, tr:first-child td { border: 0; padding: 0; }
    .owner, .due, .mark { display: inline; font-size: 14px; color: #6b6b6b; }
    .due::before, .mark:not(:empty)::before { content: " · "; }
    .mark.accent { color: #b42318; }
  }
"""


def ru_date(d):
    return "%d %s" % (d.day, MONTHS[d.month - 1])


def row(task, marks):
    owner = task["owner"].strip()
    if not owner:
        marks = marks + [("ответственный не назначен", False)]
    mark_html = "; ".join('<span class="accent">%s</span>' % html.escape(text) if accent
                          else html.escape(text) for text, accent in marks)
    return ('<tr><td class="task">%s</td><td class="owner">%s</td>'
            '<td class="due">%s</td><td class="mark">%s</td></tr>'
            % (html.escape(task["task"].strip()), html.escape(owner),
               ru_date(date.fromisoformat(task["due"].strip())), mark_html))


def block(title, rows):
    parts = ["<section>", "<h2>%s</h2>" % title]
    if rows:
        parts += ["<table>",
                  '<colgroup><col style="width:44%"><col style="width:18%">'
                  '<col style="width:14%"><col style="width:24%"></colgroup>']
        parts += rows
        parts.append("</table>")
    else:
        parts.append('<p class="empty">Задач нет.</p>')
    parts.append("</section>")
    return parts


def main():
    with open(INPUT, encoding="utf-8", newline="") as f:
        tasks = list(csv.DictReader(f))
    risk, work, done = [], [], []
    for t in tasks:
        status = t["status"].strip()
        due = date.fromisoformat(t["due"].strip())
        if status == "блокер":
            reason = t["note"].strip() or "причина не указана"
            risk.append(row(t, [("блокер: " + reason, True)]))
        elif status != "готово" and due < STATUS_DATE:
            risk.append(row(t, [("просрочено", True)]))
        elif status == "готово":
            done.append(row(t, []))
        else:
            work.append(row(t, []))
    verdict = "Запуск под риском" if risk else "Запуск по плану"
    verdict_class = "verdict risk" if risk else "verdict"
    parts = [
        "<!doctype html>",
        '<html lang="ru">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Статус запуска на %s</title>" % ru_date(STATUS_DATE),
        "<style>",
        STYLE.rstrip("\n"),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        '<p class="subtitle">%s</p>' % html.escape(SUBTITLE),
        '<h1 class="%s">%s</h1>' % (verdict_class, verdict),
        '<p class="meta">Статус на <span class="num">%s</span>. Всего задач: <span class="num">%d</span>.</p>'
        % (ru_date(STATUS_DATE), len(tasks)),
    ]
    parts += block("Блокеры и просрочки", risk)
    parts += block("В работе", work)
    parts += block("Готово", done)
    if CHART.exists():
        parts += ["<section>", "<h2>Рекламные каналы, 1–3 мая</h2>",
                  '<img src="channels.svg" alt="CPL по каналам, 1–3 мая 2026">',
                  "</section>"]
    parts += ["</main>", "</body>", "</html>", ""]
    OUTPUT.parent.mkdir(exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    print("%s: %s, задач %d" % (OUTPUT, verdict, len(tasks)))


if __name__ == "__main__":
    main()
