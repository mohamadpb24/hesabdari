# installment_panel.py (نسخه بازنویسی شده)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QAbstractItemView,
    QGroupBox, QGridLayout
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

from db_manager import DatabaseManager
from utils import format_money, add_months_jalali

class InstallmentPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        self.current_customer_id = None
        self.current_loan_id = None
        
        # --- مرحله ۱: ساخت تمام ویجت‌ها فقط یک بار ---
        self._create_widgets()
        # --- مرحله ۲: اتصال سیگنال‌ها فقط یک بار ---
        self._connect_signals()
        # --- مرحله ۳: چیدمان ویجت‌ها در لایه ---
        self.build_ui()

    def _create_widgets(self):
        """تمام ویجت‌های پنل با یک طراحی تمیز و مدرن برای هدر ساخته می‌شوند."""
        
        # --- بخش اصلی پنل (بدون تغییر) ---
        self.title_label = QLabel("پنل پرداخت اقساط")
        self.title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)

        self.customer_label = QLabel("انتخاب مشتری:")
        self.customer_combo = QComboBox()
        # ... (بقیه ویجت‌های اصلی بدون تغییر)

        self.loan_label = QLabel("انتخاب وام:")
        self.loan_combo = QComboBox()
        
        self.settle_loan_btn = QPushButton("تسویه کامل وام")
        # ... (بقیه دکمه‌ها بدون تغییر)
        self.delete_loan_btn = QPushButton("حذف وام")
        self.edit_loan_btn = QPushButton("اصلاح وام")
    
        # --- شروع بازطراحی کامل هدر وام ---
        self.loan_header_group = QGroupBox("اطلاعات کلی وام")
        self.loan_header_group.setFont(QFont("B Yekan", 11, QFont.Bold))
        self.loan_header_group.setStyleSheet("""
            QGroupBox {
                background-color: #f7f9fc; border: 1px solid #e0e6ed;
                border-radius: 8px; margin-top: 15px; padding-top: 25px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 5px 15px; background-color: #34495e;
                color: white; border-radius: 5px;
            }
            QLabel { font-size: 10pt; }
            QLabel#valueLabel { font-weight: bold; color: #2c3e50; }
            QLabel#importantValueLabel { font-weight: bold; font-size: 11pt; color: #c0392b; }
            QLabel#uuidLabel { font-family: monospace; color: #636e72; font-size: 8pt; }
        """)

        main_header_layout = QHBoxLayout(self.loan_header_group)
        main_header_layout.setSpacing(20)

        # ستون راست
        right_layout = QFormLayout()
        right_layout.setSpacing(10)
        self.lbl_total_amount = QLabel("..."); self.lbl_total_amount.setObjectName("valueLabel")
        self.lbl_installment_amount = QLabel("..."); self.lbl_installment_amount.setObjectName("valueLabel")
        self.lbl_interest_rate = QLabel("..."); self.lbl_interest_rate.setObjectName("valueLabel")
        self.lbl_loan_readable_id = QLabel("..."); self.lbl_loan_readable_id.setObjectName("valueLabel")
        self.lbl_loan_uuid = QLabel("..."); self.lbl_loan_uuid.setObjectName("uuidLabel") # <-- جدید
        
        right_layout.addRow("مبلغ کل وام:", self.lbl_total_amount)
        right_layout.addRow("قسط هر ماه:", self.lbl_installment_amount)
        right_layout.addRow("سود ماهانه:", self.lbl_interest_rate)
        right_layout.addRow("کد وام:", self.lbl_loan_readable_id)
        right_layout.addRow("UUID وام:", self.lbl_loan_uuid) # <-- جدید

        # ستون چپ
        left_layout = QFormLayout()
        left_layout.setSpacing(10)
        self.lbl_remaining_balance = QLabel("..."); self.lbl_remaining_balance.setObjectName("importantValueLabel")
        self.lbl_loan_term = QLabel("..."); self.lbl_loan_term.setObjectName("valueLabel")
        self.lbl_grant_date = QLabel("..."); self.lbl_grant_date.setObjectName("valueLabel")
        self.lbl_customer_readable_id = QLabel("..."); self.lbl_customer_readable_id.setObjectName("valueLabel")
        self.lbl_customer_uuid = QLabel("..."); self.lbl_customer_uuid.setObjectName("uuidLabel") # <-- جدید

        left_layout.addRow("<b>مانده کل وام:</b>", self.lbl_remaining_balance)
        left_layout.addRow("تعداد اقساط:", self.lbl_loan_term)
        left_layout.addRow("تاریخ پرداخت وام:", self.lbl_grant_date)
        left_layout.addRow("کد کاربر:", self.lbl_customer_readable_id)
        left_layout.addRow("Parent ID (UUID کاربر):", self.lbl_customer_uuid) # <-- جدید

        main_header_layout.addLayout(right_layout)
        main_header_layout.addLayout(left_layout)
        
        self.loan_header_group.setVisible(False)
        # --- پایان بازطراحی کامل هدر وام ---

        # --- جدول اقساط (بدون تغییر) ---
        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(6)
        self.installments_table.setHorizontalHeaderLabels(["کد قسط", "تاریخ سررسید", "مبلغ قسط", "مانده", "وضعیت", "عملیات"])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.installments_table.setFont(QFont("B Yekan", 10))
        self.installments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.installments_table.setSelectionMode(QTableWidget.SingleSelection)



    def _connect_signals(self):
        """اتصال سیگنال‌ها به اسلات‌ها فقط یک بار انجام می‌شود."""
        self.customer_combo.currentIndexChanged.connect(self.load_customer_loans)
        self.loan_combo.currentIndexChanged.connect(self.load_loan_installments)
        self.settle_loan_btn.clicked.connect(self.show_settlement_dialog)
        self.delete_loan_btn.clicked.connect(self.delete_loan_confirmation)
        self.edit_loan_btn.clicked.connect(self.show_edit_loan_dialog)

    def build_ui(self):
        """ویجت‌های از قبل ساخته شده را به درستی در لایه اصلی چیدمان می‌کند."""
        self.clear_layout(self.main_layout)

        # افزودن عنوان اصلی پنل
        self.main_layout.addWidget(self.title_label)
        
        # --- لایه انتخاب مشتری ---
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(self.customer_label)
        customer_layout.addWidget(self.customer_combo)
        self.main_layout.addLayout(customer_layout)

        # --- لایه انتخاب وام و دکمه‌های عملیاتی ---
        loan_layout = QHBoxLayout()
        loan_layout.addWidget(self.loan_label)
        loan_layout.addWidget(self.loan_combo, 1) # بخش بیشتر فضا را به کومبو باکس وام می‌دهد
        loan_layout.addWidget(self.edit_loan_btn)
        loan_layout.addWidget(self.settle_loan_btn)
        loan_layout.addWidget(self.delete_loan_btn)
        self.main_layout.addLayout(loan_layout)

        # افزودن گروه هدر اطلاعات وام
        self.main_layout.addWidget(self.loan_header_group)

        # افزودن جدول اقساط
        self.main_layout.addWidget(self.installments_table)

    def refresh_data(self):
        self.load_customers_to_combo()
        # بقیه موارد در cascade فراخوانی می‌شوند

    # ... (بقیه توابع کلاس بدون تغییر باقی می‌مانند) ...

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().setParent(None) # جدا کردن ویجت از لایه
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def load_customers_to_combo(self):
        # جلوگیری از فراخوانی‌های تودرتو هنگام پاک کردن
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.blockSignals(False)
        
        self.customer_combo.addItem("یک مشتری انتخاب کنید", None)
        customers = self.db_manager.get_all_customers()
        for customer_id, name in customers:
            self.customer_combo.addItem(name, customer_id)
            
    def load_customer_loans(self):
        # پاک کردن اطلاعات قبلی
        self.loan_combo.clear()
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)
        self.delete_loan_btn.setEnabled(False)
        self.edit_loan_btn.setEnabled(False)
        
        self.current_customer_id = self.customer_combo.currentData()
        
        if self.current_customer_id:
            loans = self.db_manager.get_customer_loans(self.current_customer_id)
            if loans:
                self.loan_combo.addItem("یک وام انتخاب کنید", None)
                for loan_id, amount, term, date in loans:
                    self.loan_combo.addItem(f"وام ID: {loan_id} - مبلغ {format_money(amount)} ({term} ماهه)", loan_id)

    def load_loan_installments(self):
        """اطلاعات هدر و لیست اقساط وام انتخاب شده را بارگذاری و نمایش می‌دهد."""
        # پاک کردن اطلاعات قبلی
        self.installments_table.setRowCount(0)
        self.loan_header_group.setVisible(False)
        self.current_loan_id = self.loan_combo.currentData()
        
        # غیرفعال کردن دکمه‌ها در ابتدا
        self.settle_loan_btn.setEnabled(False)
        self.delete_loan_btn.setEnabled(False)
        self.edit_loan_btn.setEnabled(False)

        if self.current_loan_id:
            # --- دریافت و نمایش اطلاعات هدر وام ---
            header_data = self.db_manager.get_loan_header_details(self.current_loan_id)
            if header_data:
                self.lbl_total_amount.setText(format_money(header_data.get('total_amount', 0)))
                self.lbl_remaining_balance.setText(format_money(header_data.get('remaining_balance', 0)))
                self.lbl_installment_amount.setText(format_money(header_data.get('installment_amount', 0)))
                self.lbl_loan_term.setText(f"{header_data.get('loan_term', 0)} ماه")
                self.lbl_interest_rate.setText(f"{header_data.get('interest_rate', 0)}%")
                self.lbl_grant_date.setText(str(header_data.get('grant_date', 'N/A')))
                
                # نمایش صحیح کدهای خوانا
                self.lbl_loan_readable_id.setText(header_data.get('loan_readable_id', 'N/A'))
                self.lbl_customer_readable_id.setText(header_data.get('customer_readable_id', 'N/A'))
                
                # نمایش UUID ها
                # شما می‌توانید این دو لیبل را نیز به UI اضافه کنید اگر می‌خواهید UUIDها هم نمایش داده شوند
                self.lbl_loan_uuid.setText(header_data.get('loan_uuid', 'N/A'))
                self.lbl_customer_uuid.setText(header_data.get('customer_uuid', 'N/A'))
                
                self.loan_header_group.setVisible(True)

            # --- فعال‌سازی دکمه‌ها بر اساس وضعیت وام ---
            is_fully_paid = self.db_manager.is_loan_fully_paid(self.current_loan_id)
            self.settle_loan_btn.setEnabled(not is_fully_paid)
            self.delete_loan_btn.setEnabled(True)
            has_paid = self.db_manager.has_paid_installments(self.current_loan_id)
            self.edit_loan_btn.setEnabled(not has_paid)

            # --- بارگذاری و نمایش لیست اقساط ---
            installments = self.db_manager.get_loan_installments(self.current_loan_id)
            if installments:
                self.installments_table.setRowCount(len(installments))
                for row, installment in enumerate(installments):
                    # باز کردن مقادیر از تاپل بازگشتی دیتابیس
                    installment_id, readable_id, due_date, amount_due, amount_paid, payment_date, status = installment
                    
                    remaining_amount = amount_due - (amount_paid or 0)
                    if remaining_amount < 0: remaining_amount = 0

                    # پر کردن جدول
                    self.installments_table.setItem(row, 0, QTableWidgetItem(str(readable_id)))
                    self.installments_table.setItem(row, 1, QTableWidgetItem(str(due_date)))
                    self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(amount_due)))
                    self.installments_table.setItem(row, 3, QTableWidgetItem(format_money(remaining_amount)))
                    self.installments_table.setItem(row, 4, QTableWidgetItem(str(status)))
                    
                    if not is_fully_paid and status != "PAID":
                        pay_btn = QPushButton("پرداخت قسط")
                        pay_btn.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; border-radius: 5px; padding: 5px;} QPushButton:hover { background-color: #27ae60; }")
                        pay_btn.clicked.connect(lambda _, inst_id=installment_id, rem_amount=remaining_amount: self.show_pay_dialog(inst_id, rem_amount))
                        self.installments_table.setCellWidget(row, 5, pay_btn)
            
    def show_settlement_dialog(self):
        if not self.current_loan_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک وام را انتخاب کنید.")
            return

        details = self.db_manager.get_loan_for_settlement(self.current_loan_id)
        if not details or not details.get('loan_grant_date'):
            QMessageBox.critical(self, "خطا", "اطلاعات وام یا تاریخ پرداخت آن یافت نشد.")
            return

        principal = details['amount']
        interest_rate = details['interest_rate']
        total_paid = details.get('total_paid') or 0
        loan_grant_date_str = details['loan_grant_date']
        
        loan_grant_date = jdatetime.datetime.strptime(loan_grant_date_str, '%Y/%m/%d').date()
        today = jdatetime.date.today()
        
        if today < loan_grant_date:
            months_passed = 0
        else:
            months_passed = (today.year - loan_grant_date.year) * 12 + (today.month - loan_grant_date.month)
            if today.day >= loan_grant_date.day:
                months_passed += 1
            elif today.day < loan_grant_date.day and months_passed == 0:
                 months_passed = 1
            if months_passed == 0 and today > loan_grant_date:
                months_passed = 1

        new_total_interest = principal * (interest_rate / 100) * months_passed
        new_total_loan_value = principal + new_total_interest
        settlement_amount = new_total_loan_value - total_paid

        if settlement_amount < 0: settlement_amount = 0

        dialog = QDialog(self)
        dialog.setWindowTitle("فرم تسویه کامل وام")
        # ... بقیه کد این تابع بدون تغییر است
        main_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        style_sheet = "QLabel { font-size: 13px; padding: 5px; } QLabel#title { font-size: 16px; font-weight: bold; color: #2c3e50; } QLabel#final_amount { font-size: 18px; font-weight: bold; color: #c0392b; padding: 10px; background-color: #f9e6e4; border-radius: 5px;} QComboBox, QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 5px; }"
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
        confirm_btn.clicked.connect(lambda: self.process_settlement(dialog, settlement_amount, cashbox_combo.currentData(), description_input.text(), new_total_loan_value))
        
        main_layout.addLayout(form_layout)
        main_layout.addWidget(confirm_btn, alignment=Qt.AlignCenter)

        dialog.exec_()
        
    def process_settlement(self, dialog, amount, cashbox_id, description, new_total_loan_value):
        if not cashbox_id:
            QMessageBox.warning(dialog, "خطا", "لطفا یک صندوق را انتخاب کنید.")
            return

        reply = QMessageBox.question(self, 'تایید تسویه', f"آیا از تسویه کامل این وام با مبلغ {format_money(amount)} مطمئن هستید؟", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            today_str = jdatetime.date.today().strftime('%Y/%m/%d')
            customer_name = self.customer_combo.currentText()
            trans_desc = f"تسویه وام مشتری {customer_name} - {description}"
            
            success = self.db_manager.settle_loan(
                self.current_loan_id, amount, cashbox_id, new_total_loan_value,
                self.current_customer_id, trans_desc, today_str
            )
            if success:
                QMessageBox.information(self, "موفقیت", "وام با موفقیت تسویه شد.")
                dialog.accept()
                self.load_loan_installments()
            else:
                QMessageBox.critical(self, "خطا", "خطا در عملیات تسویه وام.")

    def show_pay_dialog(self, installment_id, remaining_amount):
        dialog = QDialog(self)
        dialog.setWindowTitle("فرم پرداخت قسط")
        dialog.setMinimumWidth(450)
        style_sheet = "QDialog { background-color: #f8f9fa; } QLabel { font-size: 13px; padding-top: 5px; } QLabel#title { font-size: 16px; font-weight: bold; color: #343a40; margin-bottom: 10px; } QLabel#remaining_amount { font-size: 15px; font-weight: bold; color: #c0392b; padding: 10px; background-color: #f9e6e4; border-radius: 8px;} QLineEdit, QComboBox { padding: 10px; border: 1px solid #ced4da; border-radius: 8px; background-color: #ffffff; } QPushButton { font-size: 12px; font-weight: bold; padding: 10px 20px; border-radius: 8px; background-color: #28a745; color: white;} QPushButton:hover { background-color: #218838; }"
        dialog.setStyleSheet(style_sheet)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        title_label = QLabel("جزئیات پرداخت قسط", objectName="title")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        installment_details = self.db_manager.get_installment_details(installment_id)
        if installment_details:
            due_date = installment_details['due_date']
            amount_due = installment_details['amount_due']
            form_layout.addRow(QLabel("تاریخ سررسید قسط:"), QLabel(f"<b>{due_date}</b>"))
            form_layout.addRow(QLabel("مبلغ کل قسط:"), QLabel(f"<b>{format_money(amount_due)}</b>"))

        remaining_label = QLabel(f"<b>{format_money(remaining_amount)}</b>", objectName="remaining_amount")
        remaining_label.setAlignment(Qt.AlignCenter)
        form_layout.addRow(QLabel("مانده قابل پرداخت:"), remaining_label)
        
        amount_input = QLineEdit(str(int(remaining_amount)))
        form_layout.addRow("مبلغ پرداخت:", amount_input)

        cashbox_combo = QComboBox()
        cashboxes = self.db_manager.get_all_cash_boxes()
        for box_id, name, balance in cashboxes:
            cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)
        form_layout.addRow("واریز به صندوق:", cashbox_combo)
        
        description_input = QLineEdit()
        description_input.setPlaceholderText("اختیاری (مثال: پرداخت توسط همراه)")
        form_layout.addRow("شرح:", description_input)

        payment_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        form_layout.addRow("تاریخ پرداخت:", payment_date_input)

        pay_btn = QPushButton("ثبت پرداخت")
        pay_btn.setIcon(QIcon.fromTheme("emblem-ok"))
        pay_btn.clicked.connect(lambda: self.process_payment(
            dialog, installment_id, amount_input.text(), 
            cashbox_combo.currentData(), description_input.text(), 
            payment_date_input.text()
        ))
        
        main_layout.addLayout(form_layout)
        main_layout.addWidget(pay_btn, alignment=Qt.AlignCenter)
        
        dialog.exec_()
    
    def process_payment(self, dialog, installment_id, amount_str, cashbox_id, description, payment_date_str):
        today = jdatetime.date.today()
        try:
            payment_date = jdatetime.datetime.strptime(payment_date_str, '%Y/%m/%d').date()
            if payment_date > today:
                QMessageBox.warning(dialog, "خطای تاریخ", "تاریخ پرداخت نمی‌تواند در آینده باشد.")
                return
        except ValueError:
            QMessageBox.warning(dialog, "خطا", "فرمت تاریخ پرداخت صحیح نیست. لطفا از فرمت YYYY/MM/DD استفاده کنید.")
            return

        amount_str = amount_str.replace("،", "").replace("تومان", "").strip()
        try:
            amount = int(amount_str)
        except (ValueError, TypeError):
            QMessageBox.warning(dialog, "خطا", "لطفا مبلغ معتبر وارد کنید.")
            return

        if amount <= 0:
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت باید بیشتر از صفر باشد.")
            return

        installment_details = self.db_manager.get_installment_details(installment_id)
        if installment_details and amount > (installment_details['amount_due'] - installment_details['amount_paid']):
            QMessageBox.warning(dialog, "خطا", "مبلغ پرداخت بیشتر از مانده قسط است.")
            return

        customer_name = self.customer_combo.currentText()
        transaction_description = f"دریافت قسط از مشتری {customer_name}"
        if description:
            transaction_description += f" - {description}"
        
        success, message = self.db_manager.pay_installment(
            self.current_customer_id, installment_id, amount, 
            cashbox_id, transaction_description, payment_date_str
        )

        if success:
            QMessageBox.information(self, "موفقیت", "قسط با موفقیت پرداخت شد.")
            dialog.accept()
            self.load_loan_installments()
        else:
            QMessageBox.critical(self, "خطا", f"خطا در پرداخت قسط: {message}")

    def delete_loan_confirmation(self):
        if not self.current_loan_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک وام را برای حذف انتخاب کنید.")
            return

        reply = QMessageBox.question(self, 'تایید حذف وام', 
                                     "آیا از حذف کامل این وام و تمام سوابق آن مطمئن هستید؟\nاین عمل غیرقابل بازگشت است.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.db_manager.delete_loan_by_id(self.current_loan_id)
            if success:
                QMessageBox.information(self, "حذف موفق", "وام با موفقیت حذف شد.")
                self.load_customer_loans() 
            else:
                QMessageBox.critical(self, "خطا", f"خطا در حذف وام:\n{message}")

    def show_edit_loan_dialog(self):
        if not self.current_loan_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک وام را برای اصلاح انتخاب کنید.")
            return

        if self.db_manager.has_paid_installments(self.current_loan_id):
            QMessageBox.critical(self, "امکان اصلاح وجود ندارد", "این وام به دلیل داشتن اقساط پرداخت شده، قابل اصلاح نیست.")
            return

        dialog = LoanEditDialog(self.current_loan_id, self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_customer_loans()


# --- کلاس جدید برای دیالوگ ویرایش وام ---
class LoanEditDialog(QDialog):
    def __init__(self, loan_id, db_manager, parent=None):
        super().__init__(parent)
        self.loan_id = loan_id
        self.db_manager = db_manager
        
        self.old_loan_data = self.db_manager.get_loan_details_for_edit(self.loan_id)
        if not self.old_loan_data:
            self.reject()
            return
        
        self.setWindowTitle("فرم اصلاح وام")
        self.setMinimumWidth(500)
        self.build_ui()
        self.populate_data()

    def build_ui(self):
        self.main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.customer_combo = QComboBox()
        self.cashbox_combo = QComboBox()
        self.amount_input = QLineEdit()
        self.term_input = QLineEdit()
        self.interest_input = QLineEdit()
        self.start_date_input = QLineEdit()
        self.transaction_date_input = QLineEdit()
        self.description_input = QLineEdit()

        form_layout.addRow("مشتری:", self.customer_combo)
        form_layout.addRow("پرداخت از صندوق:", self.cashbox_combo)
        form_layout.addRow("مبلغ وام (تومان):", self.amount_input)
        form_layout.addRow("مدت بازپرداخت (ماه):", self.term_input)
        form_layout.addRow("سود ماهانه (درصد):", self.interest_input)
        form_layout.addRow("تاریخ پرداخت وام:", self.transaction_date_input)
        form_layout.addRow("تاریخ اولین قسط:", self.start_date_input)
        form_layout.addRow("شرح:", self.description_input)
        
        self.save_btn = QPushButton("ثبت تغییرات")
        self.save_btn.clicked.connect(self.process_update)
        
        self.main_layout.addLayout(form_layout)
        self.main_layout.addWidget(self.save_btn)

    def populate_data(self):
        customers = self.db_manager.get_all_customers()
        for cid, name in customers:
            self.customer_combo.addItem(name, cid)
        
        cashboxes = self.db_manager.get_all_cash_boxes()
        for bid, name, balance in cashboxes:
            self.cashbox_combo.addItem(f"{name} ({format_money(balance)})", bid)

        self.customer_combo.setCurrentIndex(self.customer_combo.findData(self.old_loan_data['customer_id']))
        self.cashbox_combo.setCurrentIndex(self.cashbox_combo.findData(self.old_loan_data['cash_box_id']))
        self.amount_input.setText(str(int(self.old_loan_data['amount'])))
        self.term_input.setText(str(self.old_loan_data['loan_term']))
        self.interest_input.setText(str(self.old_loan_data['interest_rate']))
        self.transaction_date_input.setText(self.old_loan_data['transaction_date'])
        self.start_date_input.setText(self.old_loan_data['start_date'])
        self.description_input.setText(self.old_loan_data['description'])

    def process_update(self):
        try:
            new_loan_data = {
                'customer_id': self.customer_combo.currentData(),
                'cash_box_id': self.cashbox_combo.currentData(),
                'amount': int(self.amount_input.text().replace("،", "")),
                'loan_term': int(self.term_input.text()),
                'interest_rate': float(self.interest_input.text()),
                'start_date': self.start_date_input.text(),
                'transaction_date': self.transaction_date_input.text(),
                'description': self.description_input.text()
            }
            
            total_interest = (new_loan_data['amount'] * (new_loan_data['interest_rate'] / 100)) * new_loan_data['loan_term']
            total_amount_with_interest = new_loan_data['amount'] + total_interest
            installment_amount = total_amount_with_interest / new_loan_data['loan_term']
            
            new_installments_data = []
            start_date_jalali = jdatetime.date(*map(int, new_loan_data['start_date'].split('/')))
            for i in range(new_loan_data['loan_term']):
                due_date_jalali = add_months_jalali(start_date_jalali, i)
                new_installments_data.append({
                    'due_date': due_date_jalali.strftime('%Y/%m/%d'),
                    'amount_due': installment_amount
                })

            success, message = self.db_manager.update_loan_and_installments(self.loan_id, self.old_loan_data, new_loan_data, new_installments_data)
            
            if success:
                QMessageBox.information(self, "موفقیت", "وام با موفقیت اصلاح شد.")
                self.accept()
            else:
                QMessageBox.critical(self, "خطا", f"خطا در اصلاح وام:\n{message}")

        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "خطای ورودی", f"لطفا تمام فیلدها را به درستی پر کنید.\n{e}")