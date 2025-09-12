# cashbox_panel.py (نسخه نهایی با پس‌زمینه سفید برای گردش حساب)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QDoubleSpinBox,
    QScrollArea, QFrame, QGridLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QBrush, QLinearGradient
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPixmap
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

# کلاس‌های سفارشی برای مرتب‌سازی صحیح در جدول
class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # این تابع برای مرتب‌سازی عددی در جدول استفاده می‌شود
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except (ValueError, TypeError):
            return super().__lt__(other)

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # این تابع برای مرتب‌سازی تاریخ در جدول استفاده می‌شود
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)

# کلاس کارت گرافیکی برای هر صندوق
class CashboxCard(QFrame):
    def __init__(self, fund_data, parent_panel):
        super().__init__()
        self.fund_data = fund_data
        self.parent_panel = parent_panel
        self.setGraphicsEffect(self.create_shadow())
        self.init_ui()

    def create_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        return shadow

    def init_ui(self):
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 20px;
                border: 1px solid rgba(200, 200, 200, 0.5);
            }
            QLabel { background: transparent; border: none; }
            QPushButton {
                background-color: rgba(0, 0, 0, 0.05); border: none;
                border-radius: 10px; padding: 8px 15px;
                font-family: "B Yekan"; font-size: 10pt; color: #2c3e50;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.1); }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(10)

        name_label = QLabel(self.fund_data[1])
        name_label.setFont(QFont("B Yekan", 14, QFont.Bold))
        name_label.setStyleSheet("color: #2c3e50;")

        balance_label = QLabel(format_money(self.fund_data[2]))
        balance_label.setFont(QFont("B Yekan", 24, QFont.Bold))
        balance_label.setStyleSheet("color: #34495e;")
        balance_label.setAlignment(Qt.AlignCenter)
        
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        
        transactions_btn = QPushButton("مشاهده تراکنش‌ها")
        transactions_btn.clicked.connect(lambda: self.parent_panel.show_transactions_dialog(self.fund_data))
        
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(lambda: self.parent_panel.show_fund_form(self.fund_data))

        footer_layout.addWidget(transactions_btn)
        footer_layout.addWidget(edit_btn)

        main_layout.addWidget(name_label)
        main_layout.addStretch()
        main_layout.addWidget(balance_label)
        main_layout.addStretch()
        main_layout.addLayout(footer_layout)

# پنل اصلی صندوق‌ها
class CashboxPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: transparent;")
        self.build_ui()

    def build_ui(self):
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #e0eafc, stop:1 #cfdef3);
                border-radius: 15px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 20, 25, 20)

        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت صندوق‌ها")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        add_btn = QPushButton("افزودن صندوق جدید")
        add_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 12px 20px; border-radius: 10px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        add_btn.clicked.connect(lambda: self.show_fund_form())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(25)
        scroll_area.setWidget(self.cards_container)
        
        container_layout.addLayout(header_layout)
        container_layout.addWidget(scroll_area)
        
        self.main_layout.addWidget(container)
        self.refresh_data()
        
    def refresh_data(self):
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        funds = self.db_manager.get_all_cash_boxes()
        row, col = 0, 0
        if funds:
            for fund in funds:
                card = CashboxCard(fund, self)
                self.cards_layout.addWidget(card, row, col)
                col += 1
                if col > 2: col = 0; row += 1
        self.cards_layout.setRowStretch(row + 1, 1)

    def show_fund_form(self, fund_data=None):
        is_edit = fund_data is not None
        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش صندوق" if is_edit else "افزودن صندوق جدید")
        form_layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        balance_input = QDoubleSpinBox()
        balance_input.setRange(-1e12, 1e12)
        balance_input.setGroupSeparatorShown(True)

        if is_edit:
            fund_id, name, balance = fund_data
            name_input.setText(name)
            balance_input.setValue(balance)

        form_layout.addRow("نام صندوق:", name_input)
        form_layout.addRow("موجودی (تومان):", balance_input)
        
        save_btn = QPushButton("ثبت تغییرات" if is_edit else "ثبت صندوق")
        
        def on_save():
            name = name_input.text()
            balance = balance_input.value()
            if not name:
                QMessageBox.warning(dialog, "خطا", "نام صندوق نمی‌تواند خالی باشد.")
                return

            if is_edit:
                success = self.db_manager.update_fund(fund_id, name, balance)
            else:
                success = self.db_manager.add_fund(name, balance)

            if success:
                QMessageBox.information(self, "موفقیت", "عملیات با موفقیت انجام شد.")
                dialog.accept()
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطا", "خطا در ثبت اطلاعات.")

        save_btn.clicked.connect(on_save)
        form_layout.addRow(save_btn)
        dialog.exec_()
    
    def show_transactions_dialog(self, fund_data):
        fund_id, fund_name, _ = fund_data
        dialog = QDialog(self)
        dialog.setWindowTitle(f"گردش حساب صندوق: {fund_name}")
        dialog.setMinimumSize(800, 600)
        
        dialog.setStyleSheet("QDialog { background-color: #ffffff; }")
        
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["تاریخ", "نوع تراکنش", "مبلغ", "طرف حساب", "شرح"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        transactions = self.db_manager.get_fund_transactions(fund_id)
        if transactions:
            table.setRowCount(len(transactions))
            
            # --- شروع اصلاحات کلیدی ---
            # ۱. دیکشنری برای ترجمه نوع تراکنش
            type_map = {
                'LoanPayment': 'پرداخت وام',
                'InstallmentPayment': 'دریافت قسط',
                'ManualPayment': 'پرداخت دستی',
                'ManualReceipt': 'دریافت دستی',
                'transfer': 'صندوق به صندوق',
                'Expense': 'هزینه',
                'CapitalInjection': 'افزایش سرمایه',
                'Settlement': 'تسویه کامل وام'
            }
            # --- پایان اصلاحات کلیدی ---

            for row, trans in enumerate(transactions):
                amount_item = QTableWidgetItem(format_money(trans['Amount']))
                if trans['Flow'] == 'ورودی':
                    amount_item.setForeground(QColor("#27ae60"))
                else:
                    amount_item.setForeground(QColor("#c0392b"))
                
                # --- اصلاح شد: استفاده از دیکشنری برای نمایش نام فارسی ---
                persian_type = type_map.get(trans['Type'], trans['Type'])

                table.setItem(row, 0, QTableWidgetItem(str(trans['Date'])))
                table.setItem(row, 1, QTableWidgetItem(persian_type)) # <-- اینجا از نام فارسی استفاده می‌شود
                table.setItem(row, 2, amount_item)
                table.setItem(row, 3, QTableWidgetItem(trans.get('Counterparty', '')))
                table.setItem(row, 4, QTableWidgetItem(trans['Description']))
        
        layout.addWidget(table)
        dialog.exec_()













