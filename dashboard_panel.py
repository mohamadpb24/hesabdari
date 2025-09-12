# dashboard_panel.py (نسخه نهایی و اصلاح شده)
import jdatetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, 
    QFrame, QHBoxLayout, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtSvg import QSvgRenderer

from db_manager import DatabaseManager
from utils import format_money

# --- SVG Icons (این بخش بدون تغییر باقی می‌ماند) ---
SVG_ICONS = {
    "balance": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/></svg>""",
    "loan_principal": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>""",
    "receivables": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7 11 2-2-2-2"/><path d="M11 13h4"/><path d="m17 11 2-2-2-2"/><circle cx="12" cy="12" r="10"/></svg>""",
    "expenses": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8c-2.2 0-4 1.8-4 4s1.8 4 4 4 4-1.8 4-4-1.8-4-4-4Z"/><path d="M21 12h-2a9 9 0 0 0-6.8-8.8V2"/><path d="M3 12h2a9 9 0 0 1 6.8 8.8V22"/><path d="M12 3v2a9 9 0 0 1 8.8 6.8H22"/><path d="M12 21v-2a9 9 0 0 0-8.8-6.8H2"/></svg>""",
    "total_profit": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12s2.545-5 7-5c4.454 0 7 5 7 5s-2.546 5-7 5c-4.455 0-7-5-7-5z"/><path d="M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/></svg>""",
    "realized_profit": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>""",
    "projected_profit": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>""",
    "active_loans": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m7.8 16.2-2.9 2.9"/><path d="M6 12H2"/><path d="m7.8 7.8-2.9-2.9"/><circle cx="12" cy="12" r="4"/></svg>""",
    "settled_loans": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m9 12 2 2 4-4"/></svg>""",
    "customers": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>""",
}

class StatCard(QFrame):
    # ... (این کلاس بدون تغییر باقی می‌ماند)
    def __init__(self, title, icon_svg, gradient_colors):
        super().__init__()
        self.gradient_colors = gradient_colors
        self.icon_svg = icon_svg
        self.title = title
        
        self.setGraphicsEffect(self.create_shadow())
        self.init_ui()

    def create_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        return shadow

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        svg_renderer = QSvgRenderer(self.icon_svg.encode('utf-8'))
        pixmap = QPixmap(QSize(24, 24))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        svg_renderer.render(painter)
        painter.end()
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setAlignment(Qt.AlignCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_label = QLabel(self.title)
        title_label.setFont(QFont("B Yekan", 10))
        title_label.setStyleSheet("color: rgba(229, 231, 235, 0.8); background: transparent;")
        
        self.value_label = QLabel("...")
        self.value_label.setObjectName("valueLabel")
        self.value_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        self.value_label.setStyleSheet("color: white; background: transparent;")

        text_layout.addWidget(self.value_label)
        text_layout.addWidget(title_label)
        
        main_layout.addWidget(self.icon_label)
        main_layout.addLayout(text_layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(self.gradient_colors[0]))
        gradient.setColorAt(1, QColor(self.gradient_colors[1]))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

    def set_value(self, text):
        self.value_label.setText(text)


class DashboardPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.cards = {}
        self.build_ui()

    def build_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #111827; }")
        self.main_layout.addWidget(scroll_area)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 20, 25, 20)
        container_layout.setSpacing(20)
        scroll_area.setWidget(container)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("داشبورد مدیریتی")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setStyleSheet("color: #e5e7eb;")
        
        today = jdatetime.date.today()
        date_label = QLabel(today.strftime("%A, %d %B %Y"))
        date_label.setFont(QFont("B Yekan", 11))
        date_label.setStyleSheet("color: #9ca3af;")
        date_label.setAlignment(Qt.AlignRight)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(date_label)
        container_layout.addLayout(header_layout)

        # Grid Layout for Cards
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        container_layout.addLayout(grid_layout)
        container_layout.addStretch()

        card_definitions = [
            {"key": "total_balance", "title": "موجودی کل صندوق‌ها", "icon": "balance", "colors": ["#10b981", "#059669"]},
            {"key": "total_loan_principal", "title": "کل سرمایه در گردش", "icon": "loan_principal", "colors": ["#3b82f6", "#2563eb"]},
            {"key": "total_receivables", "title": "مجموع مطالبات", "icon": "receivables", "colors": ["#f97316", "#ea580c"]},
            {"key": "total_expenses", "title": "مجموع هزینه‌ها", "icon": "expenses", "colors": ["#ef4444", "#dc2626"]},
            {"key": "total_projected_profit", "title": "کل سود", "icon": "total_profit", "colors": ["#8b5cf6", "#7c3aed"]},
            {"key": "realized_profit", "title": "سود تحقق یافته", "icon": "realized_profit", "colors": ["#14b8a6", "#0d9488"]},
            {"key": "unrealized_profit", "title": "سود پیش‌بینی شده", "icon": "projected_profit", "colors": ["#d946ef", "#c026d3"]},
            {"key": "active_loans", "title": "وام‌های فعال", "icon": "active_loans", "colors": ["#64748b", "#475569"]},
            {"key": "settled_loans", "title": "وام‌های تسویه شده", "icon": "settled_loans", "colors": ["#22c55e", "#16a34a"]},
            {"key": "total_customers", "title": "تعداد کل مشتریان", "icon": "customers", "colors": ["#0ea5e9", "#0284c7"]},
        ]

        row, col = 0, 0
        for definition in card_definitions:
            card = StatCard(definition["title"], SVG_ICONS[definition["icon"]], definition["colors"])
            self.cards[definition["key"]] = card
            grid_layout.addWidget(card, row, col)
            
            col += 1
            if col > 1:
                col = 0
                row += 1

    def refresh_data(self):
        stats = self.db_manager.get_dashboard_stats()
        if stats:
            self.cards["total_balance"].set_value(format_money(stats['total_balance']))
            self.cards["total_loan_principal"].set_value(format_money(stats['total_loan_principal']))
            self.cards["total_receivables"].set_value(format_money(stats['total_receivables']))
            self.cards["total_expenses"].set_value(format_money(stats.get('total_expenses', 0)))
            self.cards["total_projected_profit"].set_value(format_money(stats['total_projected_profit']))
            self.cards["realized_profit"].set_value(format_money(stats['realized_profit']))
            self.cards["unrealized_profit"].set_value(format_money(stats['unrealized_profit']))
            self.cards["active_loans"].set_value(f"{stats['active_loans']} وام")
            self.cards["settled_loans"].set_value(f"{stats['settled_loans']} وام")
            # --- اصلاح شد: استفاده از کلید 'total_customers' ---
            self.cards["total_customers"].set_value(f"{stats['total_customers']} نفر")