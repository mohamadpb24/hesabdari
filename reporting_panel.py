# reporting_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QMessageBox, QFileDialog, QGroupBox,
    QGridLayout
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QSize
import jdatetime

from db_manager import DatabaseManager
from utils import format_money
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

        title_label = QLabel("مرکز گزارش‌گیری")
        title_label.setFont(QFont("B Yekan", 22, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2d3436; margin-bottom: 20px;")
        self.main_layout.addWidget(title_label)

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

        desc = QLabel("گزارش کامل از وضعیت وام‌ها و اقساط یک مشتری خاص.", objectName="card_description")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.update_loan_combo)
        
        self.loan_combo = QComboBox()
        
        btn = QPushButton("دریافت پرونده مشتری")
        btn.clicked.connect(self.generate_customer_report)

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

        desc = QLabel("گزارش دقیق از تمام واریزها و برداشت‌های یک صندوق.", objectName="card_description")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        self.cashbox_combo = QComboBox()
        btn = QPushButton("دریافت گزارش صندوق")
        btn.clicked.connect(self.generate_cashbox_report)
        
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

    def load_customers_to_combo(self):
        self.customer_combo.clear()
        customers = self.db_manager.get_all_customers_with_details()
        self.customer_combo.addItem("یک مشتری را انتخاب کنید...", None)
        
        if customers:
            for customer in customers:
                # روش هوشمند: هم دیکشنری و هم تاپل را پشتیبانی می‌کند
                try:
                    # تلاش برای خواندن به صورت دیکشنری (نام ستون‌ها در SQL)
                    c_id = customer['ID']
                    c_name = customer['FullName']
                    c_nat = customer['NationalID']
                    c_phone = customer['PhoneNumber']
                    c_addr = customer['Address']
                    c_debt = customer['TotalDebt']
                except (TypeError, KeyError, IndexError):
                    # اگر خطا داد، یعنی فرمت تاپل است
                    c_id = customer[0]
                    c_name = customer[1]
                    c_nat = customer[2]
                    c_phone = customer[3]
                    c_addr = customer[4]
                    c_debt = customer[5]

                customer_data = {
                    'id': c_id, 
                    'name': c_name, 
                    'national_code': c_nat,
                    'phone_number': c_phone, 
                    'address': c_addr, 
                    'total_debt': c_debt
                }
                self.customer_combo.addItem(c_name, customer_data)

    def load_cashboxes_to_combo(self):
        self.cashbox_combo.clear()
        cashboxes = self.db_manager.get_all_cash_boxes()
        self.cashbox_combo.addItem("یک صندوق را انتخاب کنید...", None)
        for box_id, name, balance in cashboxes:
            self.cashbox_combo.addItem(name, {'id': box_id, 'name': name, 'balance': balance})
    
    def update_loan_combo(self):
        self.loan_combo.clear()
        customer_data = self.customer_combo.currentData()
        if customer_data:
            loans = self.db_manager.get_customer_loans(customer_data['id'])
            self.loan_combo.addItem("همه وام‌ها", "all")
            for loan_id, readable_id, amount, term in loans:
                item_text = f"{readable_id}: {format_money(amount)} ({term} ماهه)"
                self.loan_combo.addItem(item_text, loan_id)
        else:
            self.loan_combo.addItem("ابتدا یک مشتری انتخاب کنید", None)
            
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
            # تابع create_cashbox_report باید در report_generator وجود داشته باشد
            success = report_generator.create_cashbox_report(cashbox_data, transactions, file_path)
            if success:
                QMessageBox.information(self, "موفقیت", "گزارش با موفقیت ذخیره شد.")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")

    def generate_customer_report(self):
        customer_data = self.customer_combo.currentData()
        selected_loan_id = self.loan_combo.currentData()
        if not customer_data:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشتری را انتخاب کنید.")
            return

        loans, installments_by_loan = self.db_manager.get_full_customer_report_data(customer_data['id'])
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
            QMessageBox.warning(self, "خطا", "فرمت تاریخ صحیح نیست.")
            return

        # دریافت داده‌ها (شامل کد وام)
        raw_installments = self.db_manager.get_installments_by_date_range(start_date, end_date, status)
        
        if not raw_installments:
            QMessageBox.information(self, "گزارش خالی", "هیچ قسطی یافت نشد.")
            return

        formatted_installments = []
        
        for inst in raw_installments:
            try:
                # تلاش برای خواندن به صورت دیکشنری
                DueDate = inst['DueDate']
                DueAmount = inst['DueAmount']
                PaidAmount = inst['PaidAmount']
                Status = inst['Status']
                FullName = inst['FullName']
                PhoneNumber = inst['PhoneNumber']
                InstCode = inst['Code']
                LoanCode = inst['LoanCode'] # ستون جدید
            except (TypeError, KeyError, IndexError):
                # تلاش برای خواندن به صورت تاپل (بر اساس ترتیب SELECT در db_manager)
                DueDate = inst[0]
                DueAmount = inst[1]
                PaidAmount = inst[2]
                Status = inst[3]
                FullName = inst[4]
                PhoneNumber = inst[5]
                InstCode = inst[6]
                LoanCode = inst[7] # ایندکس 7 (ستون آخر)

            # ساخت دیکشنری نهایی
            formatted_item = {
                'due_date': DueDate,
                'amount_due': DueAmount,
                'paid_amount': PaidAmount,
                'amount_paid': PaidAmount, # جهت اطمینان
                'status': Status,
                'customer_name': FullName,
                'phone_number': PhoneNumber,
                'code': InstCode,           # کد قسط
                'loan_readable_id': LoanCode # <--- کلید حل مشکل (کد پرونده وام)
            }
            formatted_installments.append(formatted_item)

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش اقساط", "گزارش_اقساط.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                success = report_generator.create_installments_report(formatted_installments, start_date, end_date, status, file_path)
                if success:
                    QMessageBox.information(self, "موفقیت", "گزارش ذخیره شد.")
                else:
                    QMessageBox.critical(self, "خطا", "خطا در ساخت PDF.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا: {e}")




