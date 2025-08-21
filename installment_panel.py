from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QDoubleSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import jdatetime
from db_manager import DatabaseManager
from utils import format_money

class InstallmentPanel(QWidget):
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
        
        loan_layout.addWidget(loan_label)
        loan_layout.addWidget(self.loan_combo)
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
        self.customer_combo.setCurrentIndex(-1)
        self.loan_combo.clear()
        self.installments_table.setRowCount(0)
    
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
        for customer_id, name in customers:
            self.customer_combo.addItem(name, customer_id)
            
    def load_customer_loans(self):
        self.current_customer_id = self.customer_combo.currentData()
        self.loan_combo.clear()
        if self.current_customer_id:
            loans = self.db_manager.get_customer_loans(self.current_customer_id)
            for loan_id, amount, term, date in loans:
                self.loan_combo.addItem(f"وام به مبلغ {format_money(amount)} ({term} ماهه)", loan_id)
    
    def load_loan_installments(self):
        self.current_loan_id = self.loan_combo.currentData()
        self.installments_table.setRowCount(0)
        if self.current_loan_id:
            installments = self.db_manager.get_loan_installments(self.current_loan_id)
            for row, installment in enumerate(installments):
                installment_id, due_date, amount_due, amount_paid = installment
                
                self.installments_table.insertRow(row)
                
                remaining_amount = amount_due - amount_paid
                
                if amount_paid == amount_due:
                    status = "پرداخت شده"
                elif amount_paid > 0:
                    status = "پرداخت ناقص"
                else:
                    status = "پرداخت نشده"
                
                self.installments_table.setItem(row, 0, QTableWidgetItem(due_date))
                self.installments_table.setItem(row, 1, QTableWidgetItem(format_money(amount_due)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(remaining_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(status))
                
                if status != "پرداخت شده":
                    pay_btn = QPushButton("پرداخت قسط")
                    pay_btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #2ecc71; 
                            color: white; 
                            border-radius: 5px;
                            padding: 5px;
                        }
                        QPushButton:hover { background-color: #27ae60; }
                    """)
                    pay_btn.clicked.connect(lambda _, inst_id=installment_id, rem_amount=remaining_amount: self.show_pay_dialog(inst_id, rem_amount))
                    self.installments_table.setCellWidget(row, 4, pay_btn)
                
    def show_pay_dialog(self, installment_id, remaining_amount):
        dialog = QDialog(self)
        dialog.setWindowTitle("پرداخت قسط")
        dialog.setGeometry(200, 200, 400, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f0f4f8;
                border: 1px solid #c0c4c8;
                border-radius: 10px;
            }
            QLabel, QLineEdit, QPushButton, QComboBox {
                font-size: 12px;
                font-family: "B Yekan";
            }
            QPushButton {
                padding: 10px;
                border-radius: 5px;
            }
        """)

        form_layout = QFormLayout(dialog)
        
        remaining_label = QLabel(f"مانده قسط: <b>{format_money(remaining_amount)}</b>")
        remaining_label.setFont(QFont("B Yekan", 12))
        form_layout.addRow(remaining_label)

        amount_input = QLineEdit()
        amount_input.setText(str(int(remaining_amount)))
        amount_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-family: "B Yekan";
            }
        """)
        amount_input.textChanged.connect(lambda text, input=amount_input: self.format_amount_input(text, input))
        form_layout.addRow("مبلغ پرداخت:", amount_input)

        cashbox_combo = QComboBox()
        cashbox_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-family: "B Yekan";
            }
        """)
        
        cashboxes = self.db_manager.get_all_cash_boxes()
        for box_id, name, balance in cashboxes:
            cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)
        
        form_layout.addRow("پرداخت به صندوق:", cashbox_combo)

        # فیلد جدید: شرح تراکنش
        self.payment_description_input = QLineEdit()
        self.payment_description_input.setPlaceholderText("شرح مربوط به پرداخت قسط")
        self.payment_description_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-family: "B Yekan";
            }
        """)
        form_layout.addRow("شرح:", self.payment_description_input)

        pay_btn = QPushButton("ثبت پرداخت")
        pay_btn.setFont(QFont("B Yekan", 12))
        pay_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2ecc71; 
                color: white; 
                border-radius: 10px; 
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        pay_btn.clicked.connect(lambda: self.process_payment(dialog, installment_id, amount_input.text(), cashbox_combo.currentData(), self.payment_description_input.text()))
        form_layout.addRow(pay_btn)
        
        dialog.exec_()
    
    def format_amount_input(self, text, input_widget):
        plain_text = text.replace("،", "").replace("تومان", "").strip()
        if not plain_text.isdigit():
            input_widget.setText("")
            return
        
        formatted_text = f"{int(plain_text):,}".replace(",", "،")
        input_widget.setText(formatted_text)
    
    def process_payment(self, dialog, installment_id, amount_str, cashbox_id, description):
        amount_str = amount_str.replace("،", "").replace("تومان", "").strip()
        try:
            amount = int(amount_str)
        except ValueError:
            QMessageBox.warning(dialog, "خطا", "لطفا مبلغ معتبر وارد کنید.")
            return

        if amount <= 0:
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت باید بیشتر از صفر باشد.")
            return

        remaining_amount_db = self.db_manager.get_installment_details(installment_id)
        if remaining_amount_db and amount > remaining_amount_db[2] - remaining_amount_db[3]:
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت بیشتر از مانده قسط است.")
            return

        if self.db_manager.pay_installment(installment_id, amount, cashbox_id):
            QMessageBox.information(self, "موفقیت", "قسط با موفقیت پرداخت شد.")
            dialog.accept()
            self.load_loan_installments()
            
            loan_details = self.db_manager.get_loan_details_by_id(self.current_loan_id)
            customer_id = loan_details[0]
            customer_name = self.db_manager.get_customer_name(customer_id)
            
            # ثبت تراکنش با شرح جدید
            transaction_description = f"دریافت قسط از مشتری {customer_name}"
            if description:
                transaction_description += f" - {description}"
            
            self.db_manager.record_transaction("installment_received", amount, jdatetime.date.today().strftime('%Y/%m/%d'), customer_id, cashbox_id, transaction_description)
            
        else:
            QMessageBox.critical(self, "خطا", "خطا در پرداخت قسط. لطفا دوباره تلاش کنید.")
