# loan_panel.py (نسخه نهایی با ظاهر مدرن، چیدمان و دکمه اصلاح شده)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money, add_months_jalali ,normalize_numbers

class LoanPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.total_loan_amount_with_interest = 0
        self.build_ui()

    def build_ui(self):
        self.main_layout.setContentsMargins(25, 20, 25, 20)
        
        title_label = QLabel("ایجاد وام جدید")
        title_label.setFont(QFont("B Yekan", 22, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("margin-bottom: 15px; color: #2c3e50;")

        # --- Top Layout for Forms ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(25)

        # --- گروه اطلاعات مشتری و پرداخت (سمت راست) ---
        customer_group = QGroupBox("اطلاعات پرداخت و مشتری")
        customer_layout = QFormLayout(customer_group)
        # --- اصلاحیه ۱: تراز کردن لیبل‌ها برای رفع نامیزونی ---
        customer_layout.setLabelAlignment(Qt.AlignRight)
        
        self.customer_combo = QComboBox()
        self.store_combo = QComboBox() # <--- ویجت جدید: انتخاب فروشگاه
        self.cashbox_combo = QComboBox()
        self.transaction_date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        self.start_date_input = QLineEdit()
        self.description_input = QLineEdit()
        
        customer_layout.addRow("انتخاب مشتری:", self.customer_combo)
        customer_layout.addRow("انتخاب فروشگاه:", self.store_combo) # <--- افزودن به فرم
        customer_layout.addRow("پرداخت از صندوق:", self.cashbox_combo)
        customer_layout.addRow("تاریخ پرداخت وام:", self.transaction_date_input)
        customer_layout.addRow("تاریخ اولین قسط:", self.start_date_input)
        customer_layout.addRow("شرح:", self.description_input)
        
        # --- گروه پارامترهای مالی (سمت چپ) ---
        details_group = QGroupBox("پارامترهای مالی وام")
        details_layout = QFormLayout(details_group)
        # --- اصلاحیه ۱: تراز کردن لیبل‌ها برای رفع نامیزونی ---
        details_layout.setLabelAlignment(Qt.AlignRight)

        self.amount_input = QLineEdit()
        self.term_input = QLineEdit()
        self.interest_input = QLineEdit()
        self.penalty_input = QLineEdit("0")
        
        details_layout.addRow("مبلغ وام:", self.amount_input)
        details_layout.addRow("مدت بازپرداخت (ماه):", self.term_input)
        details_layout.addRow("سود ماهانه (%):", self.interest_input)
        details_layout.addRow("جریمه روزانه (%):", self.penalty_input)
        
        # چیدمان صحیح (چپ به راست در کد، راست به چپ در اجرا برای فارسی)
        top_layout.addWidget(details_group, 1) # گروه کوچک در سمت چپ
        top_layout.addWidget(customer_group, 2) # گروه بزرگ در سمت راست

        # --- Bottom Layout for Preview ---
        preview_group = QGroupBox("پیش‌نمایش اقساط")
        preview_layout = QVBoxLayout(preview_group)
        
        self.summary_label = QLabel("اطلاعات را برای محاسبه وارد کنید.")
        self.summary_label.setStyleSheet("""
            QLabel {
                font-size: 11pt; padding: 12px;
                background-color: #e9ecef; border-radius: 8px;
                color: #495057;
            }
        """)
        self.summary_label.setAlignment(Qt.AlignCenter)
        
        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(2)
        self.installments_table.setHorizontalHeaderLabels(["تاریخ سررسید", "مبلغ قسط"])
        self.installments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        preview_layout.addWidget(self.summary_label)
        preview_layout.addWidget(self.installments_table)
        
        # --- Save Button ---
        self.save_btn = QPushButton(" پرداخت و ثبت نهایی وام")
        self.save_btn.setFont(QFont("B Yekan", 12, QFont.Bold))
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setIcon(QIcon.fromTheme("document-save"))
        
        # --- اصلاحیه ۲: رنگی کردن دکمه ثبت وام ---
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; /* رنگ سبز */
                color: white;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2ecc71; /* کمی روشن‌تر */
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)

        # --- Assemble Layouts ---
        self.main_layout.addWidget(title_label)
        self.main_layout.addLayout(top_layout)
        self.main_layout.addWidget(preview_group)
        self.main_layout.addWidget(self.save_btn)

        # --- Connect Signals ---
        self.amount_input.textChanged.connect(self._format_amount_input)
        self.term_input.textChanged.connect(self.calculate_installments)
        self.interest_input.textChanged.connect(self.calculate_installments)
        self.start_date_input.textChanged.connect(self.calculate_installments)
        self.save_btn.clicked.connect(self.save_loan)

        # --- Initial Data Load ---
        self.refresh_data()

    # --- بقیه توابع کلاس (منطق برنامه) بدون هیچ تغییری باقی می‌مانند ---

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

    def refresh_data(self):
        self.load_customers_to_combo()
        self.load_cashboxes_to_combo()
        self.load_stores_to_combo() # <--- لود کردن فروشگاه‌ها
        self.amount_input.clear()
        self.term_input.clear()
        self.interest_input.clear()
        self.penalty_input.setText("0")
        self.start_date_input.clear()
        self.description_input.clear()
        self.summary_label.setText("اطلاعات را برای محاسبه وارد کنید.")
        self.installments_table.setRowCount(0)

    def load_stores_to_combo(self):
            self.store_combo.clear()
            # فرض بر این است که تابعی برای گرفتن لیست فروشگاه‌ها در db_manager داریم
            # یا می‌توانیم یک کوئری مستقیم بزنیم. برای تمیزی کار، فرض می‌کنیم متد get_all_stores داریم
            # اما چون هنوز نداریم، اینجا یک کوئری مستقیم می‌زنیم یا بعدا به db_manager اضافه می‌کنیم
            # فعلا از طریق db_manager.execute_query لیست را می‌گیریم
            query = "SELECT id, storename FROM [demodeln_Pezhvak].[Stores] WHERE isactive = 1"
            stores = self.db_manager._execute_query(query, fetch='all')
            
            self.store_combo.addItem("یک فروشگاه انتخاب کنید...", None)
            if stores:
                for store in stores:
                    self.store_combo.addItem(store['storename'], store['id'])


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
                store_id = self.store_combo.currentData() # <--- دریافت ID فروشگاه
                fund_id = self.cashbox_combo.currentData()
                
                # --- اصلاحیه ۱: نرمالایز کردن تمامی ورودی‌های عددی (برای اطمینان) ---
                
                amount_str = self.amount_input.text().replace(",", "")
                normalized_amount_str = normalize_numbers(amount_str)
                amount = int(normalized_amount_str)
                
                term_str = self.term_input.text()
                normalized_term_str = normalize_numbers(term_str)
                loan_term = int(normalized_term_str)
                
                interest_str = self.interest_input.text()
                normalized_interest_str = normalize_numbers(interest_str)
                interest_rate = float(normalized_interest_str)
                
                penalty_rate_text = self.penalty_input.text()
                # اطمینان از تبدیل صحیح ۰٫۰۲ به 0.02
                normalized_penalty_rate_text = normalize_numbers(penalty_rate_text).strip() 
                penalty_rate = float(normalized_penalty_rate_text or 0)

                # --- اصلاحیه ۲: نرمالایز کردن تاریخ‌ها برای ذخیره در دیتابیس ---
                start_date_raw = self.start_date_input.text() 
                start_date = normalize_numbers(start_date_raw) # <-- اعمال نرمالایز به تاریخ اولین قسط
                
                loan_date_raw = self.transaction_date_input.text()
                loan_date = normalize_numbers(loan_date_raw) # <-- اعمال نرمالایز به تاریخ پرداخت وام
                
                description = self.description_input.text() or f"پرداخت وام به {self.customer_combo.currentText()}"

                if not all([person_id, store_id, fund_id, amount > 0, loan_term > 0, start_date, loan_date]):
                    QMessageBox.warning(self, "خطای ورودی", "لطفا مشتری، فروشگاه، صندوق و مقادیر مالی را پر کنید.")
                    return

                installments_data = []
                installment_amount = self.total_loan_amount_with_interest / loan_term
                
                # استفاده از start_date نرمالایز شده برای تبدیل به jdatetime
                start_date_jalali = jdatetime.date(*map(int, start_date.split('/')))
                for i in range(loan_term):
                    due_date_jalali = add_months_jalali(start_date_jalali, i)
                    installments_data.append({
                        # نرمالایز کردن تاریخ‌های اقساط قبل از ذخیره در loan_data
                        'due_date': normalize_numbers(due_date_jalali.strftime('%Y/%m/%d')), 
                        'amount_due': installment_amount
                    })
                
                end_date = installments_data[-1]['due_date'] if installments_data else start_date

                loan_data = {
                    'person_id': person_id, 'fund_id': fund_id, 'amount': amount,
                    'store_id': store_id, # <--- ارسال store_id به دیتابیس منیجر
                    'loan_term': loan_term, 'interest_rate': interest_rate,
                    'penalty_rate': penalty_rate,
                    'loan_date': loan_date, # <-- استفاده از تاریخ نرمالایز شده
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





