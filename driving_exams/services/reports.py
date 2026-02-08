"""PDF report generation."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QMarginsF, Qt
from PyQt6.QtGui import QFont, QPainter, QPageLayout
from PyQt6.QtPrintSupport import QPrinter


def export_pdf(path: Path, table_widget=None, chart_widget=None, title: str = "Driving Exam Statistics") -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Could not start PDF writer")

    page_rect = printer.pageRect()
    margin = 20
    y = margin

    painter.setFont(QFont("Arial", 14))
    painter.drawText(margin, y + 20, title)
    y += 40

    widgets = [w for w in (table_widget, chart_widget) if w is not None]
    if widgets:
        available_height = page_rect.height() - y - margin
        block_height = available_height // len(widgets)
        for w in widgets:
            pixmap = w.grab()
            target_rect = page_rect
            target_rect.setTop(y)
            target_rect.setHeight(block_height)
            target_rect.setLeft(margin)
            target_rect.setWidth(page_rect.width() - 2 * margin)

            scaled = pixmap.scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(target_rect.left(), target_rect.top(), scaled)
            y += block_height

    painter.end()
