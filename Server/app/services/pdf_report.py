"""
Professional PDF market intelligence report generator.
Clean, minimal design with blue/navy color scheme suitable for financial reports.
"""
from __future__ import annotations

import io
import math
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.colors import HexColor

from app.core.config import Settings
from app.models.prediction import Prediction

# Professional color palette (finance/business standard)
COLOR_NAVY = HexColor("#1e3a8a")  # Dark blue
COLOR_BLUE = HexColor("#2563eb")  # Professional blue
COLOR_WHITE = HexColor("#ffffff")
COLOR_TEXT = HexColor("#1f2937")  # Dark grey
COLOR_TEXT_LIGHT = HexColor("#6b7280")  # Medium grey
COLOR_BG = HexColor("#f9fafb")  # Off-white background
COLOR_BORDER = HexColor("#e5e7eb")  # Light grey border
COLOR_BUY = HexColor("#16a34a")  # Green (for bullish)
COLOR_SELL = HexColor("#dc2626")  # Red (for bearish)


def _position_alloc(confidence: int, budget: float) -> float:
    """Return capital to allocate based on confidence tier."""
    if confidence >= 80:
        pct = 0.15
    elif confidence >= 70:
        pct = 0.10
    elif confidence >= 60:
        pct = 0.07
    else:
        pct = 0.05
    return round(budget * pct, 2)


def generate_pdf(predictions: list[Prediction], settings: Settings) -> bytes:
    """Generate a professional PDF report and return as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    report_date = date.today().strftime("%B %d, %Y")

    # ─── Header ───────────────────────────────────────────────────────
    header = Paragraph(
        "OpenBell<br/>Market Intelligence Report",
        ParagraphStyle(
            'Header',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=COLOR_NAVY,
            alignment=0,  # left
            spaceAfter=6,
            fontName='Helvetica-Bold',
        ),
    )
    story.append(header)

    # Metadata line
    meta = Paragraph(
        f"<font color='#6b7280' size=10>Analysis Date: {report_date}</font>",
        ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            textColor=COLOR_TEXT_LIGHT,
            alignment=0,
            spaceAfter=12,
        ),
    )
    story.append(meta)

    # Divider
    story.append(Spacer(1, 0.1 * inch))

    # ─── Executive Summary ────────────────────────────────────────────
    story.append(Paragraph(
        "Executive Summary",
        ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=COLOR_NAVY,
            spaceAfter=10,
            fontName='Helvetica-Bold',
        ),
    ))

    bullish = [p for p in predictions if p.signal == "bullish" and p.confidence >= 60]
    bearish = [p for p in predictions if p.signal == "bearish" and p.confidence >= 60]
    avg_conf = round(sum(p.confidence for p in predictions) / len(predictions), 1) if predictions else 0

    summary_data = [
        ["Stocks Analyzed", str(len(predictions))],
        ["Buy Signals (≥60%)", str(len(bullish))],
        ["Sell Alerts (≥60%)", str(len(bearish))],
        ["Avg. Confidence", f"{avg_conf}%"],
        ["Portfolio Budget", f"₹{settings.PORTFOLIO_BUDGET:,.0f}"],
    ]

    summary_table = Table(summary_data, colWidths=[2.2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), COLOR_BG),
        ('BACKGROUND', (1, 0), (1, -1), COLOR_WHITE),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXT),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [COLOR_WHITE, COLOR_BG]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # ─── Top Buy Recommendations ──────────────────────────────────────
    if bullish:
        story.append(Paragraph(
            "Top Buy Recommendations",
            ParagraphStyle(
                'SectionHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=COLOR_NAVY,
                spaceAfter=12,
                fontName='Helvetica-Bold',
            ),
        ))

        for rank, pred in enumerate(bullish[:10], 1):
            alloc = _position_alloc(pred.confidence, settings.PORTFOLIO_BUDGET)
            qty = max(1, math.floor(alloc / pred.limit_price)) if pred.limit_price else 0
            stop = round(pred.limit_price * 0.97, 2)
            rr = round((pred.target_high - pred.limit_price) / (pred.limit_price - stop), 2) if (pred.limit_price - stop) else 0
            upside_pct = round(((pred.target_high - pred.limit_price) / pred.limit_price * 100), 1) if pred.limit_price else 0

            # Stock header
            header_text = f"<b>{rank}. {pred.ticker}</b> — {pred.confidence}% Confidence"
            story.append(Paragraph(
                header_text,
                ParagraphStyle(
                    'StockName',
                    parent=styles['Normal'],
                    fontSize=11,
                    textColor=COLOR_NAVY,
                    spaceAfter=6,
                    fontName='Helvetica-Bold',
                ),
            ))

            # Details grid
            details_text = f"""
            <b>Entry:</b> ₹{pred.limit_price:.2f} | <b>Target:</b> ₹{pred.target_low:.2f}–{pred.target_high:.2f} (↑{upside_pct}%) |
            <b>Stop:</b> ₹{stop:.2f} | <b>R:R:</b> {rr:0.1f} | <b>Qty:</b> {qty} | <b>Capital:</b> ₹{alloc:,.0f}
            """
            story.append(Paragraph(
                details_text,
                ParagraphStyle(
                    'Details',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=COLOR_TEXT,
                    spaceAfter=6,
                    leftIndent=0,
                ),
            ))

            # Reasoning
            story.append(Paragraph(
                pred.reasoning,
                ParagraphStyle(
                    'Reasoning',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=COLOR_TEXT_LIGHT,
                    spaceAfter=12,
                    leftIndent=0,
                ),
            ))

        story.append(Spacer(1, 0.2 * inch))
        story.append(PageBreak())

    # ─── All Signals Table ────────────────────────────────────────────
    story.append(Paragraph(
        "All Signals",
        ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=COLOR_NAVY,
            spaceAfter=10,
            fontName='Helvetica-Bold',
        ),
    ))

    sorted_preds = sorted(predictions, key=lambda p: p.confidence, reverse=True)

    table_data = [["Ticker", "Signal", "Conf%", "Current", "Entry", "Target", "Direction"]]

    for pred in sorted_preds:
        signal_text = pred.signal.upper()
        signal_color = COLOR_BUY if pred.signal == "bullish" else COLOR_SELL if pred.signal == "bearish" else COLOR_TEXT_LIGHT

        table_data.append([
            pred.ticker,
            signal_text,
            str(pred.confidence),
            f"₹{pred.current_price:.0f}",
            f"₹{pred.limit_price:.0f}",
            f"₹{pred.target_high:.0f}",
            pred.predicted_direction.upper(),
        ])

    table = Table(table_data, colWidths=[0.85*inch, 0.9*inch, 0.7*inch, 0.85*inch, 0.85*inch, 0.85*inch, 0.7*inch])

    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_BG]),
    ]

    table.setStyle(TableStyle(style_commands))
    story.append(table)

    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())

    # ─── Bearish Watch List ──────────────────────────────────────────
    if bearish:
        story.append(Paragraph(
            "Stocks to Avoid — Bearish Signals",
            ParagraphStyle(
                'SectionHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=COLOR_NAVY,
                spaceAfter=10,
                fontName='Helvetica-Bold',
            ),
        ))

        watch_data = [["Ticker", "Confidence", "Target Low", "Downside%", "Reason"]]

        for pred in bearish:
            downside_pct = round(((pred.target_low - pred.current_price) / pred.current_price * 100), 1)
            reason_short = pred.reasoning[:60] + "…" if len(pred.reasoning) > 60 else pred.reasoning

            watch_data.append([
                pred.ticker,
                f"{pred.confidence}%",
                f"₹{pred.target_low:.0f}",
                f"{downside_pct}%",
                reason_short,
            ])

        watch_table = Table(watch_data, colWidths=[0.85*inch, 1.0*inch, 1.0*inch, 0.85*inch, 2.1*inch])
        watch_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXT),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_BG]),
        ]))
        story.append(watch_table)

        story.append(Spacer(1, 0.3 * inch))

    story.append(PageBreak())

    # ─── Disclaimer ───────────────────────────────────────────────────
    story.append(Paragraph(
        "Important Disclaimer",
        ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=COLOR_NAVY,
            spaceAfter=8,
            fontName='Helvetica-Bold',
        ),
    ))

    disclaimer_text = """
    This report contains AI-generated market signals based on historical data and technical analysis.
    These signals are not financial advice and should not be considered as a recommendation to buy or sell securities.
    Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
    Past performance does not guarantee future results. Stock market investments carry risk, including potential loss of capital.
    """

    story.append(Paragraph(
        disclaimer_text,
        ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=COLOR_TEXT_LIGHT,
            alignment=4,  # justify
        ),
    ))

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()
