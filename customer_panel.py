from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QAbstractItemView, QFrame,
    QComboBox
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QTimer
from db_manager import DatabaseManager
from utils import format_money

class CustomerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        
        # صفحه‌بندی
        self.current_page = 1
        self.page_size = 10
        self.total_pages = 1
        
        # طرح کلی
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. اول رابط کاربری (جدول و دکمه‌ها) را می‌سازیم
        self.setup_ui()
        
        # 2. بعد داده‌ها را لود می‌کنیم (رفع خطای AttributeError)
        self.refresh_data()

    def setup_ui(self):
        # --- نوار ابزار بالا (جستجو و افزودن) ---
        top_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد ملی یا شماره تماس...")
        self.search_input.textChanged.connect(self.on_search_changed)
        
        add_btn = QPushButton("افزودن مشتری جدید")
        add_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 5px; font-weight: bold;")
        add_btn.clicked.connect(lambda: self.show_customer_form(None))
        
        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(add_btn)
        
        self.layout.addLayout(top_bar)
        
        # --- جدول مشتریان ---
        self.table = QTableWidget()
        # ستون‌ها: کد، نام، کد ملی، تلفن، آدرس، جنسیت، عملیات
        self.table.setColumnCount(7) 
        self.table.setHorizontalHeaderLabels(["کد", "نام و نام خانوادگی", "کد ملی", "شماره تماس", "آدرس", "جنسیت", "عملیات"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # ستون عملیات بزرگتر باشد
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { border: 1px solid #ddd; border-radius: 5px; }")
        
        self.layout.addWidget(self.table)
        
        # --- نوار پایین (صفحه‌بندی) ---
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("قبلی")
        self.next_btn = QPushButton("بعدی")
        self.page_label = QLabel("صفحه 1 از 1")
        
        self.prev_btn.clicked.connect(self.go_prev_page)
        self.next_btn.clicked.connect(self.go_next_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        
        self.layout.addLayout(pagination_layout)

    def refresh_data(self):
        self.load_customers()

    def load_customers(self):
        search_query = self.search_input.text()
        customers = self.db_manager.get_customers_paginated(self.current_page, self.page_size, search_query)
        
        # اگر خروجی دیتابیس total_count دارد (برای صفحه‌بندی)
        # در غیر این صورت باید منطق count را جدا پیاده کنید. 
        # اینجا فرض ساده: اگر تعداد کمتر از page_size بود یعنی صفحه آخر است
        
        self.table.setRowCount(0)
        
        if customers:
            for row, customer in enumerate(customers):
                self.table.insertRow(row)
                
                self.table.setItem(row, 0, QTableWidgetItem(str(customer.get('Code', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(customer.get('FullName', '')))
                self.table.setItem(row, 2, QTableWidgetItem(customer.get('NationalID', '')))
                self.table.setItem(row, 3, QTableWidgetItem(customer.get('PhoneNumber', '')))
                self.table.setItem(row, 4, QTableWidgetItem(customer.get('Address', '')))
                self.table.setItem(row, 5, QTableWidgetItem(customer.get('Gender', '')))
                
                # --- ستون عملیات (دکمه‌ها) ---
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(5)
                
                # ۱. دکمه ویرایش
                edit_btn = QPushButton("ویرایش")
                edit_btn.setStyleSheet("background-color: #3498db; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
                edit_btn.clicked.connect(lambda _, c=customer: self.show_customer_form(c))
                actions_layout.addWidget(edit_btn)

                # ۲. دکمه تراکنش‌ها (بازگردانده شد)
                trans_btn = QPushButton("تراکنش‌ها")
                trans_btn.setStyleSheet("background-color: #f39c12; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
                trans_btn.clicked.connect(lambda _, c=customer: self.show_transactions(c))
                actions_layout.addWidget(trans_btn)

                # ۳. دکمه تبدیل به فروشگاه (منطق جدید)
                person_type = customer.get('PersonType', '')
                if person_type != 'تامین کننده':
                    store_btn = QPushButton("تبدیل به فروشگاه")
                    store_btn.setStyleSheet("background-color: #8e44ad; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
                    store_btn.clicked.connect(lambda _, c=customer: self.show_convert_to_store_dialog(c))
                    actions_layout.addWidget(store_btn)
                else:
                    lbl = QLabel("تامین کننده")
                    lbl.setStyleSheet("color: #27ae60; font-weight: bold; margin-left: 5px;")
                    actions_layout.addWidget(lbl)

                self.table.setCellWidget(row, 6, actions_widget)
                
        # بروزرسانی لیبل صفحه (ساده)
        self.page_label.setText(f"صفحه {self.current_page}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(len(customers) == self.page_size)

    def on_search_changed(self):
        self.current_page = 1
        self.refresh_data()

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_data()

    def go_next_page(self):
        self.current_page += 1
        self.refresh_data()

    def show_customer_form(self, customer_data=None):
        is_edit = customer_data is not None
        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش مشتری" if is_edit else "افزودن مشتری جدید")
        dialog.setMinimumWidth(450)

        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        name_input = QLineEdit()
        national_code_input = QLineEdit()
        phone_input = QLineEdit()
        gender_combo = QComboBox()
        gender_combo.addItems(["آقا", "خانم"])
        
        if is_edit:
            customer_id = customer_data['ID']
            name_input.setText(customer_data.get('FullName', ''))
            national_code_input.setText(customer_data.get('NationalID', ''))
            phone_input.setText(customer_data.get('PhoneNumber', ''))
            gender_combo.setCurrentText(customer_data.get('Gender', 'آقا'))
        
        form_layout.addRow("نام و نام خانوادگی:", name_input)
        form_layout.addRow("کد ملی:", national_code_input)
        form_layout.addRow("شماره تماس:", phone_input)
        form_layout.addRow("جنسیت:", gender_combo)
        
        save_btn = QPushButton("ثبت تغییرات" if is_edit else "ثبت مشتری")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px;")
        
        def on_save():
            name = name_input.text()
            national_code = national_code_input.text()
            phone = phone_input.text()
            gender = gender_combo.currentText()

            if not all([name, national_code, phone]):
                QMessageBox.warning(dialog, "خطا", "پر کردن نام، کد ملی و شماره تماس الزامی است.")
                return

            if is_edit:
                success = self.db_manager.update_customer(customer_id, name, national_code, phone, gender)
            else:
                success = self.db_manager.add_customer(name, national_code, phone, gender)
            
            if success:
                QMessageBox.information(self, "موفقیت", "عملیات با موفقیت انجام شد.")
                dialog.accept()
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطا", "خطا در ثبت اطلاعات.")

        save_btn.clicked.connect(on_save)
        layout.addLayout(form_layout)
        layout.addWidget(save_btn)
        dialog.exec_()

    def show_transactions(self, customer_data):
        # نمایش تاریخچه تراکنش‌ها
        # این متد می‌تواند یک دیالوگ جدید باز کند یا به پنل گزارش هدایت کند
        # فعلا یک پیام ساده یا منطق قبلی خودتان را قرار دهید
        QMessageBox.information(self, "تراکنش‌ها", f"مشاهده تراکنش‌های {customer_data['FullName']} (در حال پیاده‌سازی)")
        # اگر قبلا کدی برای این داشتید، اینجا قرار دهید.

    def show_convert_to_store_dialog(self, customer_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"ثبت فروشگاه برای {customer_data['FullName']}")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # فیلدهای ورودی
        store_name_input = QLineEdit(customer_data['FullName']) 
        store_address_input = QLineEdit(customer_data.get('Address', ''))
        store_phone_input = QLineEdit(customer_data.get('PhoneNumber', ''))
        
        form_layout.addRow("نام فروشگاه:", store_name_input)
        form_layout.addRow("آدرس فروشگاه:", store_address_input)
        form_layout.addRow("تلفن فروشگاه:", store_phone_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("تایید و ثبت نهایی")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px;")
        cancel_btn = QPushButton("انصراف")
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        
        def on_save():
            s_name = store_name_input.text()
            s_addr = store_address_input.text()
            s_phone = store_phone_input.text()
            
            if not s_name:
                QMessageBox.warning(dialog, "خطا", "نام فروشگاه الزامی است.")
                return
            
            success, msg = self.db_manager.convert_person_to_store(
                customer_data['ID'], s_name, s_addr, s_phone
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", "کاربر با موفقیت به عنوان فروشگاه ثبت شد.")
                dialog.accept()
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطا", f"خطا در ثبت اطلاعات:\n{msg}")

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()