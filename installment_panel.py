# installment_panel.py (نسخه نهایی و اصلاح شده)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout ,QAbstractItemView ,QDialog , QFrame
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
        
        # اینجا لیست وضعیت‌ها را نگه می‌داریم
        self.status_map = {} 
        
        self.current_customer_id = None
        self.current_loan_id = None
        
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        # --- استایل‌ها ---
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

        # --- بخش بالایی: انتخاب مشتری و وام ---
        top_layout = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.loan_combo = QComboBox()
        self.settle_loan_btn = QPushButton("تسویه کامل وام")
        self.settle_loan_btn.setEnabled(False)
        self.settle_loan_btn.setStyleSheet("background-color: #e67e22; color: white; border-radius: 5px; padding: 5px; font-weight: bold;")
        
        
        self.delete_loan_btn = QPushButton("حذف وام (اصلاح)")
        self.delete_loan_btn.setEnabled(False)
        self.delete_loan_btn.setStyleSheet("background-color: #c0392b; color: white; border-radius: 5px; padding: 5px; font-weight: bold;")
        self.delete_loan_btn.clicked.connect(self.delete_current_loan)
        
        
        top_layout.addWidget(QLabel("انتخاب مشتری:"))
        top_layout.addWidget(self.customer_combo, 1)
        top_layout.addWidget(QLabel("انتخاب وام:"))
        top_layout.addWidget(self.loan_combo, 2)
        top_layout.addWidget(self.settle_loan_btn)
        top_layout.addWidget(self.delete_loan_btn) # افزودن دکمه به لایوت


        # --- بخش هدر: خلاصه وضعیت وام ---
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
        self.lbl_total_penalty.setStyleSheet("color: #c0392b;")

        header_grid.addWidget(QLabel("<b>مشتری:</b>"), 0, 0); header_grid.addWidget(self.lbl_person_name, 0, 1)
        header_grid.addWidget(QLabel("<b>کد وام:</b>"), 0, 2); header_grid.addWidget(self.lbl_loan_code, 0, 3)
        header_grid.addWidget(QLabel("<b>مبلغ کل وام:</b>"), 1, 0); header_grid.addWidget(self.lbl_total_amount, 1, 1)
        header_grid.addWidget(QLabel("<b>مجموع باقیمانده:</b>"), 1, 2); header_grid.addWidget(self.lbl_remaining_balance, 1, 3)
        header_grid.addWidget(QLabel("<b>مجموع جریمه:</b>"), 1, 4); header_grid.addWidget(self.lbl_total_penalty, 1, 5)        
        header_grid.addWidget(QLabel("<b>مبلغ هر قسط:</b>"), 2, 0); header_grid.addWidget(self.lbl_installment_amount, 2, 1)
        header_grid.addWidget(QLabel("<b>تعداد اقساط:</b>"), 2, 2); header_grid.addWidget(self.lbl_loan_term, 2, 3)
        header_grid.setColumnStretch(1, 1); header_grid.setColumnStretch(3, 1)

        # --- جدول اقساط ---
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

        # --- اتصالات (Signals) ---
        self.customer_combo.currentIndexChanged.connect(self.load_customer_loans)
        self.loan_combo.currentIndexChanged.connect(self.load_loan_installments)
        self.settle_loan_btn.clicked.connect(self.show_settlement_dialog)

    def refresh_data(self):
        # 1. خواندن نام وضعیت‌ها از دیتابیس (جدول categories)
        # ما دنبال رکوردهایی هستیم که PID آنها 'installmentstatus' باشد
        self.status_map = self.db_manager.get_category_map('installmentstatus')
        
        # اگر دیتابیس خالی بود، حداقل چند مورد پیش‌فرض داشته باشیم که ارور ندهد
        if not self.status_map:
            self.status_map = {
                30: "موعد نرسیده",
                31: "سررسید امروز",
                32: "پرداخت کامل",
                36: "تسویه شده"
            }

        self.load_customers_to_combo()

    def clear_loan_data(self):
        self.loan_header_group.setVisible(False)
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)
        self.delete_loan_btn.setEnabled(False) # غیرفعال کردن دکمه حذف

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
        person_id = self.customer_combo.currentData()
        self.loan_combo.clear()
        
        if not person_id:
            return

        loans = self.db_manager.get_customer_loans(person_id)
        
        if loans:
            for loan in loans:
                # --- اصلاح: استفاده از نام ستون‌ها (دیکشنری) به جای اعداد ---
                # ستون‌های کوئری: ID, Code, Amount, LoanTerm
                
                try:
                    # حالت دیکشنری (روش صحیح)
                    l_id = loan['ID']
                    l_code = loan['Code']
                    l_amount = loan['Amount']
                    l_term = loan['LoanTerm']
                except (TypeError, KeyError):
                    # حالت تاپل (پشتیبان برای شرایط خاص)
                    l_id = loan[0]
                    l_code = loan[1]
                    l_amount = loan[2]
                    l_term = loan[3]

                display_text = f"وام {l_code} - مبلغ {format_money(l_amount)} ({l_term} ماهه)"
                self.loan_combo.addItem(display_text, l_id)

    def clear_loan_data(self):
        self.loan_header_group.setVisible(False)
        self.installments_table.setRowCount(0)
        self.settle_loan_btn.setEnabled(False)

    def load_loan_installments(self):
        self.current_loan_id = self.loan_combo.currentData()
        if not self.current_loan_id:
            self.clear_loan_data()
            return

        # 1. آپدیت وضعیت اقساط (اختیاری: اگر اسکریپت خودکار دارید این خط را کامنت کنید)
        # self.db_manager.update_installment_statuses()

        # 2. دریافت اطلاعات هدر وام
        header_data = self.db_manager.get_loan_header_details(self.current_loan_id)
        if header_data:
            self.lbl_person_name.setText(header_data.get('person_name', 'N/A'))
            self.lbl_loan_code.setText(str(header_data.get('loan_code', 'N/A')))
            self.lbl_total_amount.setText(format_money(header_data.get('total_amount', 0)))
            self.lbl_installment_amount.setText(format_money(header_data.get('installment_amount', 0)))
            self.lbl_loan_term.setText(f"{header_data.get('loan_term', 0)} ماه")
            self.loan_header_group.setVisible(True)
            self.settle_loan_btn.setEnabled(True)
            self.delete_loan_btn.setEnabled(True)

        # 3. دریافت لیست اقساط
        installments = self.db_manager.get_loan_installments(self.current_loan_id)
        self.installments_table.setRowCount(0)
        
        total_payment_remain = 0
        total_penalty_amount = 0

        if installments:
            for row, inst in enumerate(installments):
                self.installments_table.insertRow(row)
                
                # خواندن مقادیر
                due_amount = inst.get('DueAmount') or 0
                paid_amount = inst.get('PaidAmount') or 0
                penalty_amount = inst.get('PenaltyAmount') or 0
                payment_remain = inst.get('PaymentRemain') or 0 
                code = inst.get('Code', 'N/A')
                due_date = inst.get('DueDate', 'N/A')

                # --- تعیین وضعیت ---
                try:
                    status_code = int(inst.get('Status', 30))
                except:
                    status_code = 30
                
                status_text = self.status_map.get(status_code, str(status_code))

                # --- پر کردن ستون‌های جدول ---
                self.installments_table.setItem(row, 0, QTableWidgetItem(str(code)))
                self.installments_table.setItem(row, 1, QTableWidgetItem(str(due_date)))
                self.installments_table.setItem(row, 2, QTableWidgetItem(format_money(due_amount)))
                self.installments_table.setItem(row, 3, QTableWidgetItem(format_money(paid_amount)))
                
                penalty_amount_item = QTableWidgetItem(format_money(penalty_amount))
                if penalty_amount > 0:
                    penalty_amount_item.setForeground(QColor("#c0392b"))
                self.installments_table.setItem(row, 4, penalty_amount_item)
                
                self.installments_table.setItem(row, 5, QTableWidgetItem(format_money(payment_remain)))
                
                # --- ساخت آیتم وضعیت (رفع خطا اینجاست) ---
                status_item = QTableWidgetItem(status_text)
                
                # رنگ‌بندی
                if status_code in [32, 35, 36]: # سبز
                    status_item.setForeground(QColor("#27ae60"))
                elif status_code in [33, 34]: # نارنجی
                    status_item.setForeground(QColor("#f39c12"))
                elif status_code == 31: # آبی
                    status_item.setForeground(QColor("#2980b9"))
                elif status_code == 37: # زرد تیره
                    status_item.setForeground(QColor("#d35400"))
                elif status_code in [38, 39, 40]: # قرمز
                    status_item.setForeground(QColor("#c0392b"))
                    status_item.setFont(QFont("B Yekan", 10, QFont.Bold))
                
                # حالا که متغیر تعریف شده، ست می‌شود
                self.installments_table.setItem(row, 6, status_item)

                # --- دکمه‌های عملیاتی (پرداخت و سابقه) ---
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(5)

                # 1. دکمه پرداخت (اگر تسویه نشده باشد)
                if status_code not in [32, 35, 36]:
                    pay_btn = QPushButton("پرداخت")
                    pay_btn.setStyleSheet("background-color: #27ae60; color: white; border-radius: 3px; padding: 2px 8px;")
                    # کپی دیکشنری برای جلوگیری از تغییر در لامبدا
                    inst_safe = inst.copy()
                    inst_safe['TotalRemain'] = payment_remain
                    pay_btn.clicked.connect(lambda _, x=inst_safe: self.show_pay_dialog(x))
                    actions_layout.addWidget(pay_btn)
                
                # 2. دکمه سابقه (همیشه فعال)
                history_btn = QPushButton("سابقه")
                history_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 3px; padding: 2px 8px;")
                history_btn.clicked.connect(lambda _, i_id=inst['ID']: self.show_history_dialog(i_id))
                actions_layout.addWidget(history_btn)

                self.installments_table.setCellWidget(row, 7, actions_widget)
                
                total_payment_remain += payment_remain
                total_penalty_amount += penalty_amount

        self.lbl_remaining_balance.setText(format_money(total_payment_remain))
        self.lbl_total_penalty.setText(format_money(total_penalty_amount))

    # --- تابع نمایش دیالوگ تسویه وام (بدون تغییر) ---
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

        dialog = QDialog(self)
        dialog.setWindowTitle("فرم تسویه کامل وام")
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet("""
            QDialog { background-color: #f9fafb; }
            QGroupBox { border: 1px solid #dfe6e9; background-color: #ffffff; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 5px 15px; background-color: #2980b9; color: white; border-radius: 5px; font-weight: bold; }
        """)
        main_layout = QVBoxLayout(dialog)

        calc_group = QGroupBox("جزئیات محاسبه مبلغ تسویه")
        calc_layout = QFormLayout(calc_group)
        calc_layout.addRow(QLabel("<b>اصل مبلغ وام:</b>"), QLabel(f"{format_money(principal)}"))
        calc_layout.addRow(QLabel("<b>سود ماهانه:</b>"), QLabel(f"{interest_rate}%"))
        calc_layout.addRow(QLabel("<b>تعداد ماه‌های محاسبه شده:</b>"), QLabel(f"{months_passed} ماه"))
        calc_layout.addRow(QLabel("<b>سود محاسبه شده جدید:</b><br/>(اصل وام × سود × ماه‌ها)"), QLabel(f"<b>{format_money(new_total_interest)}</b>"))
        calc_layout.addRow(QLabel("<b>مبلغ کل جدید:</b><br/>(اصل وام + سود جدید)"), QLabel(f"<b>{format_money(new_total_loan_value)}</b>"))
        calc_layout.addRow(QLabel("<b>مجموع مبالغ پرداخت شده:</b>"), QLabel(f"<b style='color:#27ae60;'>- {format_money(total_paid)}</b>"))

        final_group = QGroupBox("اطلاعات پرداخت نهایی")
        final_layout = QFormLayout(final_group)
        cashbox_combo = QComboBox()
        cashboxes = self.db_manager.get_all_cash_boxes()
        if cashboxes:
            for box_id, name, _ in cashboxes:
                cashbox_combo.addItem(name, box_id)
        final_layout.addRow(QLabel("<b>مبلغ نهایی برای تسویه:</b>"), QLabel(f"<b style='color:#c0392b; font-size:14pt;'>{format_money(settlement_amount)}</b>"))
        final_layout.addRow("واریز به صندوق:", cashbox_combo)

        save_btn = QPushButton(" تایید و تسویه نهایی")
        save_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        save_btn.setStyleSheet("background-color: #27ae60; color: white; border-radius: 8px; padding: 10px;")
        save_btn.clicked.connect(lambda: self.process_settlement(dialog, cashbox_combo.currentData(), settlement_amount))

        main_layout.addWidget(calc_group)
        main_layout.addWidget(final_group)
        main_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        dialog.exec_()

    # --- تابع پردازش تسویه (بدون تغییر) ---
    def process_settlement(self, dialog, fund_id, settlement_amount):
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

    # --- تابع نمایش دیالوگ پرداخت قسط (بدون تغییر) ---
    def show_pay_dialog(self, installment_data):
        # --- 1. استخراج داده‌ها ---
        try:
            inst_id = installment_data['ID']
            due_date = str(installment_data.get('DueDate', '-'))
            
            due_amount = float(installment_data.get('DueAmount', 0))
            penalty = float(installment_data.get('PenaltyAmount', 0))
            paid_so_far = float(installment_data.get('PaidAmount', 0))
            remain = float(installment_data.get('PaymentRemain', 0))
            status_code = int(installment_data.get('Status', 30))
        except (TypeError, KeyError, IndexError):
            QMessageBox.critical(self, "خطا", "اطلاعات قسط ناقص است.")
            return

        status_map = {
            30: "موعد نرسیده", 31: "سررسید امروز", 32: "تکمیل شده",
            33: "پرداخت ناقص", 34: "ناقص (با جریمه)", 35: "تاخیر",
            36: "جریمه شده", 37: "معوق (تنفس)", 38: "معوق", 
            39: "مشکوک‌الوصول", 40: "حقوقی"
        }
        status_text = status_map.get(status_code, "نامشخص")

        # --- 2. تنظیمات پنجره و استایل (CSS) ---
        dialog = QDialog(self)
        dialog.setWindowTitle(f"پرداخت قسط - {due_date}")
        dialog.setMinimumWidth(480)
        dialog.setStyleSheet("""
            QDialog { background-color: #fdfefe; }
            QLabel { font-family: 'B Yekan'; font-size: 13px; color: #34495e; }
            QLineEdit, QComboBox { 
                padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px; background: white; 
                font-family: 'B Yekan'; font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; }
            QPushButton { font-family: 'B Yekan'; font-weight: bold; border-radius: 5px; padding: 10px; }
            QGroupBox { 
                background-color: #ecf0f1; border-radius: 8px; border: 1px solid #bdc3c7; 
                margin-top: 10px; padding-top: 15px; font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        # --- 3. کارت اطلاعات (بالا) ---
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame { background-color: #f4f6f7; border-radius: 8px; border: 1px solid #d5dbdb; }
            QLabel#ValueLabel { font-weight: bold; font-size: 14px; color: #2c3e50; }
            QLabel#RedLabel { font-weight: bold; font-size: 14px; color: #c0392b; }
            QLabel#GreenLabel { font-weight: bold; font-size: 14px; color: #27ae60; }
        """)
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setVerticalSpacing(12)

        # ردیف 1
        info_layout.addWidget(QLabel("تاریخ سررسید:"), 0, 0)
        info_layout.addWidget(QLabel(due_date, objectName="ValueLabel"), 0, 1)
        info_layout.addWidget(QLabel("وضعیت:"), 0, 2)
        lbl_status = QLabel(status_text, objectName="ValueLabel")
        if status_code in [36, 38, 39, 40]: lbl_status.setStyleSheet("color: #c0392b")
        info_layout.addWidget(lbl_status, 0, 3)

        # خط جداکننده
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(line, 1, 0, 1, 4)

        # ردیف 2
        info_layout.addWidget(QLabel("مبلغ قسط:"), 2, 0)
        info_layout.addWidget(QLabel(format_money(due_amount), objectName="ValueLabel"), 2, 1)
        info_layout.addWidget(QLabel("جریمه:"), 2, 2)
        lbl_penalty = QLabel(format_money(penalty), objectName="RedLabel" if penalty > 0 else "ValueLabel")
        info_layout.addWidget(lbl_penalty, 2, 3)

        # ردیف 3
        info_layout.addWidget(QLabel("پرداخت شده:"), 3, 0)
        info_layout.addWidget(QLabel(format_money(paid_so_far), objectName="GreenLabel"), 3, 1)
        info_layout.addWidget(QLabel("مانده نهایی:"), 3, 2)
        lbl_remain = QLabel(format_money(remain), objectName="RedLabel")
        lbl_remain.setFont(QFont("B Yekan", 16, QFont.Bold))
        info_layout.addWidget(lbl_remain, 3, 3)

        main_layout.addWidget(info_frame)

        # --- 4. فرم پرداخت (پایین) ---
        # نکته مهم: تعریف متغیرها با self برای دسترسی در تابع process_payment
        form_group = QGroupBox("ثبت تراکنش جدید")
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(15, 20, 15, 15)
        form_layout.setSpacing(10)

        # انتخاب صندوق
        self.pay_fund_combo = QComboBox()
        funds = self.db_manager.get_all_cash_boxes()
        self.pay_fund_combo.addItem("--- انتخاب صندوق ---", None)
        if funds:
            for f in funds:
                try: f_id=f['ID']; f_name=f['Name']; f_inv=f['Inventory']
                except: f_id=f[0]; f_name=f[1]; f_inv=f[2]
                self.pay_fund_combo.addItem(f"{f_name} (موجودی: {format_money(f_inv)})", f_id)
        if self.pay_fund_combo.count() > 1: self.pay_fund_combo.setCurrentIndex(1)

        # مبلغ
        self.pay_amount_input = QLineEdit(str(int(remain)))
        self.pay_amount_input.setPlaceholderText("مبلغ به تومان")
        self.pay_amount_input.textChanged.connect(lambda: self.format_price_input(self.pay_amount_input))
        self.format_price_input(self.pay_amount_input)

        # تاریخ و شرح
        self.pay_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        self.pay_desc_input = QLineEdit()
        self.pay_desc_input.setPlaceholderText("توضیحات (اختیاری)")

        form_layout.addRow("صندوق:", self.pay_fund_combo)
        form_layout.addRow("مبلغ پرداخت:", self.pay_amount_input)
        form_layout.addRow("تاریخ:", self.pay_date_input)
        form_layout.addRow("شرح:", self.pay_desc_input)

        main_layout.addWidget(form_group)

        # --- 5. دکمه‌ها ---
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("ثبت و ذخیره")
        save_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        save_btn.setCursor(Qt.PointingHandCursor)
        # اتصال به تابع پردازش با ارسال ID و Dialog
        save_btn.clicked.connect(lambda: self.process_payment(inst_id, dialog))
        
        cancel_btn = QPushButton("انصراف")
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; border: none; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        dialog.exec_()

    def process_payment(self, inst_id, dialog):
        """منطق ذخیره پرداخت که جدا شده تا کد تمیزتر باشد."""
        selected_fund_id = self.pay_fund_combo.currentData()
        raw_amount = self.pay_amount_input.text().replace(',', '').strip()
        pay_date = self.pay_date_input.text().strip()
        description = self.pay_desc_input.text().strip()

        # اعتبارسنجی
        errors = []
        if not selected_fund_id: errors.append("- لطفاً یک صندوق را انتخاب کنید.")
        if not raw_amount or not raw_amount.isdigit() or float(raw_amount) <= 0:
            errors.append("- مبلغ وارد شده صحیح نیست.")
        if not pay_date: errors.append("- تاریخ پرداخت الزامی است.")

        if errors:
            QMessageBox.warning(dialog, "اطلاعات ناقص", "\n".join(errors))
            return

        # ارسال به دیتابیس
        try:
            success, msg = self.db_manager.pay_installment(
                inst_id, float(raw_amount), pay_date, selected_fund_id, description
            )
            
            if success:
                QMessageBox.information(dialog, "موفقیت", "پرداخت با موفقیت ثبت شد.")
                dialog.accept()
                self.load_loan_installments() # رفرش لیست اقساط
            else:
                QMessageBox.critical(dialog, "خطا", f"خطا در ثبت: {msg}")
        
        except Exception as e:
            QMessageBox.critical(dialog, "خطا", f"خطای سیستمی: {str(e)}")

    # تابع کمکی فرمت پول (اگر در کلاس نیست، اضافه کنید)
    def format_price_input(self, line_edit):
        text = line_edit.text().replace(',', '')
        if text.isdigit():
            formatted = f"{int(text):,}"
            if line_edit.text() != formatted:
                line_edit.blockSignals(True)
                line_edit.setText(formatted)
                line_edit.blockSignals(False)

    def delete_current_loan(self):
            if not self.current_loan_id: return

            # هشدار جدی به کاربر
            reply = QMessageBox.question(
                self, "تایید حذف",
                "آیا مطمئن هستید که می‌خواهید این وام را حذف کنید؟\n\n"
                "این عملیات غیرقابل بازگشت است و تمام اقساط و سوابق این وام پاک خواهد شد.\n"
                "موجودی کسر شده از صندوق نیز بازگردانده می‌شود.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                success, message = self.db_manager.delete_loan_fully(self.current_loan_id)
                if success:
                    QMessageBox.information(self, "موفقیت", "وام با موفقیت حذف شد.")
                    # رفرش کردن صفحه
                    self.load_customer_loans()
                else:
                    QMessageBox.critical(self, "خطا", f"حذف انجام نشد:\n{message}")


    def show_history_dialog(self, installment_id):
            dialog = QDialog(self)
            dialog.setWindowTitle("تاریخچه پرداخت‌های قسط")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout(dialog)
            
            # جدول لیست پرداخت‌ها
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["تاریخ پرداخت", "مبلغ", "شرح", "عملیات"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            # دریافت داده‌ها
            payments = self.db_manager.get_installment_payments(installment_id)
            
            table.setRowCount(0)
            if payments:
                for row, pay in enumerate(payments):
                    table.insertRow(row)
                    table.setItem(row, 0, QTableWidgetItem(str(pay['PaymentDate'])))
                    table.setItem(row, 1, QTableWidgetItem(format_money(pay['Amount'])))
                    table.setItem(row, 2, QTableWidgetItem(pay['Description']))
                    
                    # دکمه حذف
                    del_btn = QPushButton("حذف (اصلاح)")
                    del_btn.setStyleSheet("background-color: #c0392b; color: white; border-radius: 3px;")
                    del_btn.clicked.connect(lambda _, p_id=pay['ID']: self.delete_payment_transaction(p_id, dialog))
                    table.setCellWidget(row, 3, del_btn)
            else:
                layout.addWidget(QLabel("هیچ پرداختی برای این قسط ثبت نشده است."))

            layout.addWidget(table)
            
            close_btn = QPushButton("بستن")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.exec_()

    def delete_payment_transaction(self, payment_id, dialog):
        reply = QMessageBox.question(
            dialog, "تایید حذف", 
            "آیا مطمئن هستید که می‌خواهید این تراکنش پرداخت را حذف کنید؟\n\n"
            "مبلغ به صندوق کسر شده برمی‌گردد و وضعیت قسط به حالت قبل باز می‌گردد.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, msg = self.db_manager.delete_installment_payment(payment_id)
            if success:
                QMessageBox.information(dialog, "موفقیت", "تراکنش با موفقیت حذف شد.")
                dialog.accept() # بستن دیالوگ تاریخچه
                self.load_loan_installments() # رفرش کردن جدول اصلی اقساط
            else:
                QMessageBox.critical(dialog, "خطا", f"خطا در حذف:\n{msg}")





