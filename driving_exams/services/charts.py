"""Chart rendering helpers (QtCharts)."""
from __future__ import annotations

from PyQt6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class ChartWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._chart = QChart()
        self._chart.setTitle("Results by Exam Type")
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def update_chart(self, rows: list[tuple]) -> None:
        self._chart.removeAllSeries()
        if self._chart.axisX() is not None:
            self._chart.removeAxis(self._chart.axisX())
        if self._chart.axisY() is not None:
            self._chart.removeAxis(self._chart.axisY())

        if not rows:
            self._chart.setTitle("No data")
            return

        labels = [r[0] or "Unknown" for r in rows]
        passed_values = [r[1] or 0 for r in rows]
        failed_values = [r[2] or 0 for r in rows]

        passed_set = QBarSet("Passed")
        failed_set = QBarSet("Failed")
        passed_set.append(passed_values)
        failed_set.append(failed_values)

        series = QBarSeries()
        series.append(passed_set)
        series.append(failed_set)

        self._chart.addSeries(series)
        self._chart.setTitle("Results by Exam Type")

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_x.setLabelsAngle(-30)
        self._chart.addAxis(axis_x, axis_x.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Candidates")
        axis_y.setMin(0)
        max_val = max((p + f) for p, f in zip(passed_values, failed_values)) if rows else 0
        axis_y.setMax(max(5, max_val))
        self._chart.addAxis(axis_y, axis_y.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._chart.legend().setVisible(True)
