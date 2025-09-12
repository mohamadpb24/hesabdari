# customer_panel.py (نسخه نهایی با رفع باگ نمایش تراکنش‌ها)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QAbstractItemView, QFrame
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QTimer

from db_manager import DatabaseManager
from utils import format_money

class CustomerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        self.current_page = 1
        self.page_size = 50
        self.total_customers = 0
        
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_customers)
        
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: #f4f7f9;
                border-radius: 15px;
            }
            QTableWidget {
                border: none;
                background-color: #ffffff;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                padding: 10px;
                border: none;
                font-weight: bold;
                color: #495057;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 20, 25, 20)

        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت مشتریان")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        add_btn = QPushButton(" افزودن مشتری جدید")
        add_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 12px 20px; border-radius: 10px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        add_btn.clicked.connect(lambda: self.show_customer_form())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد ملی یا شماره تماس...")
        self.search_input.textChanged.connect(lambda: self.search_timer.start(500))
        
        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(6)
        self.customers_table.setHorizontalHeaderLabels(["کد", "نام و نام خانوادگی", "کد ملی", "مبلغ کل بدهی", "شماره تماس", "عملیات"])
        
        header = self.customers_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4, 5]: header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.customers_table.setColumnWidth(5, 180)
        self.customers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customers_table.setAlternatingRowColors(True)

        pagination_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("صفحه قبل")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.page_label = QLabel("صفحه ۱ از ۱")
        self.next_page_btn = QPushButton("صفحه بعد")
        self.next_page_btn.clicked.connect(self.next_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_btn)
        pagination_layout.addStretch()

        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.search_input)
        container_layout.addWidget(self.customers_table)
        container_layout.addLayout(pagination_layout)
        self.main_layout.addWidget(container)

    def refresh_data(self):
        self.search_input.clear()
        self.current_page = 1
        self.load_customers()

    def load_customers(self):
        search_query = self.search_input.text()
        self.total_customers = self.db_manager.get_customers_count(search_query)
        customers = self.db_manager.get_customers_paginated(self.current_page, self.page_size, search_query)
            
        self.customers_table.setRowCount(0)
        if not customers:
            self.update_pagination_controls()
            return

        for row, customer in enumerate(customers):
            self.customers_table.insertRow(row)
            self.customers_table.setItem(row, 0, QTableWidgetItem(str(customer['Code'])))
            self.customers_table.setItem(row, 1, QTableWidgetItem(customer['FullName']))
            self.customers_table.setItem(row, 2, QTableWidgetItem(customer['NationalID']))
            
            debt_item = QTableWidgetItem(format_money(customer['TotalDebt']))
            if customer['TotalDebt'] > 0:
                debt_item.setForeground(QColor("#c0392b"))
                debt_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            self.customers_table.setItem(row, 3, debt_item)

            self.customers_table.setItem(row, 4, QTableWidgetItem(customer['PhoneNumber']))
            
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(5, 5, 5, 5)
            ops_layout.setSpacing(5)

            trans_btn = QPushButton("تراکنش‌ها")
            trans_btn.setStyleSheet("background-color: #16a085; color: white; border-radius: 5px; padding: 5px;")
            trans_btn.clicked.connect(lambda _, c=customer: self.show_customer_transactions_dialog(c))

            edit_btn = QPushButton("ویرایش")
            edit_btn.setStyleSheet("background-color: #f39c12; color: white; border-radius: 5px; padding: 5px;")
            edit_btn.clicked.connect(lambda _, c=customer: self.show_customer_form(c))
            
            ops_layout.addWidget(trans_btn)
            ops_layout.addWidget(edit_btn)
            
            self.customers_table.setCellWidget(row, 5, ops_widget)
            
        self.update_pagination_controls()

    def show_customer_transactions_dialog(self, customer_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تاریخچه تراکنش‌های: {customer_data['FullName']}")
        dialog.setMinimumSize(700, 500)
        dialog.setStyleSheet("QDialog { background-color: #ffffff; }")
        
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["تاریخ", "صندوق", "نوع تراکنش", "مبلغ", "شرح"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        transactions = self.db_manager.get_person_transactions(customer_data['ID'])
        if transactions:
            table.setRowCount(len(transactions))
            for row, trans in enumerate(transactions):
                # --- شروع اصلاحات کلیدی ---
                amount_item = QTableWidgetItem(format_money(trans['Amount']))
                if trans['PaymentType'] in ['LoanPayment', 'ManualPayment']:
                    amount_item.setForeground(QColor("#c0392b")) # Red for outgoing
                else:
                    amount_item.setForeground(QColor("#27ae60")) # Green for incoming

                table.setItem(row, 0, QTableWidgetItem(str(trans['PaymentDate'])))
                table.setItem(row, 1, QTableWidgetItem(trans['FundName']))
                table.setItem(row, 2, QTableWidgetItem(trans['PaymentType']))
                table.setItem(row, 3, amount_item)
                table.setItem(row, 4, QTableWidgetItem(trans['Description']))
                # --- پایان اصلاحات کلیدی ---
        
        layout.addWidget(table)
        dialog.exec_()
        
    def search_customers(self):
        self.current_page = 1
        self.load_customers()

    def update_pagination_controls(self):
        total_pages = (self.total_customers + self.page_size - 1) // self.page_size if self.total_customers > 0 else 1
        self.page_label.setText(f"صفحه {self.current_page} از {total_pages}")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_customers()

    def next_page(self):
        total_pages = (self.total_customers + self.page_size - 1) // self.page_size if self.total_customers > 0 else 1
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_customers()

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
        address_input = QLineEdit()

        if is_edit:
            customer_id = customer_data['ID']
            name_input.setText(customer_data.get('FullName', ''))
            national_code_input.setText(customer_data.get('NationalID', ''))
            phone_input.setText(customer_data.get('PhoneNumber', ''))
            address_input.setText(customer_data.get('Address', ''))
        
        form_layout.addRow("نام و نام خانوادگی:", name_input)
        form_layout.addRow("کد ملی:", national_code_input)
        form_layout.addRow("شماره تماس:", phone_input)
        form_layout.addRow("آدرس:", address_input)
        
        save_btn = QPushButton("ثبت تغییرات" if is_edit else "ثبت مشتری")
        
        def on_save():
            name = name_input.text()
            national_code = national_code_input.text()
            phone = phone_input.text()
            address = address_input.text()

            if not all([name, national_code, phone]):
                QMessageBox.warning(dialog, "خطا", "پر کردن نام، کد ملی و شماره تماس الزامی است.")
                return

            if is_edit:
                success = self.db_manager.update_customer(customer_id, name, national_code, phone, address)
            else:
                success = self.db_manager.add_customer(name, national_code, phone, address)
            
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