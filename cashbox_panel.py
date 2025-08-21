from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QDoubleSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from db_manager import DatabaseManager
from utils import format_money

class CashboxPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.build_ui()

    def build_ui(self):
        self.clear_layout(self.main_layout)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت صندوق‌ها")
        title_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        add_btn = QPushButton("افزودن صندوق جدید")
        add_btn.setFixedSize(200, 40)
        add_btn.setFont(QFont("B Yekan", 12))
        add_btn.setStyleSheet("""
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
        add_btn.clicked.connect(self.show_add_cashbox_form)
        
        header_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        header_layout.addWidget(add_btn, alignment=Qt.AlignRight)
        
        self.cashbox_table = QTableWidget()
        self.cashbox_table.setColumnCount(4)
        self.cashbox_table.setHorizontalHeaderLabels(["نام صندوق", "موجودی", "عملیات", "تراکنش‌ها"])
        self.cashbox_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cashbox_table.setFont(QFont("B Yekan", 10))
        
        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.cashbox_table)
        
        self.load_cash_boxes()

    def refresh_data(self):
        self.load_cash_boxes()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def load_cash_boxes(self):
    # دریافت اطلاعات صندوق‌ها
        cash_boxes = self.db_manager.get_all_cash_boxes()
        self.cashbox_table.setRowCount(0)
        
        for row, box in enumerate(cash_boxes):
            self.cashbox_table.insertRow(row)
            
            # در اینجا 3 مقدار از تاپل box دریافت می‌شود
            box_id, name, balance = box
            
            self.cashbox_table.setItem(row, 0, QTableWidgetItem(name))
            self.cashbox_table.setItem(row, 1, QTableWidgetItem(format_money(balance)))
            
            # Action Buttons
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            edit_btn = QPushButton("ویرایش")
            delete_btn = QPushButton("حذف")
            edit_btn.clicked.connect(lambda _, b=(box_id, name, balance): self.show_add_cashbox_form(b))
            delete_btn.clicked.connect(lambda _, b_id=box_id: self.delete_cash_box_confirmation(b_id))
            ops_layout.addWidget(edit_btn)
            ops_layout.addWidget(delete_btn)
            ops_layout.setContentsMargins(0, 0, 0, 0)
            self.cashbox_table.setCellWidget(row, 2, ops_widget)
            
            show_transactions_btn = QPushButton("مشاهده تراکنش‌ها")
            show_transactions_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
            show_transactions_btn.clicked.connect(lambda _, b=(box_id, name, balance): self.show_transactions_dialog(b))
            self.cashbox_table.setCellWidget(row, 3, show_transactions_btn)


    def show_add_cashbox_form(self, cashbox_data=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("افزودن/ویرایش صندوق")
        form_layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        balance_input = QDoubleSpinBox()
        balance_input.setRange(-1000000000000, 1000000000000)
        balance_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        
        name_input.setStyleSheet("QLineEdit { background-color: white; border: 1px solid #bdc3c7; border-radius: 5px; padding: 5px; }")
        
        form_layout.addRow("نام صندوق:", name_input)
        form_layout.addRow("موجودی اولیه (تومان):", balance_input)
        
        if cashbox_data:
            box_id, name, balance = cashbox_data
            name_input.setText(name)
            balance_input.setValue(balance)
            save_btn_text = "ویرایش صندوق"
        else:
            save_btn_text = "ثبت صندوق"
            
        save_btn = QPushButton(save_btn_text)
        save_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2ecc71; 
                color: white; 
                border-radius: 10px; 
                padding: 10px; 
            }
            QPushButton:hover { 
                background-color: #27ae60; 
            }
        """)
        save_btn.clicked.connect(lambda: self.save_cash_box(dialog, cashbox_data))
        form_layout.addRow(save_btn)
        
        dialog.exec_()
    
    def save_cash_box(self, dialog, cashbox_data):
        name = dialog.findChild(QLineEdit).text()
        balance = dialog.findChild(QDoubleSpinBox).value()
        
        if not name:
            QMessageBox.warning(dialog, "خطا", "لطفا نام صندوق را وارد کنید.")
            return

        if cashbox_data:
            box_id, _, _ = cashbox_data
            success = self.db_manager.update_cash_box(box_id, name, balance)
        else:
            success = self.db_manager.add_cash_box(name, balance)
            
        if success:
            QMessageBox.information(dialog, "موفقیت", "صندوق با موفقیت ثبت شد.")
            dialog.accept()
            self.load_cash_boxes()
        else:
            QMessageBox.critical(dialog, "خطا", "خطا در ثبت صندوق. لطفاً مجدداً تلاش کنید.")

    def delete_cash_box_confirmation(self, box_id):
        reply = QMessageBox.question(self, 'تأیید حذف', 
                                     "آیا مطمئن هستید که می‌خواهید این صندوق را حذف کنید؟ این عمل غیرقابل بازگشت است.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_cash_box(box_id)
            self.load_cash_boxes()
            QMessageBox.information(self, "حذف موفق", "صندوق با موفقیت حذف شد.")
            
    def show_transactions_dialog(self, cashbox_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تراکنش‌های صندوق: {cashbox_data[1]}")
        dialog.setGeometry(200, 200, 800, 600)
        layout = QVBoxLayout(dialog)
        
        transactions_table = QTableWidget()
        transactions_table.setColumnCount(5)
        transactions_table.setHorizontalHeaderLabels(["نوع", "نام مشتری", "مبلغ", "تاریخ", "شرح"])
        transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        transactions = self.db_manager.get_transactions_by_cashbox(cashbox_data[0])
        transactions_table.setRowCount(len(transactions))
        
        for row, transaction in enumerate(transactions):
            trans_id, trans_type, amount, date, source_id, destination_id, description = transaction
            
            # تعیین نوع تراکنش به زبان فارسی
            if trans_type == "loan_payment":
                display_type = "پرداخت وام"
                customer_id = destination_id
            elif trans_type == "installment_received":
                display_type = "دریافت قسط"
                customer_id = source_id
            else:
                display_type = trans_type
                customer_id = None
            
            # دریافت نام مشتری
            customer_name = "ناشناس"
            if customer_id:
                customer_name = self.db_manager.get_customer_name(customer_id)
            
            transactions_table.setItem(row, 0, QTableWidgetItem(display_type))
            transactions_table.setItem(row, 1, QTableWidgetItem(customer_name))
            transactions_table.setItem(row, 2, QTableWidgetItem(format_money(amount)))
            transactions_table.setItem(row, 3, QTableWidgetItem(date))
            transactions_table.setItem(row, 4, QTableWidgetItem(description))

        layout.addWidget(transactions_table)
        dialog.exec_()
