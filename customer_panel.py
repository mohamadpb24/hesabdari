from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QAbstractItemView, QFileDialog
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize

from db_manager import DatabaseManager
from utils import format_money
import report_generator

class CustomerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.build_ui()

    def build_ui(self):
        self.clear_layout(self.main_layout)
        
        # --- Header Layout ---
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت مشتریان")
        title_label.setFont(QFont("B Yekan", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        print_btn = QPushButton("چاپ گزارش")
        print_btn.setFont(QFont("B Yekan", 11))
        print_btn.setIcon(QIcon.fromTheme("document-print"))
        print_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; color: white; 
                border: none; border-radius: 8px; padding: 10px 15px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        print_btn.clicked.connect(self.print_customers_list)

        add_customer_btn = QPushButton("افزودن مشتری")
        add_customer_btn.setFont(QFont("B Yekan", 11))
        add_customer_btn.setIcon(QIcon.fromTheme("list-add"))
        add_customer_btn.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; color: white; 
                border: none; border-radius: 8px; padding: 10px 15px;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        add_customer_btn.clicked.connect(lambda: self.show_add_customer_form())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(print_btn)
        header_layout.addWidget(add_customer_btn)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد ملی یا شماره تماس...")
        self.search_input.setFont(QFont("B Yekan", 10))
        self.search_input.setStyleSheet("""
            QLineEdit { 
                background-color: white; border: 1px solid #dcdcdc;
                border-radius: 8px; padding: 10px; margin-top: 10px;
            }
        """)
        self.search_input.textChanged.connect(self.search_customers)
        
        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(6)
        self.customers_table.setHorizontalHeaderLabels(["نام و نام خانوادگی", "کد ملی", "شماره تماس", "آدرس", "میزان بدهی", "عملیات"])
        
        header = self.customers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.customers_table.setColumnWidth(5, 130)

        self.customers_table.setAlternatingRowColors(True)
        self.customers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customers_table.setStyleSheet("""
            QTableWidget { border: none; }
            QHeaderView::section { background-color: #f2f2f2; padding: 5px; border: none; font-weight: bold; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #e0e0e0; color: black; }
        """)

        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.search_input)
        self.main_layout.addWidget(self.customers_table)
        
        self.load_customers()

    def print_customers_list(self):
        customers = self.db_manager.get_customers_with_debt()
        if not customers:
            QMessageBox.warning(self, "خطا", "مشتری برای گزارش‌گیری وجود ندارد.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش مشتریان", "", "PDF Files (*.pdf)")

        if file_path:
            success = report_generator.create_customers_report(customers, file_path)
            if success:
                QMessageBox.information(self, "موفقیت", f"گزارش با موفقیت در مسیر زیر ذخیره شد:\n{file_path}")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def refresh_data(self):
        self.search_input.clear()
        self.load_customers()
    
    def show_add_customer_form(self, customer_data=None):
        dialog = QDialog(self)
        dialog.setMinimumWidth(450)
        title_text = "فرم ثبت مشتری جدید" if customer_data is None else "فرم ویرایش مشتری"
        dialog.setWindowTitle(title_text)

        dialog.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-size: 12px; }
            QLineEdit { 
                padding: 10px; border: 1px solid #ced4da; 
                border-radius: 8px; background-color: #ffffff; 
            }
            QPushButton { 
                font-size: 12px; font-weight: bold;
                padding: 10px 20px; border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        title_label = QLabel(title_text)
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #343a40; margin-bottom: 10px;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.national_code_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()

        if customer_data:
            self.customer_id = customer_data['id']
            self.name_input.setText(customer_data['name'])
            self.national_code_input.setText(customer_data['national_code'])
            self.phone_input.setText(customer_data['phone_number'])
            self.address_input.setText(customer_data['address'])
        
        form_layout.addRow("نام و نام خانوادگی:", self.name_input)
        form_layout.addRow("کد ملی:", self.national_code_input)
        form_layout.addRow("شماره تماس:", self.phone_input)
        form_layout.addRow("آدرس:", self.address_input)
        
        btn_layout = QHBoxLayout()
        save_btn_text = "ثبت مشتری" if customer_data is None else "ویرایش مشتری"
        save_btn = QPushButton(save_btn_text)
        save_btn.setStyleSheet("background-color: #007bff; color: white;")
        
        if customer_data:
            save_btn.clicked.connect(lambda: self.update_customer(dialog))
        else:
            save_btn.clicked.connect(lambda: self.save_customer(dialog))
            
        back_btn = QPushButton("انصراف")
        back_btn.setStyleSheet("background-color: #6c757d; color: white;")
        back_btn.clicked.connect(dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(back_btn)

        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        
        dialog.exec_()

    def save_customer(self, dialog):
        name = self.name_input.text()
        national_code = self.national_code_input.text()
        phone = self.phone_input.text()
        address = self.address_input.text()

        if not name or not national_code:
            QMessageBox.warning(self, "خطا", "لطفا نام و کد ملی را وارد کنید.")
            return

        if self.db_manager.add_customer(name, national_code, phone, address):
            QMessageBox.information(self, "موفقیت", f"مشتری {name} با موفقیت ثبت شد.")
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "خطا", "خطا در ثبت مشتری. لطفا ورودی‌ها را بررسی کنید.")
    
    def update_customer(self, dialog):
        name = self.name_input.text()
        national_code = self.national_code_input.text()
        phone = self.phone_input.text()
        address = self.address_input.text()

        if not name or not national_code:
            QMessageBox.warning(self, "خطا", "لطفا نام و کد ملی را وارد کنید.")
            return
            
        if self.db_manager.update_customer(self.customer_id, name, national_code, phone, address):
            QMessageBox.information(self, "موفقیت", f"مشتری {name} با موفقیت ویرایش شد.")
            dialog.accept()
            self.refresh_data()
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
        if customer_list is None:
            customers = self.db_manager.get_customers_with_debt()
        else:
            customers = customer_list
            
        self.customers_table.setRowCount(0)
        
        for row, customer in enumerate(customers):
            self.customers_table.insertRow(row)
            
            self.customers_table.setItem(row, 0, QTableWidgetItem(customer['name']))
            self.customers_table.setItem(row, 1, QTableWidgetItem(customer['national_code']))
            self.customers_table.setItem(row, 2, QTableWidgetItem(customer['phone_number']))
            self.customers_table.setItem(row, 3, QTableWidgetItem(customer['address']))
            
            debt_item = QTableWidgetItem(format_money(customer['total_debt']))
            if customer['total_debt'] > 0:
                debt_item.setForeground(QColor("#c0392b"))
                debt_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            self.customers_table.setItem(row, 4, debt_item)
                
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(0, 0, 0, 0)
            ops_layout.setSpacing(5)

            trans_btn = QPushButton("تراکنش‌ها")
            trans_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 4px; padding: 4px;")
            trans_btn.clicked.connect(lambda _, c=customer: self.show_customer_transactions_dialog(c))
            
            edit_btn = QPushButton("ویرایش")
            edit_btn.setStyleSheet("background-color: #f1c40f; color: white; border-radius: 4px; padding: 4px;")
            edit_btn.clicked.connect(lambda _, c=customer: self.show_add_customer_form(c))
            
            delete_btn = QPushButton("حذف")
            delete_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 4px; padding: 4px;")
            delete_btn.clicked.connect(lambda _, c_id=customer['id']: self.delete_customer_confirmation(c_id))
            
            ops_layout.addWidget(trans_btn)
            ops_layout.addWidget(edit_btn)
            ops_layout.addWidget(delete_btn)
            
            self.customers_table.setCellWidget(row, 5, ops_widget)
            
    def search_customers(self, query_str):
        if query_str:
            results = self.db_manager.search_customers(query_str)
            self.load_customers(results)
        else:
            self.load_customers()

    def show_customer_transactions_dialog(self, customer_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تراکنش‌های مشتری: {customer_data['name']}")
        dialog.setGeometry(250, 250, 700, 500)
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["تاریخ", "نوع تراکنش", "مبلغ", "شرح"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        transactions = self.db_manager.get_transactions_by_customer(customer_data['id'])
        table.setRowCount(len(transactions))
        
        for row, trans in enumerate(transactions):
            trans_type = trans['type']
            display_type_map = {
                "loan_payment": "پرداخت وام به مشتری",
                "installment_received": "دریافت قسط از مشتری",
                "settlement_received": "تسویه کامل وام"
            }
            display_type = display_type_map.get(trans_type, trans_type)

            amount_item = QTableWidgetItem(format_money(trans['amount']))
            if trans_type == 'loan_payment':
                amount_item.setForeground(QColor("#c0392b"))
            else:
                amount_item.setForeground(QColor("#27ae60"))
            
            table.setItem(row, 0, QTableWidgetItem(trans['date']))
            table.setItem(row, 1, QTableWidgetItem(display_type))
            table.setItem(row, 2, amount_item)
            table.setItem(row, 3, QTableWidgetItem(trans['description']))
        
        print_record_btn = QPushButton("چاپ پرونده مشتری")
        print_record_btn.setFont(QFont("B Yekan", 11))
        print_record_btn.setIcon(QIcon.fromTheme("document-print"))
        print_record_btn.clicked.connect(lambda: self.print_single_customer_report(customer_data))

        layout.addWidget(table)
        layout.addWidget(print_record_btn)
        dialog.exec_()

    def print_single_customer_report(self, customer_data):
        # فراخوانی تابع جدید برای دریافت تمام اطلاعات با یک اتصال
        loans, installments_by_loan = self.db_manager.get_full_customer_report_data(customer_data['id'])
        
        if loans is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات از پایگاه داده.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره پرونده مشتری", f"پرونده_{customer_data['name']}.pdf", "PDF Files (*.pdf)")

        if file_path:
            success = report_generator.create_single_customer_report(customer_data, loans, installments_by_loan, file_path)
            if success:
                QMessageBox.information(self, "موفقیت", "پرونده مشتری با موفقیت ذخیره شد.")
            else:
                QMessageBox.critical(self, "خطا", "خطا در ساخت گزارش PDF.")










