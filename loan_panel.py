# loan_panel.py (نسخه نهایی با ظاهر جدید و چیدمان اصلاح شده)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money, add_months_jalali

class LoanPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.total_loan_amount_with_interest = 0
        self.build_ui()

    def build_ui(self):
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet("""
            #container { background-color: #f4f7f9; }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e1e8ed;
                border-radius: 12px;
                padding: 20px;
            }
            QLineEdit, QComboBox {
                padding: 12px;
                border: 1px solid #ced4da;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QLabel#summaryLabel {
                font-size: 11pt; padding: 12px;
                background-color: #e9ecef; border-radius: 8px;
                color: #495057;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 20, 25, 20)
        
        title_label = QLabel("ایجاد وام جدید")
        title_label.setFont(QFont("B Yekan", 22, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("margin-bottom: 15px; color: #2c3e50;")

        # --- Top Layout for Forms ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(25)

        # --- Basic Info GroupBox ---
        customer_group = QGroupBox("اطلاعات پایه")
        customer_layout = QFormLayout(customer_group)
        self.customer_combo = QComboBox()
        self.cashbox_combo = QComboBox()
        self.transaction_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        customer_layout.addRow("انتخاب مشتری:", self.customer_combo)
        customer_layout.addRow("پرداخت از صندوق:", self.cashbox_combo)
        customer_layout.addRow("تاریخ پرداخت وام:", self.transaction_date_input)
        
        # --- Loan Details GroupBox ---
        details_group = QGroupBox("جزئیات وام")
        details_layout = QFormLayout(details_group)
        self.amount_input = QLineEdit()
        self.term_input = QLineEdit()
        self.interest_input = QLineEdit()
        self.penalty_input = QLineEdit("0")
        self.start_date_input = QLineEdit()
        self.description_input = QLineEdit()
        
        details_layout.addRow("مبلغ وام:", self.amount_input)
        details_layout.addRow("مدت بازپرداخت (ماه):", self.term_input)
        details_layout.addRow("سود ماهانه (%):", self.interest_input)
        details_layout.addRow("جریمه روزانه (%):", self.penalty_input)
        details_layout.addRow("تاریخ اولین قسط:", self.start_date_input)
        details_layout.addRow("شرح:", self.description_input)

        top_layout.addWidget(customer_group)
        top_layout.addWidget(details_group)

        # --- Bottom Layout for Preview ---
        preview_group = QGroupBox("پیش‌نمایش اقساط")
        preview_layout = QVBoxLayout(preview_group)
        
        self.summary_label = QLabel("اطلاعات را برای محاسبه وارد کنید.")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setAlignment(Qt.AlignCenter)
        
        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(2)
        self.installments_table.setHorizontalHeaderLabels(["تاریخ سررسید", "مبلغ قسط"])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        preview_layout.addWidget(self.summary_label)
        preview_layout.addWidget(self.installments_table)
        
        # --- Save Button ---
        self.save_btn = QPushButton(" ثبت نهایی وام")
        self.save_btn.setFont(QFont("B Yekan", 12, QFont.Bold))
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; border-radius: 12px; padding: 10px; }
            QPushButton:hover { background-color: #3498db; }
        """)

        # --- Assemble Layouts ---
        container_layout.addWidget(title_label)
        container_layout.addLayout(top_layout)
        container_layout.addWidget(preview_group)
        container_layout.addWidget(self.save_btn)
        self.main_layout.addWidget(container)

        # --- Connect Signals ---
        self.amount_input.textChanged.connect(self._format_amount_input)
        self.term_input.textChanged.connect(self.calculate_installments)
        self.interest_input.textChanged.connect(self.calculate_installments)
        self.start_date_input.textChanged.connect(self.calculate_installments)
        self.save_btn.clicked.connect(self.save_loan)

        # --- Initial Data Load ---
        self.refresh_data()

    def _format_amount_input(self):
        text = self.amount_input.text()
        text_no_comma = text.replace(",", "")
        if text_no_comma.isdigit():
            formatted_text = f"{int(text_no_comma):,}"
            if text != formatted_text:
                self.amount_input.textChanged.disconnect()
                self.amount_input.setText(formatted_text)
                self.amount_input.setCursorPosition(len(formatted_text))
                self.amount_input.textChanged.connect(self._format_amount_input)
                self.calculate_installments()
        elif text:
             self.amount_input.textChanged.disconnect()
             self.amount_input.clear()
             self.amount_input.textChanged.connect(self._format_amount_input)
             self.calculate_installments()

    # ... (بقیه توابع کلاس بدون تغییر باقی می‌مانند و نیازی به بازنویسی ندارند)
    def refresh_data(self):
        self.load_customers_to_combo()
        self.load_cashboxes_to_combo()
        self.amount_input.clear()
        self.term_input.clear()
        self.interest_input.clear()
        self.penalty_input.setText("0")
        self.start_date_input.clear()
        self.description_input.clear()
        self.summary_label.setText("اطلاعات را برای محاسبه وارد کنید.")
        self.installments_table.setRowCount(0)

    def load_customers_to_combo(self):
        self.customer_combo.clear()
        customers = self.db_manager.get_all_customers()
        self.customer_combo.addItem("یک مشتری انتخاب کنید...", None)
        if customers:
            for customer_id, name in customers:
                self.customer_combo.addItem(name, customer_id)

    def load_cashboxes_to_combo(self):
        self.cashbox_combo.clear()
        cashboxes = self.db_manager.get_all_cash_boxes()
        self.cashbox_combo.addItem("یک صندوق انتخاب کنید...", None)
        if cashboxes:
            for box_id, name, balance in cashboxes:
                self.cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)

    def calculate_installments(self):
        try:
            amount_str = self.amount_input.text().replace(",", "")
            loan_amount = int(amount_str) if amount_str else 0
            term_str = self.term_input.text()
            interest_str = self.interest_input.text()
            start_date_str = self.start_date_input.text()

            if not all([loan_amount > 0, term_str, interest_str, start_date_str]):
                self.installments_table.setRowCount(0)
                self.summary_label.setText("لطفا فیلدهای مالی و تاریخ را پر کنید.")
                return

            loan_term = int(term_str)
            interest_rate = float(interest_str)
            
            if len(start_date_str.split('/')) != 3:
                self.installments_table.setRowCount(0); return

            start_date_jalali = jdatetime.date(*map(int, start_date_str.split('/')))
            total_interest = (loan_amount * (interest_rate / 100)) * loan_term
            self.total_loan_amount_with_interest = loan_amount + total_interest
            installment_amount = self.total_loan_amount_with_interest / loan_term

            summary_text = (f"کل سود: {format_money(total_interest)}  |  "
                            f"مبلغ نهایی: {format_money(self.total_loan_amount_with_interest)}  |  "
                            f"هر قسط: {format_money(installment_amount)}")
            self.summary_label.setText(summary_text)

            self.installments_table.setRowCount(loan_term)
            for i in range(loan_term):
                due_date = add_months_jalali(start_date_jalali, i)
                self.installments_table.setItem(i, 0, QTableWidgetItem(due_date.strftime('%Y/%m/%d')))
                self.installments_table.setItem(i, 1, QTableWidgetItem(format_money(installment_amount)))

        except (ValueError, IndexError):
            self.installments_table.setRowCount(0)
            self.summary_label.setText("خطا در مقادیر ورودی. لطفا فرمت‌ها را بررسی کنید.")

    def save_loan(self):
        try:
            person_id = self.customer_combo.currentData()
            fund_id = self.cashbox_combo.currentData()
            amount = int(self.amount_input.text().replace(",", ""))
            loan_term = int(self.term_input.text())
            interest_rate = float(self.interest_input.text())
            penalty_rate = float(self.penalty_input.text() or 0)
            
            # `start_date` تاریخ اولین قسط است
            start_date = self.start_date_input.text() 
            # `loan_date` تاریخ پرداخت وام است
            loan_date = self.transaction_date_input.text() 
            
            description = self.description_input.text() or f"پرداخت وام به {self.customer_combo.currentText()}"

            if not all([person_id, fund_id, amount > 0, loan_term > 0, start_date, loan_date]):
                QMessageBox.warning(self, "خطای ورودی", "لطفا تمام فیلدهای اصلی را به درستی پر کنید.")
                return

            installments_data = []
            installment_amount = self.total_loan_amount_with_interest / loan_term
            start_date_jalali = jdatetime.date(*map(int, start_date.split('/')))
            for i in range(loan_term):
                due_date_jalali = add_months_jalali(start_date_jalali, i)
                installments_data.append({
                    'due_date': due_date_jalali.strftime('%Y/%m/%d'),
                    'amount_due': installment_amount
                })
            
            end_date = installments_data[-1]['due_date'] if installments_data else start_date

            loan_data = {
                'person_id': person_id, 'fund_id': fund_id, 'amount': amount,
                'loan_term': loan_term, 'interest_rate': interest_rate,
                'penalty_rate': penalty_rate,
                'loan_date': loan_date, 
                'end_date': end_date,
                'remain_amount': self.total_loan_amount_with_interest,
                'description': description
            }

            success, message = self.db_manager.create_loan_and_installments(loan_data, installments_data)

            if success:
                QMessageBox.information(self, "موفقیت", "وام و اقساط با موفقیت ثبت شد.")
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطای پایگاه داده", message)

        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "خطای ورودی", f"مقادیر وارد شده نامعتبر است. لطفا فیلدها را بررسی کنید.\n{e}")










