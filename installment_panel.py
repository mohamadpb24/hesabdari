# installment_panel.py (نسخه نهایی با فرم تسویه وام مدرن و اصلاح شده)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QAbstractItemView,
    QGroupBox, QGridLayout
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt
import jdatetime
from decimal import Decimal

from db_manager import DatabaseManager
from utils import format_money

class InstallmentPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.setContentsMargins(25, 20, 25, 20)
        self.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff; border: 1px solid #e1e8ed;
                border-radius: 12px; padding: 20px; margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 5px 20px; background-color: #34495e;
                color: white; border-radius: 8px; font-weight: bold;
            }
            QLabel { color: #34495e; font-size: 10pt; }
            QLabel.header-value { font-weight: bold; color: #2c3e50; font-size: 11pt; }
            QLabel#remaining_balance_val { font-weight: bold; color: #c0392b; font-size: 12pt; }
            QTableWidget { border: 1px solid #e1e8ed; border-radius: 8px; }
        """)

        self.current_customer_id = None
        self.current_loan_id = None
        
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        top_layout = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.loan_combo = QComboBox()
        self.settle_loan_btn = QPushButton("تسویه کامل وام")
        self.settle_loan_btn.setEnabled(False)
        self.settle_loan_btn.setStyleSheet("background-color: #e67e22; color: white; border-radius: 5px; padding: 5px; font-weight: bold;")
        
        top_layout.addWidget(QLabel("انتخاب مشتری:"))
        top_layout.addWidget(self.customer_combo, 1)
        top_layout.addWidget(QLabel("انتخاب وام:"))
        top_layout.addWidget(self.loan_combo, 2)
        top_layout.addWidget(self.settle_loan_btn)

        self.loan_header_group = QGroupBox("خلاصه وضعیت وام")
        self.loan_header_group.setFont(QFont("B Yekan", 11, QFont.Bold))
        self.loan_header_group.setVisible(False)
        
        header_grid = QGridLayout(self.loan_header_group)
        self.lbl_person_name = QLabel("..."); self.lbl_person_name.setObjectName("header-value")
        self.lbl_loan_code = QLabel("..."); self.lbl_loan_code.setObjectName("header-value")
        self.lbl_total_amount = QLabel("..."); self.lbl_total_amount.setObjectName("header-value")
        self.lbl_remaining_balance = QLabel("..."); self.lbl_remaining_balance.setObjectName("remaining_balance_val")
        self.lbl_installment_amount = QLabel("..."); self.lbl_installment_amount.setObjectName("header-value")
        self.lbl_loan_term = QLabel("..."); self.lbl_loan_term.setObjectName("header-value")

        self.lbl_total_penalty = QLabel("..."); self.lbl_total_penalty.setObjectName("header-value")
        self.lbl_total_penalty.setStyleSheet("color: #c0392b;") # رنگ قرمز برای جریمه

        header_grid.addWidget(QLabel("<b>مشتری:</b>"), 0, 0); header_grid.addWidget(self.lbl_person_name, 0, 1)
        header_grid.addWidget(QLabel("<b>کد وام:</b>"), 0, 2); header_grid.addWidget(self.lbl_loan_code, 0, 3)
        header_grid.addWidget(QLabel("<b>مبلغ کل وام:</b>"), 1, 0); header_grid.addWidget(self.lbl_total_amount, 1, 1)
        header_grid.addWidget(QLabel("<b>مجموع باقیمانده:</b>"), 1, 2); header_grid.addWidget(self.lbl_remaining_balance, 1, 3)
        header_grid.addWidget(QLabel("<b>مجموع جریمه:</b>"), 1, 4); header_grid.addWidget(self.lbl_total_penalty, 1, 5)        
        header_grid.addWidget(QLabel("<b>مبلغ هر قسط:</b>"), 2, 0); header_grid.addWidget(self.lbl_installment_amount, 2, 1)
        header_grid.addWidget(QLabel("<b>تعداد اقساط:</b>"), 2, 2); header_grid.addWidget(self.lbl_loan_term, 2, 3)
        header_grid.setColumnStretch(1, 1); header_grid.setColumnStretch(3, 1)

        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(8)
        self.installments_table.setHorizontalHeaderLabels([
            "کد قسط", "سررسید", "مبلغ قسط", "پرداختی", 
            "جریمه این قسط", "باقیمانده کل", "وضعیت", "عملیات"
        ])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.installments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.installments_table.setAlternatingRowColors(True)

        self.main_layout.addLayout(top_layout)
        self.main_layout.addWidget(self.loan_header_group)
        self.main_layout.addWidget(self.installments_table)

        self.customer_combo.currentIndexChanged.connect(self.load_customer_loans)
        self.loan_combo.currentIndexChanged.connect(self.load_loan_installments)
        self.settle_loan_btn.clicked.connect(self.show_settlement_dialog)

    def refresh_data(self):
        self.load_customers_to_combo()

    def load_customers_to_combo(self):
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem("یک مشتری را انتخاب کنید...", None)
        customers = self.db_manager.get_all_customers()
        if customers:
            for customer_id, name in customers:
                self.customer_combo.addItem(name, customer_id)
        self.customer_combo.blockSignals(False)
        self.clear_loan_data()

    def load_customer_loans(self):
        self.current_customer_id = self.customer_combo.currentData()
        self.loan_combo.blockSignals(True)
        self.loan_combo.clear()
        self.loan_combo.addItem("یک وام را انتخاب کنید...", None)
        if self.current_customer_id:
            loans = self.db_manager.get_customer_loans(self.current_customer_id)
            if loans:
                for loan in loans:
                    self.loan_combo.addItem(f"وام {loan[1]} - مبلغ {format_money(loan[2])} ({loan[3]} ماهه)", loan[0])
        self.loan_combo.blockSignals(False)
        self.clear_loan_data()

    def clear_loan_data(self):
        self.loan_header_group.setVisible(False)
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)

# لطفاً کل این تابع را با کد زیر جایگزین کنید

    def load_loan_installments(self):
        self.current_loan_id = self.loan_combo.currentData()
        if not self.current_loan_id:
            self.clear_loan_data()
            return

        header_data = self.db_manager.get_loan_header_details(self.current_loan_id)
        if header_data:
            self.lbl_person_name.setText(header_data.get('person_name', 'N/A'))
            self.lbl_loan_code.setText(str(header_data.get('loan_code', 'N/A')))
            self.lbl_total_amount.setText(format_money(header_data.get('total_amount', 0)))
            self.lbl_installment_amount.setText(format_money(header_data.get('installment_amount', 0)))
            self.lbl_loan_term.setText(f"{header_data.get('loan_term', 0)} ماه")
            self.loan_header_group.setVisible(True)
            self.settle_loan_btn.setEnabled(True)

        installments = self.db_manager.get_loan_installments(self.current_loan_id)
        self.installments_table.setRowCount(0)
        
        total_payment_remain = 0
        total_penalty_amount = 0

        if installments:
            for row, inst in enumerate(installments):
                self.installments_table.insertRow(row)
                
                # --- شروع بخش ایمن‌سازی در برابر None ---
                # مقادیر را می‌خوانیم و اگر None بودند، آنها را به صفر تبدیل می‌کنیم
                due_amount = inst.get('DueAmount') or 0
                paid_amount = inst.get('PaidAmount') or 0
                penalty_amount = inst.get('PenaltyAmount') or 0
                # در دیتابیس جدید شما، PaymentRemain همان باقیمانده کل است
                payment_remain = inst.get('PaymentRemain') or 0 
                status = inst.get('Status', 'N/A')
                code = inst.get('Code', 'N/A')
                due_date = inst.get('DueDate', 'N/A')
                # --- پایان بخش ایمن‌سازی ---

                self.installments_table.setItem(row, 0, QTableWidgetItem(str(code)))
                self.installments_table.setItem(row, 1, QTableWidgetItem(str(due_date)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(due_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(format_money(paid_amount)))
                
                penalty_amount_item = QTableWidgetItem(format_money(penalty_amount))
                if penalty_amount > 0: # این مقایسه اکنون امن است
                    penalty_amount_item.setForeground(QColor("#c0392b"))
                self.installments_table.setItem(row, 4, penalty_amount_item)
                
                self.installments_table.setItem(row, 5, QTableWidgetItem(format_money(payment_remain)))
                
                status_item = QTableWidgetItem(status)
                if status == 'PAID':
                    status_item.setForeground(QColor("#27ae60"))
                elif status == 'PARTIALLY_PAID':
                    status_item.setForeground(QColor("#f39c12"))
                self.installments_table.setItem(row, 6, status_item)

                if status != 'PAID':
                    pay_btn = QPushButton("پرداخت")
                    pay_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
                    # اطمینان از اینکه داده‌های ارسالی به دیالوگ پرداخت هم None نیستند
                    inst_safe = inst.copy()
                    inst_safe['TotalRemain'] = payment_remain
                    pay_btn.clicked.connect(lambda _, installment_data=inst_safe: self.show_pay_dialog(installment_data))
                    self.installments_table.setCellWidget(row, 7, pay_btn)
                
                total_payment_remain += payment_remain
                total_penalty_amount += penalty_amount

        self.lbl_remaining_balance.setText(format_money(total_payment_remain))
        self.lbl_total_penalty.setText(format_money(total_penalty_amount))
        self.current_loan_id = self.loan_combo.currentData()
        if not self.current_loan_id:
            self.clear_loan_data()
            return

        header_data = self.db_manager.get_loan_header_details(self.current_loan_id)
        if header_data:
            self.lbl_person_name.setText(header_data.get('person_name', 'N/A'))
            self.lbl_loan_code.setText(str(header_data.get('loan_code', 'N/A')))
            self.lbl_total_amount.setText(format_money(header_data.get('total_amount', 0)))
            self.lbl_installment_amount.setText(format_money(header_data.get('installment_amount', 0)))
            self.lbl_loan_term.setText(f"{header_data.get('loan_term', 0)} ماه")
            self.loan_header_group.setVisible(True)
            self.settle_loan_btn.setEnabled(True)

        installments = self.db_manager.get_loan_installments(self.current_loan_id)
        self.installments_table.setRowCount(0)
        
        total_payment_remain = 0
        total_penalty_amount = 0

        if installments:
            for row, inst in enumerate(installments):
                self.installments_table.insertRow(row)
                
                # --- شروع بخش ایمن‌سازی در برابر None ---
                # مقادیر را می‌خوانیم و اگر None بودند، آنها را به صفر تبدیل می‌کنیم
                due_amount = inst.get('DueAmount') or 0
                paid_amount = inst.get('PaidAmount') or 0
                penalty_amount = inst.get('PenaltyAmount') or 0
                # در دیتابیس جدید شما، PaymentRemain همان باقیمانده کل است
                payment_remain = inst.get('PaymentRemain') or 0 
                status = inst.get('Status', 'N/A')
                code = inst.get('Code', 'N/A')
                due_date = inst.get('DueDate', 'N/A')
                # --- پایان بخش ایمن‌سازی ---

                self.installments_table.setItem(row, 0, QTableWidgetItem(str(code)))
                self.installments_table.setItem(row, 1, QTableWidgetItem(str(due_date)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(due_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(format_money(paid_amount)))
                
                penalty_amount_item = QTableWidgetItem(format_money(penalty_amount))
                if penalty_amount > 0: # این مقایسه اکنون امن است
                    penalty_amount_item.setForeground(QColor("#c0392b"))
                self.installments_table.setItem(row, 4, penalty_amount_item)
                
                self.installments_table.setItem(row, 5, QTableWidgetItem(format_money(payment_remain)))
                
                status_item = QTableWidgetItem(status)
                if status == 'PAID':
                    status_item.setForeground(QColor("#27ae60"))
                elif status == 'PARTIALLY_PAID':
                    status_item.setForeground(QColor("#f39c12"))
                self.installments_table.setItem(row, 6, status_item)

                if status != 'PAID':
                    pay_btn = QPushButton("پرداخت")
                    pay_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
                    # اطمینان از اینکه داده‌های ارسالی به دیالوگ پرداخت هم None نیستند
                    inst_safe = inst.copy()
                    inst_safe['TotalRemain'] = payment_remain
                    pay_btn.clicked.connect(lambda _, installment_data=inst_safe: self.show_pay_dialog(installment_data))
                    self.installments_table.setCellWidget(row, 7, pay_btn)
                
                total_payment_remain += payment_remain
                total_penalty_amount += penalty_amount

        self.lbl_remaining_balance.setText(format_money(total_payment_remain))
        self.lbl_total_penalty.setText(format_money(total_penalty_amount)) 
        self.current_loan_id = self.loan_combo.currentData()
        if not self.current_loan_id:
            self.clear_loan_data()
            return

        header_data = self.db_manager.get_loan_header_details(self.current_loan_id)
        if header_data:
            self.lbl_person_name.setText(header_data.get('person_name', 'N/A'))
            self.lbl_loan_code.setText(str(header_data.get('loan_code', 'N/A')))
            self.lbl_total_amount.setText(format_money(header_data.get('total_amount', 0)))
            self.lbl_installment_amount.setText(format_money(header_data.get('installment_amount', 0)))
            self.lbl_loan_term.setText(f"{header_data.get('loan_term', 0)} ماه")
            self.loan_header_group.setVisible(True)
            self.settle_loan_btn.setEnabled(True)

        installments = self.db_manager.get_loan_installments(self.current_loan_id)
        self.installments_table.setRowCount(0)
        
        total_payment_remain = 0
        total_penalty_amount = 0

        if installments:
            for row, inst in enumerate(installments):
                self.installments_table.insertRow(row)
                
                # --- استفاده از .get() برای جلوگیری از خطا ---
                due_amount = inst.get('DueAmount', 0)
                paid_amount = inst.get('PaidAmount', 0)
                penalty_amount = inst.get('PenaltyAmount', 0)
                payment_remain = inst.get('PaymentRemain', 0) # این همان باقیمانده کل است
                status = inst.get('Status', 'N/A')
                code = inst.get('Code', 'N/A')
                due_date = inst.get('DueDate', 'N/A')

                self.installments_table.setItem(row, 0, QTableWidgetItem(str(code)))
                self.installments_table.setItem(row, 1, QTableWidgetItem(str(due_date)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(due_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(format_money(paid_amount)))
                
                penalty_amount_item = QTableWidgetItem(format_money(penalty_amount))
                if penalty_amount > 0:
                    penalty_amount_item.setForeground(QColor("#c0392b"))
                self.installments_table.setItem(row, 4, penalty_amount_item)
                
                self.installments_table.setItem(row, 5, QTableWidgetItem(format_money(payment_remain)))
                
                status_item = QTableWidgetItem(status)
                if status == 'PAID':
                    status_item.setForeground(QColor("#27ae60"))
                elif status == 'PARTIALLY_PAID':
                    status_item.setForeground(QColor("#f39c12"))
                self.installments_table.setItem(row, 6, status_item)

                if status != 'PAID':
                    pay_btn = QPushButton("پرداخت")
                    pay_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
                    pay_btn.clicked.connect(lambda _, installment_data=inst: self.show_pay_dialog(installment_data))
                    self.installments_table.setCellWidget(row, 7, pay_btn)
                
                total_payment_remain += payment_remain
                total_penalty_amount += penalty_amount

        self.lbl_remaining_balance.setText(format_money(total_payment_remain))
        self.lbl_total_penalty.setText(format_money(total_penalty_amount))

    def show_settlement_dialog(self):
        if not self.current_loan_id: return
        details = self.db_manager.get_loan_for_settlement(self.current_loan_id)
        if not details or not details.get('loan_date'):
            QMessageBox.critical(self, "خطا", "اطلاعات وام برای تسویه یافت نشد."); return

        principal = details['principal_amount']
        interest_rate = details['interest_rate']
        total_paid = details.get('total_paid') or 0
        loan_date_str = str(details['loan_date'])
        
        try:
            if '/' in loan_date_str:
                loan_date = jdatetime.datetime.strptime(loan_date_str.split(' ')[0], '%Y/%m/%d').date()
            else:
                loan_date = jdatetime.datetime.strptime(loan_date_str.split(' ')[0], '%Y-%m-%d').date()
        except ValueError:
            QMessageBox.critical(self, "خطای تاریخ", "فرمت تاریخ وام در دیتابیس نامعتبر است."); return

        today = jdatetime.date.today()
        months_passed = (today.year - loan_date.year) * 12 + (today.month - loan_date.month)
        if today.day >= loan_date.day: months_passed += 1
        months_passed = max(1, months_passed)

        new_total_interest = principal * (interest_rate / Decimal(100)) * months_passed
        new_total_loan_value = principal + new_total_interest
        settlement_amount = new_total_loan_value - total_paid
        settlement_amount = max(settlement_amount, 0)

        # --- DIALOG UI ---
        dialog = QDialog(self)
        dialog.setWindowTitle("فرم تسویه کامل وام")
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet("""
            QDialog { background-color: #f9fafb; }
            QGroupBox { border: 1px solid #dfe6e9; background-color: #ffffff; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 5px 15px; background-color: #2980b9; color: white; border-radius: 5px; font-weight: bold; }
        """)
        main_layout = QVBoxLayout(dialog)

        # --- Calculation Details Group ---
        calc_group = QGroupBox("جزئیات محاسبه مبلغ تسویه")
        calc_layout = QFormLayout(calc_group)
        calc_layout.addRow(QLabel("<b>اصل مبلغ وام:</b>"), QLabel(f"{format_money(principal)}"))
        calc_layout.addRow(QLabel("<b>سود ماهانه:</b>"), QLabel(f"{interest_rate}%"))
        calc_layout.addRow(QLabel("<b>تعداد ماه‌های محاسبه شده:</b>"), QLabel(f"{months_passed} ماه"))
        calc_layout.addRow(QLabel("<b>سود محاسبه شده جدید:</b><br/>(اصل وام × سود × ماه‌ها)"), QLabel(f"<b>{format_money(new_total_interest)}</b>"))
        calc_layout.addRow(QLabel("<b>مبلغ کل جدید:</b><br/>(اصل وام + سود جدید)"), QLabel(f"<b>{format_money(new_total_loan_value)}</b>"))
        calc_layout.addRow(QLabel("<b>مجموع مبالغ پرداخت شده:</b>"), QLabel(f"<b style='color:#27ae60;'>- {format_money(total_paid)}</b>"))

        # --- Final Amount Group ---
        final_group = QGroupBox("اطلاعات پرداخت نهایی")
        final_layout = QFormLayout(final_group)
        cashbox_combo = QComboBox()
        cashboxes = self.db_manager.get_all_cash_boxes()
        if cashboxes:
            for box_id, name, _ in cashboxes:
                cashbox_combo.addItem(name, box_id)
        final_layout.addRow(QLabel("<b>مبلغ نهایی برای تسویه:</b>"), QLabel(f"<b style='color:#c0392b; font-size:14pt;'>{format_money(settlement_amount)}</b>"))
        final_layout.addRow("واریز به صندوق:", cashbox_combo)

        # --- Save Button ---
        save_btn = QPushButton(" تایید و تسویه نهایی")
        save_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        save_btn.setStyleSheet("background-color: #27ae60; color: white; border-radius: 8px; padding: 10px;")
        save_btn.clicked.connect(lambda: self.process_settlement(dialog, cashbox_combo.currentData(), settlement_amount))

        main_layout.addWidget(calc_group)
        main_layout.addWidget(final_group)
        main_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        dialog.exec_()

    def process_settlement(self, dialog, fund_id, settlement_amount):
        # ... (این تابع بدون تغییر باقی می‌ماند)
        if not fund_id:
            QMessageBox.warning(dialog, "خطا", "لطفا یک صندوق را انتخاب کنید.")
            return
        
        description = f"تسویه کامل وام {self.lbl_loan_code.text()} برای مشتری {self.lbl_person_name.text()}"
        success, message = self.db_manager.settle_loan(self.current_loan_id, self.current_customer_id, fund_id, settlement_amount, description)

        if success:
            QMessageBox.information(self, "موفقیت", "وام با موفقیت تسویه شد.")
            dialog.accept()
            self.load_loan_installments()
        else:
            QMessageBox.critical(self, "خطا", message)

    def show_pay_dialog(self, installment_data):
        # ... (این تابع بدون تغییر باقی می‌ماند)
        dialog = QDialog(self)
        dialog.setWindowTitle("فرم پرداخت قسط")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog { background-color: #f9fafb; }
            QGroupBox { 
                border: 1px solid #dfe6e9; background-color: #ffffff; 
                border-radius: 8px; margin-top: 10px; 
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 5px 15px; background-color: #8e44ad; color: white;
                border-radius: 5px; font-weight: bold;
            }
            QLineEdit, QComboBox { padding: 10px; border: 1px solid #ced4da; border-radius: 8px; }
        """)
        
        main_layout = QVBoxLayout(dialog)
        
        info_group = QGroupBox("اطلاعات قسط")
        info_layout = QGridLayout(info_group)
        info_layout.addWidget(QLabel("<b>کد قسط:</b>"), 0, 0, alignment=Qt.AlignRight)
        info_layout.addWidget(QLabel(str(installment_data['Code'])), 0, 1)
        info_layout.addWidget(QLabel("<b>تاریخ سررسید:</b>"), 0, 2, alignment=Qt.AlignRight)
        info_layout.addWidget(QLabel(str(installment_data['DueDate'])), 0, 3)
        info_layout.addWidget(QLabel("<b>مبلغ کل قسط:</b>"), 1, 0, alignment=Qt.AlignRight)
        info_layout.addWidget(QLabel(format_money(installment_data['DueAmount'])), 1, 1)
        info_layout.addWidget(QLabel("<b>مبلغ باقی‌مانده:</b>"), 1, 2, alignment=Qt.AlignRight)
        info_layout.addWidget(QLabel(f"<b style='color:#c0392b;'>{format_money(installment_data['PaymentRemain'])}</b>"), 1, 3)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        amount_input = QLineEdit(f"{int(installment_data['PaymentRemain']):,}")
        cashbox_combo = QComboBox()
        description_input = QLineEdit("پرداخت قسط")
        payment_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        
        cashboxes = self.db_manager.get_all_cash_boxes()
        if cashboxes:
            for box_id, name, _ in cashboxes:
                cashbox_combo.addItem(name, box_id)

        form_layout.addRow("مبلغ پرداخت:", amount_input)
        form_layout.addRow("واریز به صندوق:", cashbox_combo)
        form_layout.addRow("تاریخ پرداخت:", payment_date_input)
        form_layout.addRow("شرح:", description_input)

        save_btn = QPushButton(" ثبت پرداخت")
        save_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border-radius: 8px; padding: 10px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)

        def on_save():
            try:
                amount_paid_str = amount_input.text().replace(",", "")
                amount_paid = float(amount_paid_str)
                fund_id = cashbox_combo.currentData()
                payment_date = payment_date_input.text()
                description = description_input.text()

                if not all([amount_paid > 0, fund_id, self.current_customer_id]):
                    QMessageBox.warning(dialog, "خطا", "اطلاعات ناقص است.")
                    return

                success, message = self.db_manager.pay_installment(
                    self.current_customer_id, installment_data['ID'], amount_paid,
                    fund_id, description, payment_date
                )

                if success:
                    QMessageBox.information(self, "موفقیت", "پرداخت با موفقیت ثبت شد.")
                    dialog.accept()
                    self.load_loan_installments()
                else:
                    QMessageBox.critical(self, "خطا", message)
            except (ValueError, TypeError) as e:
                QMessageBox.warning(dialog, "خطای ورودی", f"لطفا مبلغ را به درستی وارد کنید.\n{e}")

        def format_payment_amount():
            text = amount_input.text().replace(",", "")
            if text.isdigit():
                formatted = f"{int(text):,}"
                if amount_input.text() != formatted:
                    amount_input.setText(formatted)
                    amount_input.setCursorPosition(len(formatted))

        amount_input.textChanged.connect(format_payment_amount)
        save_btn.clicked.connect(on_save)

        main_layout.addWidget(info_group)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        dialog.exec_()