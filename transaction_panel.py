# transaction_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from db_manager import DatabaseManager
from utils import format_money

class TransactionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        title_label = QLabel("مشاهده تراکنش‌ها")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)

        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(6)
        self.transaction_table.setHorizontalHeaderLabels(["شناسه", "نوع", "مبلغ", "تاریخ", "صندوق", "شرح"])
        self.transaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_layout.addWidget(self.transaction_table)

    def refresh_data(self):
            self.transaction_table.setRowCount(0)
            transactions = self.db_manager.get_all_transactions()
            if transactions:
                self.transaction_table.setRowCount(len(transactions))
                # اصلاح شد: دریافت ۷ مقدار از دیتابیس برای جلوگیری از خطا
                for row_index, (id, type, amount, date, source_id, destination_id, description) in enumerate(transactions):
                    self.transaction_table.setItem(row_index, 0, QTableWidgetItem(str(id)))
                    self.transaction_table.setItem(row_index, 1, QTableWidgetItem(type))
                    self.transaction_table.setItem(row_index, 2, QTableWidgetItem(format_money(amount)))
                    self.transaction_table.setItem(row_index, 3, QTableWidgetItem(date))
                    
                    # منطق هوشمند برای نمایش نام صندوق
                    box_id = source_id if type == 'expense' else (destination_id if type in ['installment_received', 'settlement_received'] else source_id)
                    
                    cashbox_name = "N/A"
                    if box_id:
                        cashbox_name = self.db_manager.get_cash_box_name(box_id)
                    
                    self.transaction_table.setItem(row_index, 4, QTableWidgetItem(cashbox_name))
                    self.transaction_table.setItem(row_index, 5, QTableWidgetItem(description))