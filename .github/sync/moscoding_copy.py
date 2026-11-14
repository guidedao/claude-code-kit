#!/usr/bin/env python3
"""Собирает копию учебного набора для Moscow Coding School из набора Guide DAO.

    python3 moscoding_copy.py ПАПКА-НАБОРА-GUIDEDAO ПАПКА-КЛОНА-MOSCODING
    python3 moscoding_copy.py --message < сообщение-коммита

Ученики Moscow Coding School проходят те же уроки, что и ученики Guide DAO, но платформа ведёт их
в копию набора github.com/moscoding/claude-code-kit без имени Guide DAO (решение владельца 24.10.2026,
lms: shared/brands.mjs). Копию собирает этот скрипт, а запускает .github/workflows/sync-moscoding.yml
при каждом пуше в main, поэтому копия не отстаёт от набора.

Копирует все файлы набора, кроме .git и .github в корне (служебное репозитория guidedao), заменяет
в текстовых файлах имя и адреса Guide DAO на Moscow Coding School и удаляет из копии файлы, которых
в наборе больше нет. Если после замены где-то осталось «guidedao» или «Guide DAO», печатает находки
и выходит с кодом 1: правило надо дописать, а не публиковать копию с чужим именем. С --message
заменяет имя в сообщении коммита из stdin. Только стандартная библиотека.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

# Порядок важен: сначала адреса и составные имена, потом голое имя.
RULES = [
    (re.compile(r"(github\.com|raw\.githubusercontent\.com)/guidedao/(claude-code-kit|vibecoding-kit|llm-wiki-agent)(?=\.git\b|[^\w.-]|$)"), r"\1/moscoding/\2"),
    (re.compile(r"yo@guidedao\.xyz"), "courses@moscoding.ru"),
    (re.compile(r"learn\.guidedao\.xyz"), "courses.moscoding.ru"),
    (re.compile(r"(?:www\.)?guidedao\.xyz", re.I), "moscoding.ru"),
    (re.compile(r"guidedao-launch"), "moscoding-launch"),
    # Служебная подпись временных коммитов в самопроверках набора (start/verify.py).
    (re.compile(r"\d+\+guidedao@users\.noreply\.github\.com"), "yo@moscoding.ru"),
    (re.compile(r"user\.name=guidedao\b"), "user.name=moscoding"),
    (re.compile(r"Guide ?DAO"), "Moscow Coding School"),
]
LEFTOVER = re.compile(r"guide ?dao", re.I)
# Только в корне: .github набора guidedao — его служебное (синхронизация), а .github внутри start/ и ci/ — учебные файлы.
SKIP = {".git", ".github"}


def files(root: Path):
    return sorted(p.relative_to(root) for p in root.rglob("*")
                  if p.is_file() and p.relative_to(root).parts[0] not in SKIP)


def rebrand(text: str) -> str:
    for rx, repl in RULES:
        text = rx.sub(repl, text)
    return text


def main():
    if sys.argv[1:] == ["--message"]:
        text = rebrand(sys.stdin.read())
        if LEFTOVER.search(text):
            print("В сообщении коммита осталось имя Guide DAO — допишите правило в RULES.", file=sys.stderr)
            sys.exit(1)
        print(text.strip())
        return
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    src, dst = (Path(a).resolve() for a in sys.argv[1:])
    if not (dst / ".git").exists():
        print(f"{dst}: нужна папка клона копии (с .git)")
        sys.exit(2)
    wanted = set(files(src))
    for rel in set(files(dst)) - wanted:
        (dst / rel).unlink()
    leftovers = []
    for rel in wanted:
        data = (src / rel).read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            out = data
        else:
            text = rebrand(text)
            leftovers += [f"{rel}: {m.group(0)}" for m in LEFTOVER.finditer(text)]
            out = text.encode("utf-8")
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(out)
        shutil.copymode(src / rel, target)
    for path in sorted(dst.rglob("*"), reverse=True):
        if path.is_dir() and path.relative_to(dst).parts[0] not in SKIP and not any(path.iterdir()):
            path.rmdir()
    if leftovers:
        print("В копии осталось имя Guide DAO — допишите правило в RULES:")
        print("\n".join(leftovers))
        sys.exit(1)


if __name__ == "__main__":
    main()
