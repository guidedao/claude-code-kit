# claude-code-kit

Учебный набор курса GuideDAO «Основы Claude Code»: входные файлы практик и контрольные скрипты.

## Как поставить

Набор лежит рядом с вашим проектом `launch-kit`, а не внутри него. Так Claude не правит проверку вместе с решением. Из папки `launch-kit`:

```bash
git clone https://github.com/guidedao/claude-code-kit ../claude-code-kit
```

Получится две соседние папки:

```text
launch-kit/          ваш проект, здесь работает Claude
claude-code-kit/     набор: входные файлы и проверки
```

Перед каждой новой практикой обновите набор:

```bash
git -C ../claude-code-kit pull
```

Свои файлы в наборе не меняйте: `pull` тогда проходит без конфликтов. Всё, что делаете в практике, остаётся в `launch-kit`.

## Практики

Команды проверки запускаются из папки `launch-kit`.

| Папка | Модуль | Практика | Проверка |
| --- | --- | --- | --- |
| `contract-redline/` | 4. Документы: Google Docs, Word и PDF | Договор с подрядчиком | `python3 ../claude-code-kit/contract-redline/checks/check_contract.py` |
| `claims-check/` | 5. Исследование и проверка фактов | Сверка утверждений с источниками | `python3 ../claude-code-kit/claims-check/checks/check_claims.py` |
| `crm-reconcile/` | 6. Таблицы: Google Sheets и Excel | Сверка выгрузок CRM | `python3 ../claude-code-kit/crm-reconcile/checks/check_reconcile.py` |
| `table-traps/` | 6. Таблицы: Google Sheets и Excel | Ловушки таблиц | разбор: ответы сверяются с уроком, скрипта нет |
| `ab-test/` | 7. Анализ данных и статистика | Решение по A/B-тесту первого экрана | `python3 ../claude-code-kit/ab-test/checks/check_ab.py` |
| `channels-report/` | 8. Скрипты и графики | Отчёт по рекламным каналам | `python3 ../claude-code-kit/channels-report/checks/check_channels.py` |
| `charts/` | 8. Скрипты и графики | Шесть графиков | разбор: ответы сверяются с уроком, скрипта нет |
| `code-reading/` | 10. Код: чтение, запуск, отладка | Четыре фрагмента кода | `python3 ../claude-code-kit/code-reading/checks/check_reading.py` |
| `buggy-report/` | 10. Код: чтение, запуск, отладка | Три бага в недельном отчёте | `python3 ../claude-code-kit/buggy-report/checks/check_bugs.py` |
| `git-drill/` | 11. Git и GitHub в команде | Ветка, конфликт и откат | `python3 ../claude-code-kit/git-drill/checks/check_git_drill.py` |
| `ci/` | 11. Git и GitHub в команде | Pull request с проверками CI | `python3 ../claude-code-kit/ci/checks/check_repo.py`, после слияния PR — `python3 ../claude-code-kit/ci/checks/check_pr.py` |

## Как устроена практика

- `<папка>/inputs/` — файлы, которые практика просит скопировать в `launch-kit/inputs/`.
- `<папка>/checks/check_<имя>.py` — автопроверка.
- `<папка>/README.md` — что скопировать и куда.

Некоторые папки устроены иначе. В разборах `table-traps/` и `charts/` лежат только файлы для просмотра. В `channels-report/` нет `inputs/`: данные практика создаёт текстом из урока. `git-drill/` собирает учебный репозиторий скриптом `setup.py`, а `ci/kit-files/` повторяет пути проекта. Что копировать, написано в README папки.

Проверка печатает по строке на критерий: `✔` — выполнен, `✘` — нет, с подсказкой, куда смотреть. Последняя строка — «Итог: N из M». Код выхода 0 — всё пройдено, 1 — есть непройденные критерии, 2 — проверку нельзя провести.

Проверки написаны на стандартной библиотеке Python 3.9+ (подходит системный `python3` macOS): ставить пакеты не нужно.

## Эталоны

Эталонных решений в наборе нет: ни готовых документов, ни скриптов, ни таблиц. Проверка сверяет ваш результат с правилами и контрольными значениями из `checks/expected/` и печатает только «совпало или нет» и подсказку. Контрольные значения раскрывают ответы, поэтому не открывайте эту папку до проверки. Если Claude просит её открыть, откажите: сравнение — работа проверки, а не модели.

Все данные синтетические: имена из сюжета курса, ссылки вида `mock://`.

## Для авторов набора

Тесты общего раннера `kitlib/check.py`: `python3 -m unittest discover -s tests`. Генераторы файлов и приёмка набора живут в отдельном закрытом репозитории.

Лицензия MIT.
