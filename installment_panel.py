from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QAbstractItemView
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

class InstallmentPanel(QWidget):
    # ... (بقیه توابع تا show_settlement_dialog بدون تغییر) ...
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        self.current_customer_id = None
        self.current_loan_id = None
        
        self.build_ui()

    def build_ui(self):
        self.clear_layout(self.main_layout)

        title_label = QLabel("پنل پرداخت اقساط")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)
        
        customer_layout = QHBoxLayout()
        customer_label = QLabel("انتخاب مشتری:")
        self.customer_combo = QComboBox()
        self.customer_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.load_customers_to_combo()
        self.customer_combo.currentIndexChanged.connect(self.load_customer_loans)
        
        customer_layout.addWidget(customer_label)
        customer_layout.addWidget(self.customer_combo)
        self.main_layout.addLayout(customer_layout)

        loan_layout = QHBoxLayout()
        loan_label = QLabel("انتخاب وام:")
        self.loan_combo = QComboBox()
        self.loan_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.loan_combo.currentIndexChanged.connect(self.load_loan_installments)
        
        self.settle_loan_btn = QPushButton("تسویه کامل وام")
        self.settle_loan_btn.setFont(QFont("B Yekan", 11))
        self.settle_loan_btn.setIcon(QIcon.fromTheme("emblem-ok"))
        self.settle_loan_btn.setStyleSheet("""
            QPushButton { 
                background-color: #e67e22; 
                color: white; 
                border-radius: 8px; 
                padding: 10px;
            }
            QPushButton:hover { background-color: #d35400; }
            QPushButton:disabled { background-color: #95a5a6; }
        """)
        self.settle_loan_btn.clicked.connect(self.show_settlement_dialog)
        self.settle_loan_btn.setEnabled(False) 
        
        loan_layout.addWidget(loan_label)
        loan_layout.addWidget(self.loan_combo, 1)
        loan_layout.addWidget(self.settle_loan_btn)
        self.main_layout.addLayout(loan_layout)

        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(5)
        self.installments_table.setHorizontalHeaderLabels(["تاریخ سررسید", "مبلغ قسط", "مانده", "وضعیت قسط", "عملیات"])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.installments_table.setFont(QFont("B Yekan", 10))
        self.installments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.installments_table.setSelectionMode(QTableWidget.SingleSelection)
        self.main_layout.addWidget(self.installments_table)

    def refresh_data(self):
        self.load_customers_to_combo()
        self.customer_combo.setCurrentIndex(0)
        self.loan_combo.clear()
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)
    
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def load_customers_to_combo(self):
        customers = self.db_manager.get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("یک مشتری انتخاب کنید", None)
        for customer_id, name in customers:
            self.customer_combo.addItem(name, customer_id)
            
    def load_customer_loans(self):
        self.current_customer_id = self.customer_combo.currentData()
        self.loan_combo.clear()
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)
        
        if self.current_customer_id:
            loans = self.db_manager.get_customer_loans(self.current_customer_id)
            if loans:
                self.loan_combo.addItem("یک وام انتخاب کنید", None)
                for loan_id, amount, term, date in loans:
                    self.loan_combo.addItem(f"وام به مبلغ {format_money(amount)} ({term} ماهه)", loan_id)
    
    def load_loan_installments(self):
        self.current_loan_id = self.loan_combo.currentData()
        self.installments_table.setRowCount(0)
        
        if self.current_loan_id:
            is_fully_paid = self.db_manager.is_loan_fully_paid(self.current_loan_id)
            self.settle_loan_btn.setEnabled(not is_fully_paid)

            installments = self.db_manager.get_loan_installments(self.current_loan_id)
            for row, installment in enumerate(installments):
                installment_id, due_date, amount_due, amount_paid = installment
                
                self.installments_table.insertRow(row)
                
                remaining_amount = amount_due - amount_paid
                if remaining_amount < 0: remaining_amount = 0

                status = "پرداخت نشده"
                if amount_paid >= amount_due:
                    status = "پرداخت شده"
                elif amount_paid > 0:
                    status = "پرداخت ناقص"
                
                self.installments_table.setItem(row, 0, QTableWidgetItem(due_date))
                self.installments_table.setItem(row, 1, QTableWidgetItem(format_money(amount_due)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(remaining_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(status))
                
                if not is_fully_paid and status != "پرداخت شده":
                    pay_btn = QPushButton("پرداخت قسط")
                    pay_btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #2ecc71; color: white; border-radius: 5px; padding: 5px;
                        }
                        QPushButton:hover { background-color: #27ae60; }
                    """)
                    pay_btn.clicked.connect(lambda _, inst_id=installment_id, rem_amount=remaining_amount: self.show_pay_dialog(inst_id, rem_amount))
                    self.installments_table.setCellWidget(row, 4, pay_btn)
        else:
            self.settle_loan_btn.setEnabled(False)
            
    def show_settlement_dialog(self):
        if not self.current_loan_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک وام را انتخاب کنید.")
            return

        details = self.db_manager.get_loan_for_settlement(self.current_loan_id)
        if not details:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات تسویه وام.")
            return

        principal = details['amount']
        interest_rate = details['interest_rate']
        total_paid = details['total_paid']
        start_date_str = details['start_date']
        
        start_date = jdatetime.datetime.strptime(start_date_str, '%Y/%m/%d').date()
        today = jdatetime.date.today()
        
        months_passed = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
        
        new_total_interest = principal * (interest_rate / 100) * months_passed
        new_total_loan_value = principal + new_total_interest
        settlement_amount = new_total_loan_value - total_paid

        if settlement_amount < 0: settlement_amount = 0

        dialog = QDialog(self)
        dialog.setWindowTitle("فرم تسویه کامل وام")
        dialog.setMinimumWidth(500)
        
        main_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        style_sheet = """
            QLabel { font-size: 13px; padding: 5px; }
            QLabel#title { font-size: 16px; font-weight: bold; color: #2c3e50; }
            QLabel#final_amount { font-size: 18px; font-weight: bold; color: #c0392b; padding: 10px; background-color: #f9e6e4; border-radius: 5px;}
            QComboBox, QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 5px; }
        """
        dialog.setStyleSheet(style_sheet)
        
        form_layout.addRow(QLabel("جزئیات محاسبه تسویه", objectName="title"))
        form_layout.addRow(QLabel("-" * 60))
        form_layout.addRow(QLabel(f"اصل مبلغ وام:"), QLabel(f"<b>{format_money(principal)}</b>"))
        form_layout.addRow(QLabel(f"تعداد ماه‌های محاسبه شده:"), QLabel(f"<b>{months_passed} ماه</b>"))
        form_layout.addRow(QLabel(f"سود محاسبه شده جدید:"), QLabel(f"<b>{format_money(new_total_interest)}</b>"))
        form_layout.addRow(QLabel(f"مبلغ کل جدید (اصل + سود جدید):"), QLabel(f"<b>{format_money(new_total_loan_value)}</b>"))
        form_layout.addRow(QLabel(f"مجموع مبالغ پرداخت شده تاکنون:"), QLabel(f"<b>{format_money(total_paid)}</b>"))
        form_layout.addRow(QLabel("-" * 60))
        form_layout.addRow(QLabel("مبلغ نهایی برای تسویه:", objectName="final_amount"), QLabel(f"<b>{format_money(settlement_amount)}</b>", objectName="final_amount"))
        
        cashbox_combo = QComboBox()
        cashboxes = self.db_manager.get_all_cash_boxes()
        for box_id, name, balance in cashboxes:
            cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)
        form_layout.addRow("واریز به صندوق:", cashbox_combo)

        description_input = QLineEdit("تسویه کامل وام")
        form_layout.addRow("شرح تراکنش:", description_input)

        confirm_btn = QPushButton("تایید و تسویه نهایی")
        confirm_btn.setFont(QFont("B Yekan", 12))
        confirm_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 8px;")
        # *** ارسال new_total_loan_value به process_settlement ***
        confirm_btn.clicked.connect(lambda: self.process_settlement(dialog, settlement_amount, cashbox_combo.currentData(), description_input.text(), new_total_loan_value))
        
        main_layout.addLayout(form_layout)
        main_layout.addWidget(confirm_btn, alignment=Qt.AlignCenter)

        dialog.exec_()
        
    # *** این تابع برای ارسال new_total_loan_value اصلاح شد ***
    def process_settlement(self, dialog, amount, cashbox_id, description, new_total_loan_value):
        if not cashbox_id:
            QMessageBox.warning(dialog, "خطا", "لطفا یک صندوق را انتخاب کنید.")
            return

        reply = QMessageBox.question(self, 'تایید تسویه', 
                                     f"آیا از تسویه کامل این وام با مبلغ {format_money(amount)} مطمئن هستید؟",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # ارسال new_total_loan_value به db_manager
            if self.db_manager.settle_loan(self.current_loan_id, amount, cashbox_id, new_total_loan_value):
                customer_name = self.customer_combo.currentText()
                trans_desc = f"تسویه وام مشتری {customer_name} - {description}"
                
                self.db_manager.record_transaction(
                    "settlement_received", amount, jdatetime.date.today().strftime('%Y/%m/%d'), 
                    self.current_customer_id, cashbox_id, trans_desc
                )
                
                QMessageBox.information(self, "موفقیت", "وام با موفقیت تسویه شد.")
                dialog.accept()
                self.load_loan_installments()
            else:
                QMessageBox.critical(self, "خطا", "خطا در عملیات تسویه وام.")

    def show_pay_dialog(self, installment_id, remaining_amount):
        dialog = QDialog(self)
        dialog.setWindowTitle("پرداخت قسط")
        dialog.setGeometry(200, 200, 400, 350)
        form_layout = QFormLayout(dialog)
        
        remaining_label = QLabel(f"مانده قسط: <b>{format_money(remaining_amount)}</b>")
        form_layout.addRow(remaining_label)

        amount_input = QLineEdit(str(int(remaining_amount)))
        amount_input.textChanged.connect(lambda text, input=amount_input: self.format_amount_input(text, input))
        form_layout.addRow("مبلغ پرداخت:", amount_input)

        cashbox_combo = QComboBox()
        cashboxes = self.db_manager.get_all_cash_boxes()
        for box_id, name, balance in cashboxes:
            cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)
        form_layout.addRow("پرداخت به صندوق:", cashbox_combo)
        
        description_input = QLineEdit()
        description_input.setPlaceholderText("شرح مربوط به پرداخت قسط")
        form_layout.addRow("شرح:", description_input)

        pay_btn = QPushButton("ثبت پرداخت")
        pay_btn.clicked.connect(lambda: self.process_payment(dialog, installment_id, amount_input.text(), cashbox_combo.currentData(), description_input.text()))
        form_layout.addRow(pay_btn)
        
        dialog.exec_()
    
    def format_amount_input(self, text, input_widget):
        try:
            plain_text = text.replace("،", "").replace("تومان", "").strip()
            if not plain_text: return
            if not plain_text.isdigit():
                valid_chars = [c for c in plain_text if c.isdigit()]
                plain_text = "".join(valid_chars) if valid_chars else ""

            formatted_text = f"{int(plain_text):,}".replace(",", "،")
            
            if input_widget.text() != formatted_text:
                input_widget.setText(formatted_text)
        except (ValueError, TypeError):
            input_widget.setText("")

    def process_payment(self, dialog, installment_id, amount_str, cashbox_id, description):
        amount_str = amount_str.replace("،", "").replace("تومان", "").strip()
        try: amount = int(amount_str)
        except (ValueError, TypeError):
            QMessageBox.warning(dialog, "خطا", "لطفا مبلغ معتبر وارد کنید.")
            return

        if amount <= 0:
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت باید بیشتر از صفر باشد.")
            return

        installment_details = self.db_manager.get_installment_details(installment_id)
        if installment_details and amount > (installment_details[2] - installment_details[3]):
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت بیشتر از مانده قسط است.")
            return

        if self.db_manager.pay_installment(installment_id, amount, cashbox_id):
            QMessageBox.information(self, "موفقیت", "قسط با موفقیت پرداخت شد.")
            dialog.accept()
            self.load_loan_installments()
            
            customer_name = self.customer_combo.currentText()
            
            transaction_description = f"دریافت قسط از مشتری {customer_name}"
            if description:
                transaction_description += f" - {description}"
            
            self.db_manager.record_transaction(
                "installment_received", amount, 
                jdatetime.date.today().strftime('%Y/%m/%d'), 
                self.current_customer_id, cashbox_id, transaction_description
            )
        else:
            QMessageBox.critical(self, "خطا", "خطا در پرداخت قسط. لطفا دوباره تلاش کنید.")