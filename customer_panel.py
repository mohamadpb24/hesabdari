from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from db_manager import DatabaseManager
from utils import format_money

class CustomerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # We'll call a method to build the UI to keep __init__ clean
        self.build_ui()

    def build_ui(self):
        self.clear_layout(self.main_layout)
        
        # Title and Add Button
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت مشتریان")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        add_customer_btn = QPushButton("افزودن مشتری جدید")
        add_customer_btn.setFixedSize(200, 40)
        add_customer_btn.setFont(QFont("B Yekan", 12))
        add_customer_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2ecc71; 
                color: white; 
                border-radius: 10px; 
                padding: 5px; 
            }
            QPushButton:hover { 
                background-color: #27ae60; 
            }
        """)
        add_customer_btn.clicked.connect(lambda: self.show_add_customer_form())
        
        header_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        header_layout.addWidget(add_customer_btn, alignment=Qt.AlignRight)
        
        # Search Box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد ملی یا شماره تماس...")
        self.search_input.setFont(QFont("B Yekan", 10))
        self.search_input.setStyleSheet("""
            QLineEdit { 
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px; 
            }
        """)
        self.search_input.textChanged.connect(self.search_customers)
        search_layout.addWidget(self.search_input)
        
        # Customers Table
        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(5)
        self.customers_table.setHorizontalHeaderLabels(["نام و نام خانوادگی", "کد ملی", "شماره تماس", "آدرس", "عملیات"])
        self.customers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customers_table.setFont(QFont("B Yekan", 10))

        self.main_layout.addLayout(header_layout)
        self.main_layout.addLayout(search_layout)
        self.main_layout.addWidget(self.customers_table)
        
        self.load_customers()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def refresh_data(self):
        self.load_customers()
    
    def show_add_customer_form(self, customer_data=None):
        self.clear_layout(self.main_layout)
        
        title_label = QLabel("فرم ثبت مشتری جدید")
        if customer_data:
            title_label.setText("فرم ویرایش مشتری")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.national_code_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()

        if customer_data:
            self.customer_id = customer_data[0]
            self.name_input.setText(customer_data[1])
            self.national_code_input.setText(customer_data[2])
            self.phone_input.setText(customer_data[3])
            self.address_input.setText(customer_data[4])
        
        style_sheet = """
            QLineEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
        """
        self.name_input.setStyleSheet(style_sheet)
        self.national_code_input.setStyleSheet(style_sheet)
        self.phone_input.setStyleSheet(style_sheet)
        self.address_input.setStyleSheet(style_sheet)
        
        form_layout.addRow("نام و نام خانوادگی:", self.name_input)
        form_layout.addRow("کد ملی:", self.national_code_input)
        form_layout.addRow("شماره تماس:", self.phone_input)
        form_layout.addRow("آدرس:", self.address_input)
        
        save_btn = QPushButton("ثبت مشتری")
        if customer_data:
            save_btn.setText("ویرایش مشتری")
            save_btn.clicked.connect(self.update_customer)
        else:
            save_btn.clicked.connect(self.save_customer)
            
        save_btn.setFont(QFont("B Yekan", 12))
        save_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                border-radius: 10px; 
                padding: 10px; 
            }
            QPushButton:hover { 
                background-color: #2980b9; 
            }
        """)
        
        back_btn = QPushButton("بازگشت")
        back_btn.setFont(QFont("B Yekan", 12))
        back_btn.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border-radius: 10px; 
                padding: 10px; 
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
        """)
        # اصلاح: اتصال به تابع build_ui برای بازگشت
        back_btn.clicked.connect(self.build_ui)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(back_btn)
        btn_layout.addWidget(save_btn)
        
        self.main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        self.main_layout.addLayout(form_layout)
        self.main_layout.addLayout(btn_layout)
        self.main_layout.addStretch()

    def save_customer(self):
        name = self.name_input.text()
        national_code = self.national_code_input.text()
        phone = self.phone_input.text()
        address = self.address_input.text()

        if not name or not national_code:
            QMessageBox.warning(self, "خطا", "لطفا نام و کد ملی را وارد کنید.")
            return

        if self.db_manager.add_customer(name, national_code, phone, address):
            QMessageBox.information(self, "موفقیت", f"مشتری {name} با موفقیت ثبت شد.")
            # اصلاح: بازگشت به پنل اصلی
            self.build_ui()
        else:
            QMessageBox.critical(self, "خطا", "خطا در ثبت مشتری. لطفا ورودی‌ها را بررسی کنید.")
    
    def update_customer(self):
        name = self.name_input.text()
        national_code = self.national_code_input.text()
        phone = self.phone_input.text()
        address = self.address_input.text()

        if not name or not national_code:
            QMessageBox.warning(self, "خطا", "لطفا نام و کد ملی را وارد کنید.")
            return
            
        if self.db_manager.update_customer(self.customer_id, name, national_code, phone, address):
            QMessageBox.information(self, "موفقیت", f"مشتری {name} با موفقیت ویرایش شد.")
            # اصلاح: بازگشت به پنل اصلی
            self.build_ui()
        else:
            QMessageBox.critical(self, "خطا", "خطا در ویرایش مشتری.")

    def delete_customer_confirmation(self, customer_id):
        reply = QMessageBox.question(self, "حذف مشتری", 
                                     "آیا از حذف این مشتری مطمئن هستید؟",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_customer(customer_id):
                QMessageBox.information(self, "موفقیت", "مشتری با موفقیت حذف شد.")
                self.load_customers()
            else:
                QMessageBox.critical(self, "خطا", "خطا در حذف مشتری.")
    
    def load_customers(self, customer_list=None):
        # اصلاح: تابع get_all_customers_with_details به db_manager اضافه شده است
        if customer_list is None:
            customers = self.db_manager.get_all_customers_with_details()
        else:
            customers = customer_list
            
        self.customers_table.setRowCount(0)
        
        for row_number, customer in enumerate(customers):
            self.customers_table.insertRow(row_number)
            
            # نمایش اطلاعات مشتری در جدول
            for col, data in enumerate(customer[1:]):
                self.customers_table.setItem(row_number, col, QTableWidgetItem(str(data)))
                
            # اضافه کردن دکمه‌های عملیات (ویرایش/حذف)
            edit_btn = QPushButton("ویرایش")
            edit_btn.setStyleSheet("background-color: #f1c40f; color: white;")
            edit_btn.clicked.connect(lambda _, c=customer: self.show_add_customer_form(c))
            
            delete_btn = QPushButton("حذف")
            delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            delete_btn.clicked.connect(lambda _, c_id=customer[0]: self.delete_customer_confirmation(c_id))
            
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.addWidget(edit_btn)
            ops_layout.addWidget(delete_btn)
            ops_layout.setContentsMargins(0, 0, 0, 0)
            self.customers_table.setCellWidget(row_number, 4, ops_widget)
            
    def search_customers(self, query_str):
        if query_str:
            results = self.db_manager.search_customers(query_str)
            self.load_customers(results)
        else:
            self.load_customers()
