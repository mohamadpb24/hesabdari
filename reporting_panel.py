# reporting_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QMessageBox, QFileDialog, QGroupBox, QSpacerItem, QSizePolicy,
    QGridLayout
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize
import jdatetime
from utils import format_money

from db_manager import DatabaseManager
import report_generator

class ReportingPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.build_ui()

    def build_ui(self):
        # --- Main Stylesheet ---
        self.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #dfe6e9;
                border-radius: 10px;
                padding: 15px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 15px;
                background-color: #0984e3;
                color: white;
                border-radius: 5px;
            }
            QLabel#card_description {
                color: #636e72;
                font-size: 10px;
                margin-bottom: 10px;
            }
            QPushButton {
                background-color: #00b894;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #00cec9;
            }
            QComboBox, QLineEdit {
                padding: 8px;
                border: 1px solid #b2bec3;
                border-radius: 5px;
            }
        """)

        # --- Main Title ---
        title_label = QLabel("مرکز گزارش‌گیری")
        title_label.setFont(QFont("B Yekan", 22, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2d3436; margin-bottom: 20px;")
        self.main_layout.addWidget(title_label)

        # --- Grid Layout for Report Cards ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(25)

        grid_layout.addWidget(self.create_customer_report_card(), 0, 0)
        grid_layout.addWidget(self.create_cashbox_report_card(), 0, 1)
        grid_layout.addWidget(self.create_installment_report_card(), 1, 0, 1, 2)

        self.main_layout.addLayout(grid_layout)
        self.main_layout.addStretch()

    def create_customer_report_card(self):
        box = QGroupBox("پرونده مالی مشتری")
        layout = QVBoxLayout(box)

        icon = QLabel()
        icon.setPixmap(QIcon.fromTheme("user-card").pixmap(QSize(48, 48)))
        icon.setAlignment(Qt.AlignCenter)
        
        desc = QLabel("گزارش کامل از وضعیت وام‌ها و اقساط یک مشتری خاص.", objectName="card_description")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.update_loan_combo)
        
        self.loan_combo = QComboBox()
        
        btn = QPushButton("دریافت پرونده مشتری")
        btn.clicked.connect(self.generate_customer_report)

        layout.addWidget(icon)
        layout.addWidget(desc)
        layout.addWidget(QLabel("۱. ابتدا مشتری را انتخاب کنید:"))
        layout.addWidget(self.customer_combo)
        layout.addWidget(QLabel("۲. سپس وام مورد نظر را انتخاب کنید:"))
        layout.addWidget(self.loan_combo)
        layout.addWidget(btn)
        return box

    def create_cashbox_report_card(self):
        box = QGroupBox("گردش حساب صندوق")
        layout = QVBoxLayout(box)
        
        icon = QLabel()
        icon.setPixmap(QIcon.fromTheme("cash-register").pixmap(QSize(48, 48)))
        icon.setAlignment(Qt.AlignCenter)

        desc = QLabel("گزارش دقیق از تمام واریزها و برداشت‌های یک صندوق.", objectName="card_description")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        self.cashbox_combo = QComboBox()
        btn = QPushButton("دریافت گزارش صندوق")
        btn.clicked.connect(self.generate_cashbox_report)
        
        layout.addWidget(icon)
        layout.addWidget(desc)
        layout.addWidget(self.cashbox_combo)
        layout.addWidget(btn)
        return box

    def create_installment_report_card(self):
        box = QGroupBox("گزارش جامع اقساط")
        layout = QGridLayout(box)

        desc = QLabel("اقساط را بر اساس بازه زمانی و وضعیت پرداخت فیلتر کرده و گزارش کامل دریافت کنید.", objectName="card_description")
        layout.addWidget(desc, 0, 0, 1, 4)

        layout.addWidget(QLabel("از تاریخ:"), 1, 0)
        self.start_date_input = QLineEdit(jdatetime.date(1400, 1, 1).strftime('%Y/%m/%d'))
        layout.addWidget(self.start_date_input, 1, 1)

        layout.addWidget(QLabel("تا تاریخ:"), 1, 2)
        self.end_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        layout.addWidget(self.end_date_input, 1, 3)

        layout.addWidget(QLabel("وضعیت پرداخت:"), 2, 0)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["همه وضعیت‌ها", "پرداخت شده", "پرداخت نشده", "پرداخت ناقص"])
        layout.addWidget(self.status_combo, 2, 1, 1, 3)

        btn = QPushButton("دریافت گزارش اقساط")
        btn.setIcon(QIcon.fromTheme("document-print"))
        btn.clicked.connect(self.generate_installment_report)
        layout.addWidget(btn, 3, 0, 1, 4)
        return box

    def refresh_data(self):
        self.load_customers_to_combo()
        self.load_cashboxes_to_combo()

    def update_loan_combo(self):
        self.loan_combo.clear()
        customer_data = self.customer_combo.currentData()
        
        if customer_data:
            customer_id = customer_data[0]
            loans = self.db_manager.get_customer_loans(customer_id)
            
            self.loan_combo.addItem("همه وام‌ها", "all")
            for loan_id, amount, term, date in loans:
                item_text = f"وام {loan_id}: {format_money(amount)} ({term} ماهه)"
                self.loan_combo.addItem(item_text, loan_id)
        else:
            self.loan_combo.addItem("ابتدا یک مشتری انتخاب کنید", None)
            
    def load_customers_to_combo(self):
        self.customer_combo.clear()
        customers = self.db_manager.get_all_customers_with_details()
        self.customer_combo.addItem("یک مشتری را انتخاب کنید...", None)
        for customer in customers:
            self.customer_combo.addItem(customer[1], customer)

    def load_cashboxes_to_combo(self):
        self.cashbox_combo.clear()
        cashboxes = self.db_manager.get_all_cash_boxes()
        self.cashbox_combo.addItem("یک صندوق را انتخاب کنید...", None)
        for box_id, name, balance in cashboxes:
            self.cashbox_combo.addItem(name, {'id': box_id, 'name': name, 'balance': balance})

    def generate_cashbox_report(self):
        cashbox_data = self.cashbox_combo.currentData()
        if not cashbox_data:
            QMessageBox.warning(self, "خطا", "لطفاً یک صندوق را انتخاب کنید.")
            return

        transactions = self.db_manager.get_transactions_by_cashbox(cashbox_data['id'])
        if not transactions:
            QMessageBox.information(self, "گزارش خالی", "هیچ تراکنشی برای این صندوق ثبت نشده است.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش صندوق", f"گزارش_{cashbox_data['name']}.pdf", "PDF Files (*.pdf)")
        if file_path:
            success = report_generator.create_cashbox_report(cashbox_data, transactions, file_path)
            if success:
                QMessageBox.information(self, "موفقیت", "گزارش با موفقیت ذخیره شد.")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")

    def generate_customer_report(self):
        customer_tuple = self.customer_combo.currentData()
        selected_loan_id = self.loan_combo.currentData()

        if not customer_tuple:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشتری را انتخاب کنید.")
            return
        
        all_customer_data = self.db_manager.get_customers_with_debt()
        customer_debt_info = next((c for c in all_customer_data if c['id'] == customer_tuple[0]), None)

        customer_data = {
            'id': customer_tuple[0], 'name': customer_tuple[1], 'national_code': customer_tuple[2],
            'phone_number': customer_tuple[3], 'address': customer_tuple[4],
            'total_debt': customer_debt_info['total_debt'] if customer_debt_info else 0
        }
        
        loans, installments_by_loan = self.db_manager.get_full_customer_report_data(customer_data['id'])
        if loans is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات از پایگاه داده.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره پرونده مشتری", f"پرونده_{customer_data['name']}.pdf", "PDF Files (*.pdf)")
        if file_path:
            success = report_generator.create_single_customer_report(customer_data, loans, installments_by_loan, file_path, selected_loan_id)
            if success:
                QMessageBox.information(self, "موفقیت", "پرونده مشتری با موفقیت ذخیره شد.")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")
                
    def generate_installment_report(self):
        start_date = self.start_date_input.text()
        end_date = self.end_date_input.text()
        status = self.status_combo.currentText()

        try:
            jdatetime.datetime.strptime(start_date, '%Y/%m/%d')
            jdatetime.datetime.strptime(end_date, '%Y/%m/%d')
        except ValueError:
            QMessageBox.warning(self, "خطا", "فرمت تاریخ صحیح نیست. لطفاً از فرمت YYYY/MM/DD استفاده کنید.")
            return

        installments = self.db_manager.get_installments_by_date_range(start_date, end_date, status)
        if not installments:
            QMessageBox.information(self, "گزارش خالی", "هیچ قسطی با این فیلترها یافت نشد.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش اقساط", "گزارش_اقساط.pdf", "PDF Files (*.pdf)")
        if file_path:
            success = report_generator.create_installments_report(installments, start_date, end_date, status, file_path)
            if success:
                QMessageBox.information(self, "موفقیت", "گزارش با موفقیت ذخیره شد.")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")




