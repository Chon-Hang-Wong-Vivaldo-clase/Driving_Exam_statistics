"""PDF report generation."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QMarginsF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPdfWriter, QPageSize


def export_pdf(path: Path, table_widget=None, chart_widget=None, title: str = "Driving Exam Statistics") -> None:
    if path.suffix.lower() != ".pdf":
        path = path.with_suffix(".pdf")

    pdf = QPdfWriter(str(path))
    pdf.setResolution(96)
    pdf.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    pdf.setPageMargins(QMarginsF(15, 15, 15, 15))
    page_rect = pdf.pageLayout().paintRectPixels(pdf.resolution())
    page_width = page_rect.width()
    page_height = page_rect.height()

    painter = QPainter(pdf)
    if not painter.isActive():
        raise RuntimeError("Could not start PDF writer")

    def new_page() -> None:
        if not pdf.newPage():
            raise RuntimeError("Could not create new PDF page")

    # Title
    y = 0
    title_font = QFont("Arial", 14)
    painter.setFont(title_font)
    title_metrics = QFontMetrics(title_font, pdf)
    y += title_metrics.height()
    painter.drawText(0, y, page_width, title_metrics.height(), Qt.AlignmentFlag.AlignHCenter, title)
    y += title_metrics.height() // 2

    # Chart (optional)
    if chart_widget is not None:
        pixmap = chart_widget.grab()
        if not pixmap.isNull():
            max_chart_height = int(page_height * 0.35)
            scaled = pixmap.scaled(
                page_width,
                max_chart_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if y + scaled.height() > page_height:
                new_page()
                y = 0
            painter.drawPixmap(0, y, scaled)
            y += scaled.height() + 10

    # Table (optional)
    if table_widget is not None and table_widget.model() is not None:
        model = table_widget.model()
        cols = model.columnCount()
        rows = model.rowCount()
        if cols > 0:
            cell_padding = 4
            header_font = QFont("Arial", 8, QFont.Weight.Bold)
            body_font = QFont("Arial", 8)
            header_metrics = QFontMetrics(header_font, pdf)
            body_metrics = QFontMetrics(body_font, pdf)

            # Estimate column widths (header + sample rows)
            sample_rows = min(rows, 50)
            col_widths: list[int] = []
            for col in range(cols):
                header = str(model.headerData(col, Qt.Orientation.Horizontal))
                max_w = header_metrics.horizontalAdvance(header)
                for row in range(sample_rows):
                    data = str(model.index(row, col).data())
                    max_w = max(max_w, body_metrics.horizontalAdvance(data))
                col_widths.append(max_w + cell_padding * 2 + 8)

            # Split columns into groups that fit on the page
            col_groups: list[list[int]] = []
            current: list[int] = []
            current_width = 0
            for col, w in enumerate(col_widths):
                w = max(60, min(w, 300))
                if current and current_width + w > page_width:
                    col_groups.append(current)
                    current = []
                    current_width = 0
                current.append(col)
                current_width += w
            if current:
                col_groups.append(current)

            header_height = header_metrics.height() + cell_padding * 2
            row_height = body_metrics.height() + cell_padding * 2

            for group_index, group in enumerate(col_groups):
                if y + header_height > page_height:
                    new_page()
                    y = 0
                if group_index > 0:
                    new_page()
                    y = 0

                # Draw header
                painter.setFont(header_font)
                painter.setPen(QColor("#000000"))
                painter.setBrush(QColor("#dddddd"))
                x = 0
                for col in group:
                    w = max(60, min(col_widths[col], 300))
                    rect = QRectF(x, y, w, header_height)
                    painter.drawRect(rect)
                    header = str(model.headerData(col, Qt.Orientation.Horizontal))
                    painter.drawText(
                        rect.adjusted(cell_padding, 0, -cell_padding, 0),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                        header,
                    )
                    x += w
                painter.setBrush(Qt.BrushStyle.NoBrush)
                y += header_height

                # Draw rows
                painter.setFont(body_font)
                for row in range(rows):
                    if y + row_height > page_height:
                        new_page()
                        y = 0
                        # Re-draw header on new page
                        painter.setFont(header_font)
                        painter.setBrush(QColor("#dddddd"))
                        x = 0
                        for col in group:
                            w = max(60, min(col_widths[col], 300))
                            rect = QRectF(x, y, w, header_height)
                            painter.drawRect(rect)
                            header = str(model.headerData(col, Qt.Orientation.Horizontal))
                            painter.drawText(
                                rect.adjusted(cell_padding, 0, -cell_padding, 0),
                                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                                header,
                            )
                            x += w
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        y += header_height
                        painter.setFont(body_font)

                    x = 0
                    for col in group:
                        w = max(60, min(col_widths[col], 300))
                        rect = QRectF(x, y, w, row_height)
                        painter.setPen(QColor("#000000"))
                        painter.drawRect(rect)
                        data = str(model.index(row, col).data())
                        elided = body_metrics.elidedText(
                            data, Qt.TextElideMode.ElideRight, int(w - cell_padding * 2)
                        )
                        painter.drawText(
                            rect.adjusted(cell_padding, 0, -cell_padding, 0),
                            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                            elided,
                        )
                        x += w
                    y += row_height

    painter.end()
