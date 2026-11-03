"""Тесты сводки по рекламным каналам: scripts/report.py на учебных данных 1–3 мая.

Контрольные числа — из outputs/method.md. Запуск из корня launch-kit:
python3 -m unittest -v
"""
import csv
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("report", ROOT / "scripts" / "report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def row(date, channel, spend, clicks=10, leads=2, revenue=1000):
    return {"date": date, "channel": channel, "spend": spend, "clicks": str(clicks),
            "leads": str(leads), "revenue": str(revenue)}


class ReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = report.read_rows(ROOT / "inputs" / "campaigns.csv")
        cls.table = {t["channel"]: t for t in report.summarize(rows)}

    def test_control_totals(self):
        """Расход 34 700 и выручка 180 000, как в method.md."""
        spend = sum(t["spend"] for t in self.table.values() if t["spend"] is not None)
        revenue = sum(t["revenue"] for t in self.table.values())
        self.assertEqual(spend, 34700)
        self.assertEqual(revenue, 180000)

    def test_seven_channels(self):
        """В сводке семь каналов."""
        self.assertEqual(len(self.table), 7)

    def test_cpl_values(self):
        """CPL с двумя знаками: email 112,5, social 270,27, search 333,96."""
        self.assertEqual(self.table["email"]["cpl"], 112.5)
        self.assertEqual(self.table["social"]["cpl"], 270.27)
        self.assertEqual(self.table["search"]["cpl"], 333.96)

    def test_empty_spend_is_unknown(self):
        """Пустой spend — неизвестно, а не ноль: CPL и ROAS не считаются, причина в note."""
        organic = self.table["organic"]
        self.assertIsNone(organic["spend"])
        self.assertIsNone(organic["cpl"])
        self.assertIsNone(organic["roas"])
        self.assertIn("spend не указан", organic["note"])

    def test_period_bounds_inclusive(self):
        """Границы периода включены: 1 и 3 мая входят, 30 апреля и 4 мая — нет."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "period.csv"
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["date", "channel", "spend", "clicks", "leads", "revenue"])
                w.writeheader()
                for d in ("2026-04-30", "2026-05-01", "2026-05-03", "2026-05-04"):
                    w.writerow(row(d, "search", "100"))
            dates = [r["date"] for r in report.read_rows(path)]
        self.assertEqual(dates, ["2026-05-01", "2026-05-03"])

    def test_zero_denominator(self):
        """Знаменатель ноль или неизвестен — метрики нет."""
        self.assertIsNone(report.ratio(100, 0))
        self.assertIsNone(report.ratio(None, 5))
        self.assertEqual(report.ratio(1, 3), 0.33)

    def test_script_writes_outputs(self):
        """Скрипт в копии проекта пишет сводку на семь каналов и график с каналами без CPL."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "launch-kit"
            (work / "inputs").mkdir(parents=True)
            (work / "scripts").mkdir()
            shutil.copy(ROOT / "inputs" / "campaigns.csv", work / "inputs")
            shutil.copy(ROOT / "scripts" / "report.py", work / "scripts")
            subprocess.run([sys.executable, "scripts/report.py"], cwd=work, check=True,
                           capture_output=True, text=True, timeout=60)
            with open(work / "outputs" / "channel-summary.csv", encoding="utf-8", newline="") as f:
                summary = list(csv.DictReader(f))
            chart = (work / "outputs" / "channels.svg").read_text(encoding="utf-8")
        self.assertEqual(len(summary), 7)
        self.assertIn("Без CPL: organic, unknown", chart)


if __name__ == "__main__":
    unittest.main()
