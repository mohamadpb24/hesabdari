import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget, 
    QDesktopWidget, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtCore import Qt, QSize

# --- ایمپورت پنل‌ها ---
from dashboard_panel import DashboardPanel
from customer_panel import CustomerPanel
from loan_panel import LoanPanel
from installment_panel import InstallmentPanel
from cashbox_panel import CashboxPanel
from expense_panel import ExpensePanel
from reporting_panel import ReportingPanel
from manual_transaction_panel import ManualTransactionPanel
# --- ایمپورت پنل جدید ---
from arrears_panel import ArrearsPanel 

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("سیستم مدیریت صندوق و وام پژواک")
        self.resize(1200, 800)
        self.center()
        
        # تنظیم جهت برنامه به راست‌چین (RTL) برای فارسی
        self.setLayoutDirection(Qt.RightToLeft)
        
        # استایل کلی برنامه
        self.setStyleSheet("""
            QMainWindow { background-color: #f4f6f9; }
            QWidget { font-family: "B Yekan", "Tahoma", sans-serif; }
            
            /* استایل منوی سمت راست */
            QFrame#Sidebar {
                background-color: #2c3e50;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }
            
            /* استایل دکمه‌های منو */
            QPushButton.SidebarBtn {
                background-color: transparent;
                color: #ecf0f1;
                text-align: right;
                padding: 12px 20px;
                border: none;
                font-size: 14px;
                border-radius: 10px;
                margin: 2px 10px;
            }
            QPushButton.SidebarBtn:hover {
                background-color: #34495e;
            }
            QPushButton.SidebarBtn:checked {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
        """)

        # ویجت اصلی
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ساخت منوی سمت راست و پنل محتوا
        self.init_ui()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        # 1. منوی سمت راست (Sidebar)
        self.sidebar = self.setup_sidebar()
        self.main_layout.addWidget(self.sidebar)

        # 2. پنل محتوا (Content Area)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        
        # استفاده از StackedWidget برای نمایش پنل‌ها
        self.stack = QStackedWidget()
        
        # --- ایجاد و افزودن پنل‌ها به استک ---
        self.dashboard_panel = DashboardPanel()
        self.customer_panel = CustomerPanel()
        self.loan_panel = LoanPanel()
        self.installment_panel = InstallmentPanel()
        self.cashbox_panel = CashboxPanel()
        self.expense_panel = ExpensePanel()
        self.reporting_panel = ReportingPanel()
        
        # پنل‌های تراکنش دستی (اختیاری، اگر دکمه جدا دارد)
        # self.manual_trans_panel = ManualTransactionPanel() 
        
        # --- افزودن پنل جدید معوقات ---
        self.arrears_panel = ArrearsPanel()
        
        # ترتیب افزودن به استک مهم است (برای ایندکس‌دهی)
        self.stack.addWidget(self.dashboard_panel)    # index 0
        self.stack.addWidget(self.customer_panel)     # index 1
        self.stack.addWidget(self.loan_panel)         # index 2
        self.stack.addWidget(self.installment_panel)  # index 3
        self.stack.addWidget(self.cashbox_panel)      # index 4
        self.stack.addWidget(self.expense_panel)      # index 5
        self.stack.addWidget(self.reporting_panel)    # index 6
        self.stack.addWidget(self.arrears_panel)      # index 7 (پنل جدید)

        self.content_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.content_area)
        
        # تنظیم پیش‌فرض روی داشبورد
        self.switch_panel(self.dashboard_panel, self.btn_dashboard)

    def setup_sidebar(self):
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("Sidebar")
        sidebar_frame.setFixedWidth(240)
        
        # سایه برای زیبایی
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(5, 0)
        sidebar_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(sidebar_frame)
        layout.setContentsMargins(0, 30, 0, 20)
        layout.setSpacing(10)

        # عنوان یا لوگوی بالای منو
        app_title = QLabel("حسابداری پژواک")
        app_title.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        app_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(app_title)

        # --- تعریف دکمه‌ها ---
        self.btn_dashboard = self.create_sidebar_btn("داشبورد", "icons/dashboard.png")
        self.btn_customers = self.create_sidebar_btn("مدیریت مشتریان", "icons/users.png")
        self.btn_loans = self.create_sidebar_btn("مدیریت وام‌ها", "icons/loan.png")
        self.btn_installments = self.create_sidebar_btn("مدیریت اقساط", "icons/installment.png")
        self.btn_cashbox = self.create_sidebar_btn("صندوق و تراکنش", "icons/cashbox.png")
        self.btn_expenses = self.create_sidebar_btn("هزینه‌ها", "icons/expense.png")
        self.btn_reports = self.create_sidebar_btn("گزارشات", "icons/report.png")
        
        # --- دکمه جدید ---
        self.btn_arrears = self.create_sidebar_btn("گزارش معوقات", "icons/warning.png") # آیکون هشدار برای معوقات
        
        self.btn_exit = self.create_sidebar_btn("خروج", "icons/exit.png")
        self.btn_exit.setStyleSheet("""
            QPushButton.SidebarBtn { color: #e74c3c; }
            QPushButton.SidebarBtn:hover { background-color: #c0392b; color: white; }
        """)

        # --- اتصال عملکرد دکمه‌ها ---
        self.btn_dashboard.clicked.connect(lambda: self.switch_panel(self.dashboard_panel, self.btn_dashboard))
        self.btn_customers.clicked.connect(lambda: self.switch_panel(self.customer_panel, self.btn_customers))
        self.btn_loans.clicked.connect(lambda: self.switch_panel(self.loan_panel, self.btn_loans))
        self.btn_installments.clicked.connect(lambda: self.switch_panel(self.installment_panel, self.btn_installments))
        self.btn_cashbox.clicked.connect(lambda: self.switch_panel(self.cashbox_panel, self.btn_cashbox))
        self.btn_expenses.clicked.connect(lambda: self.switch_panel(self.expense_panel, self.btn_expenses))
        self.btn_reports.clicked.connect(lambda: self.switch_panel(self.reporting_panel, self.btn_reports))
        
        # اتصال دکمه جدید به پنل معوقات
        self.btn_arrears.clicked.connect(lambda: self.switch_panel(self.arrears_panel, self.btn_arrears))
        
        self.btn_exit.clicked.connect(self.close)

        # افزودن به لی‌اوت
        layout.addWidget(self.btn_dashboard)
        layout.addWidget(self.btn_customers)
        layout.addWidget(self.btn_loans)
        layout.addWidget(self.btn_installments)
        layout.addWidget(self.btn_cashbox)
        layout.addWidget(self.btn_expenses)
        layout.addWidget(self.btn_reports)
        
        # افزودن دکمه جدید به لیست
        layout.addWidget(self.btn_arrears)
        
        layout.addStretch() # فاصله انداز
        layout.addWidget(self.btn_exit)

        return sidebar_frame

    def create_sidebar_btn(self, text, icon_path):
        btn = QPushButton(text)
        btn.setProperty("class", "SidebarBtn") # برای شناسایی در CSS
        # اگر آیکون دارید، خط زیر را فعال کنید. فعلا کامنت شده تا ارور ندهد
        # btn.setIcon(QIcon(icon_path))
        # btn.setIconSize(QSize(24, 24))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setCheckable(True)
        return btn

    def switch_panel(self, panel_widget, active_btn):
        # 1. تغییر پنل در استک
        self.stack.setCurrentWidget(panel_widget)
        
        # 2. مدیریت وضعیت ظاهری دکمه‌ها (فقط دکمه فعال رنگی باشد)
        buttons = [
            self.btn_dashboard, self.btn_customers, self.btn_loans,
            self.btn_installments, self.btn_cashbox, self.btn_expenses,
            self.btn_reports, self.btn_arrears
        ]
        
        for btn in buttons:
            btn.setChecked(False)
        
        active_btn.setChecked(True)
        
        # 3. رفرش کردن اطلاعات پنل (اگر متد refresh_data داشته باشد)
        if hasattr(panel_widget, 'refresh_data'):
            try:
                panel_widget.refresh_data()
            except Exception as e:
                print(f"Error refreshing data: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # تنظیم فونت کلی برنامه
    font = QFont("B Yekan", 10)
    app.setFont(font)
    
    window = MainApp()
    window.show()
    sys.exit(app.exec_())