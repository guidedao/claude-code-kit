#!/usr/bin/env python3
"""Сводка по рекламным каналам за 1–3 мая 2026 года.

Вход: inputs/campaigns.csv. Период: с 1 по 3 мая 2026 года включительно.
Правила: суммы spend, clicks, leads, revenue по channel; CPC = spend / clicks,
CVR = leads / clicks, CPL = spend / leads, ROAS = revenue / spend — только при
известном знаменателе больше нуля, округление до двух знаков. Пустой spend —
«неизвестно»: метрики с расходом не считаются, причина в note. CTR нет: нет показов.
Выход: outputs/channel-summary.csv и outputs/channels.svg — столбцы CPL
по возрастанию, ось от нуля, каналы без CPL перечислены под графиком.
Запуск из корня launch-kit: python3 scripts/report.py
"""

import csv
from pathlib import Path
from xml.sax.saxutils import escape

INPUT = Path("inputs/campaigns.csv")
SUMMARY = Path("outputs/channel-summary.csv")
CHART = Path("outputs/channels.svg")
PERIOD = ("2026-05-01", "2026-05-03")


def read_rows(path):
    """Строки выгрузки, дата которых попадает в период, границы включительно."""
    with open(path, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f)
                if PERIOD[0] <= r["date"].strip()[:10] <= PERIOD[1]]


def ratio(a, b):
    """a / b с округлением до двух знаков; None, если a неизвестно или b не больше нуля."""
    if a is None or b is None or b <= 0:
        return None
    return round(a / b, 2)


def summarize(rows):
    """Суммы и метрики по каждому channel; каналы по алфавиту."""
    acc = {}
    for r in rows:
        a = acc.setdefault(r["channel"].strip(), {"spend": 0.0, "clicks": 0, "leads": 0,
                                                   "revenue": 0.0, "spend_known": True})
        if r["spend"].strip():
            a["spend"] += float(r["spend"])
        else:
            a["spend_known"] = False
        a["clicks"] += int(r["clicks"])
        a["leads"] += int(r["leads"])
        a["revenue"] += float(r["revenue"])
    table = []
    for channel in sorted(acc):
        a = acc[channel]
        spend = a["spend"] if a["spend_known"] else None
        table.append({
            "channel": channel, "spend": spend, "clicks": a["clicks"], "leads": a["leads"],
            "revenue": a["revenue"], "cpc": ratio(spend, a["clicks"]),
            "cvr": ratio(a["leads"], a["clicks"]), "cpl": ratio(spend, a["leads"]),
            "roas": ratio(a["revenue"], spend),
            "note": "" if a["spend_known"] else "spend не указан: CPC, CPL и ROAS не считаются",
        })
    return table


def write_summary(table, path):
    """Сводка в CSV: деньги целыми, метрики с двумя знаками, неизвестное — пусто."""
    fields = ["channel", "spend", "clicks", "leads", "revenue", "cpc", "cvr", "cpl", "roas", "note"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for t in table:
            out = dict(t)
            out["spend"] = "" if t["spend"] is None else "%.0f" % t["spend"]
            out["revenue"] = "%.0f" % t["revenue"]
            for k in ("cpc", "cvr", "cpl", "roas"):
                out[k] = "" if t[k] is None else t[k]
            w.writerow(out)


def draw_chart(table, path):
    """Горизонтальные столбцы CPL по возрастанию, ось от нуля, вид — по style.md."""
    bars = sorted((t for t in table if t["cpl"] is not None), key=lambda t: t["cpl"])
    missing = [t["channel"] for t in table if t["cpl"] is None]
    top = max(t["cpl"] for t in bars)
    step = 10 ** (len(str(int(top))) - 1)
    while top / step > 5:
        step *= 2
    scale_max = step * (int(top // step) + (1 if top % step else 0))
    left, plot_w, bar_h, gap, y0 = 96, 440, 20, 14, 48
    x = lambda v: left + plot_w * v / scale_max
    axis_y = y0 + len(bars) * (bar_h + gap)
    height = axis_y + 64
    sans = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif"
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="640" height="%d" viewBox="0 0 640 %d" '
             'font-family="%s" font-size="16" fill="#1a1a1a">' % (height, height, sans),
             '<rect width="640" height="%d" fill="#ffffff"/>' % height,
             '<text x="0" y="24">CPL по каналам, 1–3 мая 2026, ₽ за лид</text>']
    for i, t in enumerate(bars):
        y = y0 + i * (bar_h + gap)
        parts.append('<text x="0" y="%d">%s</text>' % (y + 15, escape(t["channel"])))
        parts.append('<rect x="%d" y="%d" width="%.1f" height="%d" fill="#1a1a1a"/>'
                     % (left, y, x(t["cpl"]) - left, bar_h))
        parts.append('<text x="%.1f" y="%d" font-family="%s">%d</text>'
                     % (x(t["cpl"]) + 8, y + 15, mono, int(t["cpl"] + 0.5)))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#6b6b6b" stroke-width="1"/>'
                 % (left, axis_y, left + plot_w, axis_y))
    for v in range(0, int(scale_max) + 1, int(step)):
        parts.append('<text x="%.1f" y="%d" font-size="14" fill="#6b6b6b" text-anchor="middle" '
                     'font-family="%s">%d</text>' % (x(v), axis_y + 18, mono, v))
    if missing:
        parts.append('<text x="0" y="%d" font-size="14" fill="#6b6b6b">Без CPL: %s — spend не указан.</text>'
                     % (axis_y + 48, escape(", ".join(missing))))
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    rows = read_rows(INPUT)
    table = summarize(rows)
    SUMMARY.parent.mkdir(exist_ok=True)
    write_summary(table, SUMMARY)
    draw_chart(table, CHART)
    spend = sum(t["spend"] for t in table if t["spend"] is not None)
    revenue = sum(t["revenue"] for t in table)
    missing = [t["channel"] for t in table if t["cpl"] is None]
    print("Каналов: %d. spend %.0f, revenue %.0f. Без CPL: %s."
          % (len(table), spend, revenue, ", ".join(missing) or "нет"))


if __name__ == "__main__":
    main()
