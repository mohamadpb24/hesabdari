# transaction_panel.py (نسخه نهایی با اسکرول افقی و تنظیم هوشمند عرض ستون)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

from db_manager import DatabaseManager
from utils import format_money

class NumericTableWidgetItem(QTableWidgetItem):
    """ویجت آیتم جدول برای مرتب‌سازی صحیح اعداد."""
    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)

class TransactionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        
        self.current_page = 1
        self.page_size = 50
        
        self.build_ui()

    def build_ui(self):
        # --- هدر پنل ---
        header_layout = QHBoxLayout()
        title_label = QLabel("لیست کل تراکنش‌ها")
        title_label.setFont(QFont("B Yekan", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # --- جدول تراکنش‌ها ---
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(9)
        self.transaction_table.setHorizontalHeaderLabels([
            "تاریخ", "نوع", "مبلغ", "مبدا", "مقصد", "شرح", "UUID تراکنش", "Parent ID", "Readable ID"
        ])
        
        header = self.transaction_table.horizontalHeader()
        # --- شروع تغییرات برای تنظیم عرض ستون‌ها و اسکرول ---
        header = self.transaction_table.horizontalHeader()
        header.setSectionResizeMode(5, QHeaderView.Stretch) # شرح
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # تاریخ
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # نوع
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # مبلغ
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # مبدا
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # مقصد
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # UUID
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) # Parent ID
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # Readable ID

        # فعال کردن اسکرول افقی
        self.transaction_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # --- پایان تغییرات ---

        self.transaction_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transaction_table.setAlternatingRowColors(True)
        self.transaction_table.setStyleSheet("""
            QTableWidget { border: none; }
            QHeaderView::section { background-color: #f2f2f2; padding: 8px; border: none; font-weight: bold; }
            QTableWidget::item { padding: 8px; }
        """)

        # --- کنترل‌های صفحه‌بندی ---
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

        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.transaction_table)
        self.main_layout.addLayout(pagination_layout)

    def refresh_data(self):
        """بارگذاری مجدد اطلاعات و نمایش در جدول."""
        self.current_page = 1
        self.load_transactions()

    def load_transactions(self):
        self.transaction_table.setRowCount(0)
        transactions = self.db_manager.get_all_transactions_paginated(self.current_page, self.page_size)
        if not transactions:
            return

        self.transaction_table.setRowCount(len(transactions))
        
        type_map = {
            "loan_payment": "پرداخت وام", "installment_received": "دریافت قسط",
            "settlement_received": "تسویه کامل", "expense": "هزینه", 
            "capital_injection": "افزایش سرمایه", "manual_payment": "پرداخت دستی",
            "manual_receipt": "دریافت دستی", "transfer": "انتقال وجه"
        }

        for row, trans in enumerate(transactions):
            # آیتم تاریخ
            date_item = QTableWidgetItem(str(trans['date']))
            
            # آیتم نوع تراکنش
            trans_type = type_map.get(trans['type'], trans['type'])
            type_item = QTableWidgetItem(trans_type)

            # آیتم مبلغ با رنگ‌بندی
            amount = trans['amount']
            amount_item = NumericTableWidgetItem(format_money(amount))
            amount_item.setData(Qt.UserRole, amount)
            if trans['type'] in ['installment_received', 'settlement_received', 'capital_injection', 'manual_receipt']:
                amount_item.setForeground(QColor("#27ae60")) # سبز برای ورودی
            else:
                amount_item.setForeground(QColor("#c0392b")) # قرمز برای خروجی

            # ستون‌های مبدا و مقصد
            source_item = QTableWidgetItem(str(trans.get('source_name', 'N/A')))
            destination_item = QTableWidgetItem(str(trans.get('destination_name', 'N/A')))
            
            # ستون‌های دیگر
            desc_item = QTableWidgetItem(trans['description'])
            uuid_item = QTableWidgetItem(trans['id'])
            readable_id_item = QTableWidgetItem(trans['readable_id'])
            
            # تنظیم فونت برای UUID برای خوانایی بهتر
            uuid_font = QFont("monospace", 9)
            uuid_item.setFont(uuid_font)
            parent_id_item = QTableWidgetItem(str(trans.get('parent_id', 'N/A')))
            parent_id_item.setFont(uuid_font)
            self.transaction_table.setItem(row, 0, QTableWidgetItem(str(trans['date'])))
            self.transaction_table.setItem(row, 1, QTableWidgetItem(type_map.get(trans['type'], trans['type'])))
            self.transaction_table.setItem(row, 2, amount_item)
            self.transaction_table.setItem(row, 3, QTableWidgetItem(str(trans.get('source_name', 'N/A'))))
            self.transaction_table.setItem(row, 4, QTableWidgetItem(str(trans.get('destination_name', 'N/A'))))
            self.transaction_table.setItem(row, 5, QTableWidgetItem(trans['description']))
            self.transaction_table.setItem(row, 6, uuid_item)
            self.transaction_table.setItem(row, 7, parent_id_item) # <-- اضافه شد
            self.transaction_table.setItem(row, 8, QTableWidgetItem(trans['readable_id']))
            
        self.update_pagination_controls()

    def update_pagination_controls(self):
        total_items = self.db_manager.get_transactions_count()
        total_pages = (total_items + self.page_size - 1) // self.page_size
        if total_pages == 0: total_pages = 1
        
        self.page_label.setText(f"صفحه {self.current_page} از {total_pages}")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_transactions()

    def next_page(self):
        total_items = self.db_manager.get_transactions_count()
        total_pages = (total_items + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_transactions()