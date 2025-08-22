from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, 
    QFrame, QHBoxLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize
from db_manager import DatabaseManager
from utils import format_money

class DashboardPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        
        self.build_ui()

    def build_ui(self):
        self.setStyleSheet("""
            #mainFrame { background-color: #ecf0f1; }
            QLabel#groupTitle {
                font-size: 14px; font-weight: bold; color: #34495e;
                margin-bottom: 8px; margin-top: 10px;
            }
        """)

        title_label = QLabel("داشبورد مدیریتی")
        title_label.setFont(QFont("B Yekan", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        self.main_layout.addWidget(title_label)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(18)

        # --- بخش ۱: وضعیت مالی ---
        grid_layout.addWidget(QLabel("وضعیت مالی", objectName="groupTitle"), 0, 0, 1, 3)
        self.total_balance_label = self.create_stat_card("موجودی کل صندوق‌ها", "0", "#16a085", "account_balance_wallet")
        self.total_loan_principal_label = self.create_stat_card("کل سرمایه در گردش", "0", "#2980b9", "trending_up")
        self.total_receivables_label = self.create_stat_card("مجموع مطالبات باقی‌مانده", "0", "#c0392b", "assignment_turned_in")
        
        grid_layout.addWidget(self.total_balance_label, 1, 0)
        grid_layout.addWidget(self.total_loan_principal_label, 1, 1)
        grid_layout.addWidget(self.total_receivables_label, 1, 2)

        # --- بخش ۲: آمار سودآوری (با سه کارت جدید) ---
        grid_layout.addWidget(QLabel("آمار سودآوری", objectName="groupTitle"), 2, 0, 1, 3)
        self.projected_profit_label = self.create_stat_card("کل سود پیش‌بینی شده", "0", "#8e44ad", "timeline")
        self.realized_profit_label = self.create_stat_card("سود تحقق یافته", "0", "#27ae60", "monetization_on")
        self.unrealized_profit_label = self.create_stat_card("سود باقی‌مانده", "0", "#f39c12", "hourglass_bottom")
        
        grid_layout.addWidget(self.projected_profit_label, 3, 0)
        grid_layout.addWidget(self.realized_profit_label, 3, 1)
        grid_layout.addWidget(self.unrealized_profit_label, 3, 2)

        # --- بخش ۳: آمار کلی ---
        grid_layout.addWidget(QLabel("آمار کلی سیستم", objectName="groupTitle"), 4, 0, 1, 3)
        self.active_loans_label = self.create_stat_card("وام‌های فعال", "0", "#7f8c8d", "hourglass_top")
        self.settled_loans_label = self.create_stat_card("وام‌های تسویه شده", "0", "#2ecc71", "check_circle")
        self.total_customers_label = self.create_stat_card("تعداد کل مشتریان", "0", "#3498db", "people")
        
        grid_layout.addWidget(self.active_loans_label, 5, 0)
        grid_layout.addWidget(self.settled_loans_label, 5, 1)
        grid_layout.addWidget(self.total_customers_label, 5, 2)

        self.main_layout.addLayout(grid_layout)
        self.main_layout.addStretch()

    def create_stat_card(self, title, value, color, icon_name):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 15, 10)
        card_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(QSize(32, 32)))
        icon_label.setStyleSheet("background: transparent;")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignVCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("B Yekan", 10))
        title_label.setStyleSheet("color: #6c757d;")
        
        value_label = QLabel(value)
        value_label.setObjectName("valueLabel")
        value_label.setFont(QFont("B Yekan", 15, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")

        text_layout.addWidget(title_label)
        text_layout.addWidget(value_label)
        
        card_layout.addLayout(text_layout)
        card_layout.addWidget(icon_label, alignment=Qt.AlignRight)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        
        return card

    def refresh_data(self):
        stats = self.db_manager.get_dashboard_stats()
        if stats:
            self.total_balance_label.findChild(QLabel, "valueLabel").setText(format_money(stats['total_balance']))
            self.total_loan_principal_label.findChild(QLabel, "valueLabel").setText(format_money(stats['total_loan_principal']))
            self.total_receivables_label.findChild(QLabel, "valueLabel").setText(format_money(stats['total_receivables']))
            
            # به‌روزرسانی کارت‌های جدید سود
            self.projected_profit_label.findChild(QLabel, "valueLabel").setText(format_money(stats['total_projected_profit']))
            self.realized_profit_label.findChild(QLabel, "valueLabel").setText(format_money(stats['realized_profit']))
            self.unrealized_profit_label.findChild(QLabel, "valueLabel").setText(format_money(stats['unrealized_profit']))

            self.active_loans_label.findChild(QLabel, "valueLabel").setText(f"{stats['active_loans']} وام")
            self.settled_loans_label.findChild(QLabel, "valueLabel").setText(f"{stats['settled_loans']} وام")
            self.total_customers_label.findChild(QLabel, "valueLabel").setText(f"{stats['total_customers']} نفر")