#!/usr/bin/env python3
"""Сверка выгрузок CRM: сентябрь (CSV) и октябрь (XLSX) по work/reconcile-plan.md.

Вход: inputs/crm-leads-sept.csv и inputs/crm-leads-oct.xlsx, их не меняет.
Выход: outputs/reconcile.xlsx — листы «Сводка», «Расхождения», «Сентябрь»,
«Октябрь»; в «Сводке» только формулы, книга пересчитывается при открытии.
Печатает контрольные числа, по которым проверяют инварианты плана.
Только стандартная библиотека. Запуск из корня launch-kit:
    python3 scripts/reconcile.py
"""
import csv
import datetime as dt
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
FIELDS = ["lead_id", "created_at", "channel", "plan", "status", "amount"]


# Правило 3: статус — без пробелов по краям и в нижнем регистре.
def norm_status(s):
    return (s or "").strip().lower()


# Правило 4: сумма «4900,00» — число 4900.
def to_amount(v):
    if isinstance(v, float):
        return v
    return float(str(v).replace(" ", "").replace(" ", "").replace(",", "."))


# Правило 5: дата ДД.ММ.ГГГГ — та же дата.
def to_date(v):
    if isinstance(v, float):
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    v = str(v).strip()
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v):
        d, m, y = v.split(".")
        return dt.date(int(y), int(m), int(d))
    return dt.date.fromisoformat(v)


def read_sept(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = to_amount(r["amount"])
        r["created_at"] = to_date(r["created_at"])
        r["status"] = norm_status(r["status"])
    return rows


# Правило 6: скрытая строка — обычный лид. Скрипт читает XML листа
# и скрытость строк не учитывает, поэтому такие строки идут в сверку как все.
def read_oct(path):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(M + "si"):
            shared.append("".join(t.text or "" for t in si.iter(M + "t")))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    table = []
    for row in sheet.iter(M + "row"):
        vals = {}
        for c in row.iter(M + "c"):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            t = c.get("t")
            if t == "inlineStr":
                v = "".join(x.text or "" for x in c.iter(M + "t"))
            elif t == "s":
                v = shared[int(c.find(M + "v").text)]
            else:
                v = float(c.find(M + "v").text)
            vals[col] = v
        table.append([vals.get(ch) for ch in "ABCDEF"])
    header = [str(h) for h in table[0]]
    rows = []
    for n, raw in enumerate(table[1:], start=2):
        r = dict(zip(header, raw))
        r["amount"] = to_amount(r["amount"])
        r["created_at"] = to_date(r["created_at"])
        r["status"] = norm_status(r["status"])
        r["_row"] = n
        rows.append(r)
    return rows


# Правила 1, 2 и 7: ключ — lead_id; повтор ключа в октябре идёт в сверку
# один раз и отчитывается как дубликат; сравнивается только status.
def reconcile(sept, octo):
    seen, unique, dups = {}, [], []
    for r in octo:
        if r["lead_id"] in seen:
            dups.append(r)
        else:
            seen[r["lead_id"]] = r
            unique.append(r)
    s = {r["lead_id"]: r for r in sept}
    diffs = []
    for lid, r in s.items():
        if lid not in seen:
            diffs.append([lid, "пропал", r["status"], "", "нет в октябрьской выгрузке"])
        elif seen[lid]["status"] != r["status"]:
            diffs.append([lid, "статус изменён", r["status"], seen[lid]["status"], ""])
    for r in unique:
        if r["lead_id"] not in s:
            diffs.append([r["lead_id"], "новый", "", r["status"], ""])
    for r in dups:
        diffs.append([r["lead_id"], "дубликат", "", r["status"], f"повтор, строка {r['_row']} исходника"])
    return unique, dups, diffs


# ---------- запись xlsx без внешних библиотек ----------

def colname(n):
    s = ""
    while n:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def cell(ref, v):
    if isinstance(v, dict):
        return f'<c r="{ref}"><f>{escape(v["f"])}</f></c>'
    if isinstance(v, dt.date):
        return f'<c r="{ref}" s="1"><v>{(v - dt.date(1899, 12, 30)).days}</v></c>'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"><v>{v}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'


def sheet(rows):
    body = []
    for i, row in enumerate(rows, start=1):
        body.append(f'<row r="{i}">' + "".join(cell(f"{colname(j)}{i}", v) for j, v in enumerate(row, start=1)) + "</row>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData>' + "".join(body) + '</sheetData></worksheet>')


def write_book(path, sheets):
    names = list(sheets)
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    ct += [f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(names) + 1)]
    ct.append("</Types>")
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
          + '</sheets><calcPr fullCalcOnLoad="1"/></workbook>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(names) + 1))
            + f'<Relationship Id="rId{len(names)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts>'
              '<fonts count="1"><font><sz val="11"/><name val="Arial"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
              '</styleSheet>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    parts = [("[Content_Types].xml", "".join(ct)), ("_rels/.rels", root_rels),
             ("xl/workbook.xml", wb), ("xl/_rels/workbook.xml.rels", rels), ("xl/styles.xml", styles)]
    parts += [(f"xl/worksheets/sheet{i}.xml", sheet(sheets[n])) for i, n in enumerate(names, 1)]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            # постоянная дата внутри архива: одинаковые данные дают одинаковый файл
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 1, 0, 0, 0)), data,
                       compress_type=zipfile.ZIP_DEFLATED)


def main():
    sept = read_sept("inputs/crm-leads-sept.csv")
    octo = read_oct("inputs/crm-leads-oct.xlsx")
    unique, dups, diffs = reconcile(sept, octo)
    data = lambda rows: [FIELDS] + [[r[k] for k in FIELDS] for r in rows]
    F = lambda f: {"f": f}
    # Инварианты плана — формулами в «Сводке»: совпали = строк в сентябре − пропали,
    # строк в октябрьском файле = уникальные + дубликаты, «Проверка» — уникальные = совпали + новые.
    summary = [
        ["Показатель", "Значение"],
        ["Строк в сентябре", F("COUNTA(Сентябрь!A:A)-1")],
        ["Уникальных лидов в октябре", F("COUNTA(Октябрь!A:A)-1")],
        ["Дубликаты в октябре", F('COUNTIF(Расхождения!B:B,"дубликат")')],
        ["Строк в октябрьском файле", F("B3+B4")],
        ["Совпали по ключу", F("B2-B7")],
        ["Пропали", F('COUNTIF(Расхождения!B:B,"пропал")')],
        ["Новые", F('COUNTIF(Расхождения!B:B,"новый")')],
        ["Изменили статус", F('COUNTIF(Расхождения!B:B,"статус изменён")')],
        ["Сумма amount, сентябрь", F("SUM(Сентябрь!F:F)")],
        ["Сумма amount, октябрь", F("SUM(Октябрь!F:F)")],
        ["Проверка", F('IF(B3=B6+B8,"сходится","не сходится")')],
    ]
    Path("outputs").mkdir(exist_ok=True)
    write_book("outputs/reconcile.xlsx", {
        "Сводка": summary,
        "Расхождения": [["lead_id", "тип", "статус в сентябре", "статус в октябре", "комментарий"]] + diffs,
        "Сентябрь": data(sept),
        "Октябрь": data(unique),
    })
    count = lambda t: sum(1 for d in diffs if d[1] == t)
    print(f"Сентябрь: {len(sept)} строк. Октябрь: {len(octo)} строк, уникальных {len(unique)}, дубликатов {len(dups)}.")
    print(f"Совпали {len(sept) - count('пропал')}, пропали {count('пропал')}, новые {count('новый')}, "
          f"изменили статус {count('статус изменён')}.")
    print(f"Сумма amount: сентябрь {sum(r['amount'] for r in sept):.2f}, октябрь {sum(r['amount'] for r in unique):.2f}.")


if __name__ == "__main__":
    main()
