# Отчёт по рекламным каналам: способ расчёта

Вопрос: сколько стоит лид в каждом рекламном канале за 1–3 мая 2026 года.

Вход: inputs/campaigns.csv — 10 строк данных, сумма spend по заполненным ячейкам
34700, сумма revenue 180000, пустых spend 2, строк с channel = unknown 1,
уникальных source 6.

Период: с 1 по 3 мая 2026 года включительно (проверено на inputs/period-test.csv:
входят B и C, не входят A и D).

Формулы: CPC = spend / clicks, CVR = leads / clicks, CPL = spend / leads,
ROAS = revenue / spend — только при известном знаменателе больше нуля.
Пустой spend — «неизвестно»: CPC, CPL и ROAS не считаются, причина в note.
CTR посчитать нельзя: нет показов. Округление до двух знаков.

Команды запуска по порядку, из корня launch-kit:

    python3 scripts/report.py
    python3 scripts/build_status.py

Ожидаемый результат: семь каналов; spend 34700, revenue 180000; CPL email 112,5,
social 270,27, search 333,96, partners 357,14, video 400; у organic и unknown CPL нет.

Вне скоупа: показы и CTR, атрибуция между каналами, данные вне 1–3 мая.
