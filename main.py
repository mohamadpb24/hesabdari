# main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from customer_panel import CustomerPanel
from cashbox_panel import CashboxPanel
from loan_panel import LoanPanel
from installment_panel import InstallmentPanel
from transaction_panel import TransactionPanel
from dashboard_panel import DashboardPanel
from expense_panel import ExpensePanel
from reporting_panel import ReportingPanel
from manual_transaction_panel import ManualTransactionPanel
from db_manager import DatabaseManager

LIGHT_THEME_STYLESHEET = """
QWidget {
    background-color: #f0f2f5; /* پس‌زمینه اصلی برنامه */
    color: #2c3e50; /* رنگ متن اصلی */
    font-family: "B Yekan";
    font-size: 10pt;
}
QFrame {
    background-color: #ffffff; /* پس‌زمینه فریم‌ها و کارت‌ها */
    border-radius: 12px;
}
QLabel {
    background-color: transparent;
    font-size: 11pt;
    color: #34495e; /* رنگ متن لیبل‌ها */
}
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox {
    background-color: #ffffff;
    color: #2c3e50;
    border: 1px solid #dfe6e9;
    border-radius: 8px;
    padding: 10px;
    font-size: 10pt;
}
QComboBox::drop-down {
    border: none;
}
QPushButton {
    background-color: #3b82f6;
    color: white;
    border-radius: 8px;
    padding: 10px 15px;
    font-size: 11pt;
    font-weight: bold;
    border: none;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:disabled {
    background-color: #bdc3c7;
    color: #7f8c8d;
}
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #dfe6e9;
    border-radius: 8px;
    gridline-color: #dfe6e9;
    color: #34495e;
}
QHeaderView::section {
    background-color: #f8f9fa;
    color: #34495e;
    padding: 8px;
    border: none;
    font-weight: bold;
}
QDialog {
    background-color: #f0f2f5;
}
QScrollArea {
    border: none;
    background-color: #f0f2f5;
}
"""

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            QMessageBox.critical(self, "خطای اتصال", f"برنامه قادر به اتصال به پایگاه داده نیست.\nخطا: {e}")
            sys.exit(1)

        self.setWindowTitle("سیستم حسابداری فروش اقساطی")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(250)
        self.sidebar_widget.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 10px;
        """)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setSpacing(10)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        
        app_title = QLabel("حسابداری اقساطی")
        app_title.setFont(QFont("B Yekan", 16, QFont.Bold))
        app_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(app_title)
        self.sidebar_layout.addSpacing(20)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #f0f2f5; border-radius: 10px;")
        
        # ساخت نمونه از تمام پنل‌ها
        self.dashboard_panel = DashboardPanel()
        self.customer_panel = CustomerPanel()
        self.cashbox_panel = CashboxPanel()
        self.loan_panel = LoanPanel()
        self.installment_panel = InstallmentPanel()
        self.manual_transaction_panel = ManualTransactionPanel()
        self.expense_panel = ExpensePanel()
        self.reporting_panel = ReportingPanel()
        self.transaction_panel = TransactionPanel()

        self.panels = {
            "dashboard": self.dashboard_panel,
            "customers": self.customer_panel,
            "cashboxes": self.cashbox_panel,
            "loans": self.loan_panel,
            "installments": self.installment_panel,
            "manual_transactions": self.manual_transaction_panel,
            "expenses": self.expense_panel,
            "reporting": self.reporting_panel,
            "transactions": self.transaction_panel,
        }
        
        for panel in self.panels.values():
            self.stacked_widget.addWidget(panel)
        
        self.main_layout.addWidget(self.sidebar_widget)
        self.main_layout.addWidget(self.stacked_widget)
        
        self.add_sidebar_buttons()
        self.stacked_widget.setCurrentWidget(self.panels["dashboard"])

    def add_sidebar_buttons(self):
        for text, panel_name in self.get_buttons_info():
            btn = self.create_button(text)
            self.sidebar_layout.addWidget(btn)
            btn.clicked.connect(lambda _, name=panel_name: self.switch_panel(self.panels[name]))
        
        self.sidebar_layout.addStretch()

    def create_button(self, text):
        btn = QPushButton(text)
        btn.setMinimumHeight(45)
        btn.setFont(QFont("B Yekan", 12))
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4b5569;
                border: none;
                padding: 10px;
                padding-right: 20px;
                text-align: right;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: white;
            }
        """)
        btn.setCheckable(True)
        return btn

    def switch_panel(self, panel):
        for i in range(self.sidebar_layout.count()):
            widget = self.sidebar_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                panel_name = next((name for name, p in self.panels.items() if p == panel), None)
                button_text = next((text for text, name in self.get_buttons_info() if name == panel_name), None)
                widget.setChecked(widget.text() == button_text)

        self.stacked_widget.setCurrentWidget(panel)
        if hasattr(panel, 'refresh_data'):
            panel.refresh_data()
    
    def get_buttons_info(self):
        return [
            ("داشبورد", "dashboard"),
            ("مشتریان", "customers"),
            ("صندوق‌ها", "cashboxes"),
            ("پرداخت وام", "loans"),
            ("پرداخت اقساط", "installments"),
            ("ایجاد تراکنش دستی", "manual_transactions"),
            ("هزینه‌ها", "expenses"),
            ("گزارش‌گیری", "reporting"),
            ("لیست کل تراکنش‌ها", "transactions"),
        ]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_THEME_STYLESHEET)
    app.setFont(QFont("B Yekan", 10))
    main_window = MainApp()
    main_window.showMaximized()
    
    main_window.switch_panel(main_window.panels["dashboard"])
    
    sys.exit(app.exec_())
