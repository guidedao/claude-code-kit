---
name: weekly-status
description: Обновляет страницу статуса запуска по новым данным в inputs/. Использовать, когда просят обновить статус. Не коммитит и ничего не отправляет.
disable-model-invocation: true
---

1. Проверь git status для inputs/. Если новых данных нет, скажи об этом и остановись.
2. Запусти python3 scripts/report.py и python3 scripts/build_status.py.
3. Запусти ${CLAUDE_SKILL_DIR}/scripts/check_status.py и покажи результат.
4. Покажи git diff --stat и перескажи изменения страницы по смыслу.
5. Остановись: коммит делает человек после проверки.
