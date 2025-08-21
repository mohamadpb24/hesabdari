import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QMessageBox, QStackedWidget
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Import all panels
from customer_panel import CustomerPanel
from cashbox_panel import CashboxPanel
from loan_panel import LoanPanel
from installment_panel import InstallmentPanel
from transaction_panel import TransactionPanel
from dashboard_panel import DashboardPanel

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("سیستم حسابداری فروش اقساطی")
        self.setGeometry(100, 100, 1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(250)
        self.sidebar_widget.setStyleSheet("""
            background-color: #34495e;
            color: white;
            border-radius: 10px;
        """)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setSpacing(20)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        
        app_title = QLabel("حسابداری اقساطی")
        app_title.setFont(QFont("B Yekan", 16, QFont.Bold))
        app_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(app_title)
        self.sidebar_layout.addSpacing(30)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #ecf0f1; border-radius: 10px;")
        
        self.dashboard_panel = DashboardPanel()
        self.customer_panel = CustomerPanel()
        self.cashbox_panel = CashboxPanel()
        self.loan_panel = LoanPanel()
        self.installment_panel = InstallmentPanel()
        self.transaction_panel = TransactionPanel()
        
        self.panels = {
            "dashboard": self.dashboard_panel,
            "customers": self.customer_panel,
            "cashboxes": self.cashbox_panel,
            "loans": self.loan_panel,
            "installments": self.installment_panel,
            "transactions": self.transaction_panel
        }
        
        self.stacked_widget.addWidget(self.panels["dashboard"])
        self.stacked_widget.addWidget(self.panels["customers"])
        self.stacked_widget.addWidget(self.panels["cashboxes"])
        self.stacked_widget.addWidget(self.panels["loans"])
        self.stacked_widget.addWidget(self.panels["installments"])
        self.stacked_widget.addWidget(self.panels["transactions"])
        
        self.main_layout.addWidget(self.sidebar_widget)
        self.main_layout.addWidget(self.stacked_widget)
        
        self.add_sidebar_buttons()
        self.stacked_widget.setCurrentIndex(0)

    def add_sidebar_buttons(self):
        buttons_info = [
            ("داشبورد", "dashboard"),
            ("مشتریان", "customers"),
            ("صندوق‌ها", "cashboxes"),
            ("پرداخت وام", "loans"),
            ("پرداخت اقساط", "installments"),
            ("تراکنش‌ها", "transactions"),
        ]
        
        for text, panel_name in buttons_info:
            btn = self.create_button(text)
            self.sidebar_layout.addWidget(btn)
            btn.clicked.connect(lambda _, name=panel_name: self.switch_panel(self.panels[name]))

    def create_button(self, text):
        btn = QPushButton(text)
        btn.setMinimumHeight(50)
        btn.setFont(QFont("B Yekan", 12))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 10px;
                text-align: right;
            }
            QPushButton:hover {
                background-color: #2c3e50;
                border-left: 5px solid #2980b9;
            }
        """)
        return btn

    def switch_panel(self, panel):
        self.stacked_widget.setCurrentWidget(panel)
        if hasattr(panel, 'refresh_data'):
            panel.refresh_data()

# Entry point of the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("B Yekan", 10))
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())