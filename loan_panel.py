from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QDate

import jdatetime
from db_manager import DatabaseManager
from utils import format_money, add_months_jalali

class LoanPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.loan_amount = 0
        self.total_interest_amount = 0
        self.total_loan_amount_with_interest = 0

        self.show_loan_form()

    # *** تابع show_loan_form با ظاهر اصلی و صحیح بازگردانده شد ***
    def show_loan_form(self):
        self.clear_layout(self.main_layout)

        title_label = QLabel("پرداخت وام جدید")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)

        form_layout = QFormLayout()

        # Selection fields
        self.customer_combo = QComboBox()
        self.customer_combo.setStyleSheet("""
            QComboBox {
                background-color: white; border: 1px solid #bdc3c7;
                border-radius: 5px; padding: 5px;
            }
        """)
        self.load_customers_to_combo()
        form_layout.addRow("انتخاب مشتری:", self.customer_combo)

        self.cashbox_combo = QComboBox()
        self.cashbox_combo.setStyleSheet("""
            QComboBox {
                background-color: white; border: 1px solid #bdc3c7;
                border-radius: 5px; padding: 5px;
            }
        """)
        self.load_cashboxes_to_combo()
        form_layout.addRow("انتخاب صندوق:", self.cashbox_combo)

        # Input fields with original styling
        line_edit_style = """
            QLineEdit {
                background-color: white; border: 1px solid #bdc3c7;
                border-radius: 5px; padding: 5px;
            }
        """
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ وام را وارد کنید")
        self.amount_input.textChanged.connect(self.format_and_calculate)
        self.amount_input.setStyleSheet(line_edit_style)
        form_layout.addRow("مبلغ وام (تومان):", self.amount_input)

        self.term_input = QLineEdit()
        self.term_input.setPlaceholderText("به ماه")
        self.term_input.textChanged.connect(self.calculate_installments)
        self.term_input.setStyleSheet(line_edit_style)
        form_layout.addRow("مدت بازپرداخت (ماه):", self.term_input)

        self.interest_input = QLineEdit()
        self.interest_input.setPlaceholderText("درصد ماهانه")
        self.interest_input.textChanged.connect(self.calculate_installments)
        self.interest_input.setStyleSheet(line_edit_style)
        form_layout.addRow("سود ماهانه (درصد):", self.interest_input)

        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("مثال: 1403/05/30")
        self.start_date_input.textChanged.connect(self.calculate_installments)
        self.start_date_input.setStyleSheet(line_edit_style)
        form_layout.addRow("تاریخ اولین قسط:", self.start_date_input)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("شرح مربوط به وام")
        self.description_input.setStyleSheet(line_edit_style)
        form_layout.addRow("شرح:", self.description_input)

        # Installments Table
        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(2)
        self.installments_table.setHorizontalHeaderLabels(["تاریخ سررسید", "مبلغ قسط"])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.installments_table.setMinimumHeight(200)

        # Summary Label
        self.summary_label = QLabel("")
        self.summary_label.setFont(QFont("B Yekan", 12))
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setStyleSheet("padding: 10px;")

        # Save Button with original styling
        self.save_btn = QPushButton("ثبت وام و اقساط")
        self.save_btn.setFont(QFont("B Yekan", 12))
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white;
                border-radius: 10px; padding: 10px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.save_btn.clicked.connect(self.save_loan)

        # Original layout structure
        self.main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        self.main_layout.addLayout(form_layout)
        self.main_layout.addWidget(self.summary_label)
        self.main_layout.addWidget(self.installments_table)
        self.main_layout.addWidget(self.save_btn)
    
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def refresh_data(self):
        self.load_customers_to_combo()
        self.load_cashboxes_to_combo()
        self.amount_input.clear()
        self.term_input.clear()
        self.interest_input.clear()
        self.start_date_input.clear()
        self.description_input.clear()
        self.summary_label.clear()
        self.installments_table.setRowCount(0)

    def format_and_calculate(self):
        try:
            text = self.amount_input.text().replace("،", "")
            if text.isdigit():
                formatted_text = f"{int(text):,}".replace(",", "،")
                if self.amount_input.text() != formatted_text:
                    self.amount_input.setText(formatted_text)
                self.calculate_installments()
            elif text:
                self.amount_input.setText("")
        except Exception:
            pass

    def load_customers_to_combo(self):
        customers = self.db_manager.get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("یک مشتری انتخاب کنید", None)
        for customer_id, name in customers:
            self.customer_combo.addItem(name, customer_id)

    def load_cashboxes_to_combo(self):
        cashboxes = self.db_manager.get_all_cash_boxes()
        self.cashbox_combo.clear()
        self.cashbox_combo.addItem("یک صندوق انتخاب کنید", None)
        for box_id, name, balance in cashboxes:
            self.cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)

    def calculate_installments(self):
        try:
            loan_amount_str = self.amount_input.text().replace("،", "")
            self.loan_amount = int(loan_amount_str) if loan_amount_str else 0

            loan_term_str = self.term_input.text()
            interest_rate_str = self.interest_input.text()
            start_date_str = self.start_date_input.text()

            if not all([loan_term_str, interest_rate_str, start_date_str, self.loan_amount > 0]):
                self.installments_table.setRowCount(0)
                self.summary_label.setText("لطفا تمام فیلدهای لازم را پر کنید.")
                return

            loan_term = int(loan_term_str)
            interest_rate = float(interest_rate_str)
            
            date_parts = start_date_str.split('/')
            if len(date_parts) != 3: raise ValueError("Invalid date format")
            start_date_jalali = jdatetime.date(*map(int, date_parts))

            if loan_term <= 0: raise ValueError("Loan term must be positive")

            self.total_interest_amount = (self.loan_amount * (interest_rate / 100)) * loan_term
            self.total_loan_amount_with_interest = self.loan_amount + self.total_interest_amount
            installment_amount = self.total_loan_amount_with_interest / loan_term

            summary = (f"مبلغ کل وام: {format_money(self.loan_amount)}\n"
                       f"مبلغ کل سود: {format_money(self.total_interest_amount)}\n"
                       f"مبلغ کل با سود: {format_money(self.total_loan_amount_with_interest)}\n"
                       f"مبلغ هر قسط: {format_money(installment_amount)}")
            self.summary_label.setText(summary)

            self.installments_table.setRowCount(loan_term)
            for i in range(loan_term):
                due_date_jalali = add_months_jalali(start_date_jalali, i)
                self.installments_table.setItem(i, 0, QTableWidgetItem(due_date_jalali.strftime('%Y/%m/%d')))
                self.installments_table.setItem(i, 1, QTableWidgetItem(format_money(installment_amount)))

        except (ValueError, IndexError):
            self.installments_table.setRowCount(0)
            self.summary_label.setText("خطا در ورودی‌ها. لطفا فرمت تاریخ (YYYY/MM/DD) و اعداد را بررسی کنید.")

    # *** تابع save_loan با منطق صحیح و تاریخ امروز برای تراکنش ***
    def save_loan(self):
        try:
            customer_id = self.customer_combo.currentData()
            customer_name = self.customer_combo.currentText()
            cash_box_id = self.cashbox_combo.currentData()
            loan_amount = int(self.amount_input.text().replace("،", ""))
            loan_term = int(self.term_input.text())
            interest_rate = float(self.interest_input.text())
            start_date_str = self.start_date_input.text()
            user_description = self.description_input.text()

            if not all([customer_id, cash_box_id, loan_amount > 0, loan_term > 0, interest_rate >= 0, start_date_str]):
                QMessageBox.warning(self, "خطا", "لطفا تمام فیلدهای لازم را به درستی پر کنید.")
                return

            # تاریخ تراکنش، همان روز جاری است
            transaction_date_str = jdatetime.date.today().strftime('%Y/%m/%d')
            
            # 1. ثبت وام در دیتابیس
            loan_id = self.db_manager.add_loan(customer_id, cash_box_id, loan_amount, loan_term, interest_rate, start_date_str)
            if not loan_id:
                QMessageBox.critical(self, "خطا", "خطا در ثبت اطلاعات وام.")
                return

            # 2. به‌روزرسانی موجودی صندوق (کاهش موجودی)
            if not self.db_manager.update_cash_box_balance(cash_box_id, -loan_amount):
                QMessageBox.critical(self, "خطا", "خطا در به‌روزرسانی موجودی صندوق.")
                return

            # 3. ثبت یک تراکنش واحد با تاریخ امروز
            transaction_description = f"پرداخت وام به {customer_name}"
            if user_description:
                transaction_description += f" - {user_description}"
            
            self.db_manager.record_transaction(
                "loan_payment", loan_amount, transaction_date_str, 
                cash_box_id, customer_id, transaction_description
            )

            # 4. ثبت اقساط وام
            start_date_jalali = jdatetime.date(*map(int, start_date_str.split('/')))
            installment_amount = self.total_loan_amount_with_interest / loan_term
            
            for i in range(loan_term):
                due_date_jalali = add_months_jalali(start_date_jalali, i)
                due_date_str = due_date_jalali.strftime('%Y/%m/%d')
                if not self.db_manager.add_installment(loan_id, due_date_str, installment_amount):
                    QMessageBox.critical(self, "خطا", f"خطا در ثبت قسط شماره {i+1}.")
                    return
            
            QMessageBox.information(self, "موفقیت", "وام و اقساط با موفقیت ثبت شد.")
            self.refresh_data()

        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "خطا", f"مقادیر ورودی نامعتبر است. لطفا فیلدها را بررسی کنید.\n{e}")