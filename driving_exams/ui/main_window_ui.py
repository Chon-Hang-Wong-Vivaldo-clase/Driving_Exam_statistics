"""UI setup for MainWindow."""
from __future__ import annotations

from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.uic import loadUi

from services.csv_importer import import_csv
from services.database import Database
from services.reports import export_pdf


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ui_path = Path(__file__).resolve().parent / "main_window.ui"
        loadUi(ui_path, self)

        self._db = Database(self._db_path())
        self.actionExit.triggered.connect(self.close)
        self.actionImportCsv.triggered.connect(self._import_csv)
        self.btnApplyFilters.clicked.connect(self._apply_filters)
        self.btnClearFilters.clicked.connect(self._clear_filters)
        self.btnPrintPdf.clicked.connect(self._export_pdf)

        self._setup_combos()
        self._apply_filters()

    def _db_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "driving_exams.db"

    def _setup_combos(self) -> None:
        for combo in (
            self.comboProvince,
            self.comboExamCenter,
            self.comboDrivingSchool,
            self.comboExamType,
            self.comboPermit,
        ):
            combo.setEditable(True)
            combo.clear()
            combo.addItem("All")

        years = self._db.available_years()
        if not years:
            years = [2020]

        self.comboFromYear.clear()
        self.comboToYear.clear()
        for y in years:
            self.comboFromYear.addItem(str(y))
            self.comboToYear.addItem(str(y))

        self.comboFromYear.setCurrentIndex(0)
        self.comboToYear.setCurrentIndex(len(years) - 1)

        self.comboFromMonth.clear()
        self.comboToMonth.clear()
        for m in range(1, 13):
            self.comboFromMonth.addItem(f"{m:02d}")
            self.comboToMonth.addItem(f"{m:02d}")
        self.comboFromMonth.setCurrentIndex(0)
        self.comboToMonth.setCurrentIndex(11)

        self._refresh_filter_values()

    def _refresh_filter_values(self) -> None:
        years = self._db.available_years()
        if not years:
            years = [2020]

        current_from = self.comboFromYear.currentText()
        current_to = self.comboToYear.currentText()

        self.comboFromYear.blockSignals(True)
        self.comboToYear.blockSignals(True)
        self.comboFromYear.clear()
        self.comboToYear.clear()
        for y in years:
            self.comboFromYear.addItem(str(y))
            self.comboToYear.addItem(str(y))

        if current_from in [str(y) for y in years]:
            self.comboFromYear.setCurrentText(current_from)
        else:
            self.comboFromYear.setCurrentIndex(0)

        if current_to in [str(y) for y in years]:
            self.comboToYear.setCurrentText(current_to)
        else:
            self.comboToYear.setCurrentIndex(len(years) - 1)

        self.comboFromYear.blockSignals(False)
        self.comboToYear.blockSignals(False)

        self._fill_combo(self.comboProvince, self._db.distinct_values("province"))
        self._fill_combo(self.comboExamCenter, self._db.distinct_values("exam_center"))
        self._fill_combo(self.comboDrivingSchool, self._db.distinct_values("driving_school_name"))
        self._fill_combo(self.comboExamType, self._db.distinct_values("exam_type"))
        self._fill_combo(self.comboPermit, self._db.distinct_values("permit_name"))

    def _fill_combo(self, combo: QtWidgets.QComboBox, values: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All")
        for v in values:
            combo.addItem(v)
        if current:
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _filters(self) -> dict:
        from_year = int(self.comboFromYear.currentText())
        to_year = int(self.comboToYear.currentText())
        from_month = int(self.comboFromMonth.currentText())
        to_month = int(self.comboToMonth.currentText())

        return {
            "province": self._value_or_none(self.comboProvince),
            "exam_center": self._value_or_none(self.comboExamCenter),
            "driving_school": self._value_or_none(self.comboDrivingSchool),
            "exam_type": self._value_or_none(self.comboExamType),
            "permit": self._value_or_none(self.comboPermit),
            "from_ym": from_year * 100 + from_month,
            "to_ym": to_year * 100 + to_month,
        }

    def _value_or_none(self, combo: QtWidgets.QComboBox) -> str | None:
        value = combo.currentText().strip()
        return None if value == "All" or not value else value

    def _apply_filters(self) -> None:
        headers, rows = self._db.fetch_table(self._filters())
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(headers)

        for row in rows:
            items = [QStandardItem(str(value)) for value in row]
            model.appendRow(items)

        self.tableView.setModel(model)
        self.tableView.resizeColumnsToContents()

    def _clear_filters(self) -> None:
        for combo in (
            self.comboProvince,
            self.comboExamCenter,
            self.comboDrivingSchool,
            self.comboExamType,
            self.comboPermit,
        ):
            combo.setCurrentIndex(0)
        self.comboFromMonth.setCurrentIndex(0)
        self.comboToMonth.setCurrentIndex(11)
        self._apply_filters()

    def _import_csv(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Import CSV/TXT", "", "*.csv *.txt")
        if not path_str:
            return

        try:
            inserted = import_csv(Path(path_str), self._db)
            self._refresh_filter_values()
            self._apply_filters()
            QMessageBox.information(self, "Import Complete", f"Inserted {inserted} rows")
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))

    def _export_pdf(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(self, "Export PDF", "report.pdf", "PDF Files (*.pdf)")
        if not path_str:
            return

        try:
            export_pdf(Path(path_str), table_widget=self.tableView, chart_widget=None)
            QMessageBox.information(self, "Export Complete", "PDF exported")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
