#!/usr/bin/env python3
"""Проверка скила weekly-status: на странице столько задач, сколько строк в CSV.

Читает inputs/tasks.csv и outputs/status.html, ничего не пишет.
Каждая задача из CSV должна встретиться на странице ровно один раз.
Печатает OK или FAIL с причиной; код выхода 0 — OK, 1 — FAIL.
Запуск из корня launch-kit.
"""
import csv
import html
import re
import sys
from pathlib import Path

TASKS = Path("inputs/tasks.csv")
PAGE = Path("outputs/status.html")


def main():
    with open(TASKS, encoding="utf-8", newline="") as f:
        names = [r["task"].strip() for r in csv.DictReader(f)]
    page = PAGE.read_text(encoding="utf-8")
    body = page.split("<body", 1)[-1]
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    found = {n: text.count(n) for n in names}
    missing = [n for n, c in found.items() if c == 0]
    repeated = [n for n, c in found.items() if c > 1]
    shown = sum(1 for c in found.values() if c > 0)
    if missing or repeated:
        print("FAIL: на странице %d задач из %d строк %s." % (shown, len(names), TASKS))
        if missing:
            print("Нет на странице: " + "; ".join(missing))
        if repeated:
            print("Встречаются больше одного раза: " + "; ".join(repeated))
        sys.exit(1)
    print("OK: на странице %d задач, в %s — %d строк." % (shown, TASKS, len(names)))


if __name__ == "__main__":
    main()
