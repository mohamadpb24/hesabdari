# expense_panel.py (نسخه نهایی بازطراحی شده با ظاهر مدرن)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QComboBox, QInputDialog, QGroupBox
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

class ExpensePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 20, 25, 20)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.build_ui()

    def build_ui(self):
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت هزینه‌ها")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        add_btn = QPushButton(" ثبت هزینه جدید")
        add_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: white; padding: 12px 20px; border-radius: 10px; }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        add_btn.clicked.connect(self.show_add_expense_form)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)

        self.category_table = QTableWidget()
        self.category_table.setColumnCount(3)
        self.category_table.setHorizontalHeaderLabels(["دسته‌بندی", "مبلغ کل هزینه شده", "عملیات"])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.category_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.category_table.setAlternatingRowColors(True)

        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.category_table)
        self.refresh_data()

    def refresh_data(self):
        self.category_table.setRowCount(0)
        categories = self.db_manager.get_expense_categories_with_total()
        
        if not categories:
            return

        for row, category in enumerate(categories):
            self.category_table.insertRow(row)
            self.category_table.setItem(row, 0, QTableWidgetItem(category['Name']))
            self.category_table.setItem(row, 1, QTableWidgetItem(format_money(category['TotalAmount'])))
            
            view_btn = QPushButton("مشاهده تراکنش‌ها")
            view_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
            view_btn.clicked.connect(lambda _, cat=category: self.show_category_transactions(cat))
            self.category_table.setCellWidget(row, 2, view_btn)

    def show_category_transactions(self, category_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تراکنش‌های دسته‌بندی: {category_data['Name']}")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["تاریخ", "صندوق پرداختی", "مبلغ", "شرح"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        transactions = self.db_manager.get_expenses_by_category(category_data['ID'])
        if transactions:
            table.setRowCount(len(transactions))
            for row, trans in enumerate(transactions):
                table.setItem(row, 0, QTableWidgetItem(str(trans['Date'])))
                table.setItem(row, 1, QTableWidgetItem(trans['FundName']))
                table.setItem(row, 2, QTableWidgetItem(format_money(trans['Amount'])))
                table.setItem(row, 3, QTableWidgetItem(trans['Description']))
        
        layout.addWidget(table)
        dialog.exec_()

    def show_add_expense_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("فرم ثبت هزینه")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog { background-color: #f9fafb; }
            QGroupBox { 
                border: 1px solid #dfe6e9; background-color: #ffffff; 
                border-radius: 8px; margin-top: 10px; 
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 5px 15px; background-color: #c0392b; color: white;
                border-radius: 5px; font-weight: bold;
            }
            QLineEdit, QComboBox { padding: 10px; border: 1px solid #ced4da; border-radius: 8px; }
        """)
        
        main_layout = QVBoxLayout(dialog)
        
        form_group = QGroupBox("جزئیات هزینه")
        form_layout = QFormLayout(form_group)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)

        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        category_layout.addWidget(self.category_combo, 1)
        
        add_cat_btn = QPushButton("+")
        add_cat_btn.setFixedSize(35, 35)
        add_cat_btn.setFont(QFont("B Yekan", 12))
        add_cat_btn.clicked.connect(self.show_add_category_dialog)
        category_layout.addWidget(add_cat_btn)
        
        self.cashbox_combo = QComboBox()
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ به تومان")
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("شرح اختیاری (مثال: خرید لوازم اداری)")
        self.date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))

        form_layout.addRow("دسته‌بندی هزینه:", category_layout)
        form_layout.addRow("پرداخت از صندوق:", self.cashbox_combo)
        form_layout.addRow("مبلغ:", self.amount_input)
        form_layout.addRow("تاریخ هزینه:", self.date_input)
        form_layout.addRow("شرح هزینه:", self.description_input)

        save_btn = QPushButton(" ثبت هزینه")
        save_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border-radius: 8px; padding: 10px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        
        self.load_categories_to_combo()
        self.load_cashboxes_to_combo()

        self.amount_input.textChanged.connect(self.format_amount_input)
        save_btn.clicked.connect(lambda: self.save_expense(dialog))
        
        main_layout.addWidget(form_group)
        main_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        dialog.exec_()

    def show_add_category_dialog(self):
        text, ok = QInputDialog.getText(self, 'افزودن دسته‌بندی جدید', 'نام دسته‌بندی:')
        if ok and text:
            success = self.db_manager.add_expense_category(text)
            if success:
                QMessageBox.information(self, "موفقیت", f"دسته‌بندی '{text}' با موفقیت اضافه شد.")
                self.load_categories_to_combo()
                new_index = self.category_combo.findText(text)
                if new_index > -1:
                    self.category_combo.setCurrentIndex(new_index)
            else:
                QMessageBox.warning(self, "خطا", "خطا در افزودن دسته‌بندی.")

    def load_categories_to_combo(self):
        self.category_combo.clear()
        categories = self.db_manager.get_all_expense_categories()
        if categories:
            for cat in categories:
                self.category_combo.addItem(cat['Name'], cat['ID'])

    def load_cashboxes_to_combo(self):
        self.cashbox_combo.clear()
        cashboxes = self.db_manager.get_all_cash_boxes()
        if cashboxes:
            for box_id, name, balance in cashboxes:
                self.cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)

    def format_amount_input(self):
        text = self.amount_input.text().replace(",", "")
        if text.isdigit():
            formatted = f"{int(text):,}"
            if self.amount_input.text() != formatted:
                self.amount_input.setText(formatted)
                self.amount_input.setCursorPosition(len(formatted))

    def save_expense(self, dialog):
        category_id = self.category_combo.currentData()
        cashbox_id = self.cashbox_combo.currentData()
        amount_str = self.amount_input.text().replace(",", "")
        description = self.description_input.text()
        expense_date = self.date_input.text()

        if not all([category_id, cashbox_id, amount_str, expense_date]):
            QMessageBox.warning(dialog, "خطا", "پر کردن تمام فیلدها الزامی است.")
            return

        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError()
        except ValueError:
            QMessageBox.warning(dialog, "خطا", "مبلغ باید یک عدد مثبت باشد.")
            return
        
        success = self.db_manager.add_expense(category_id, cashbox_id, amount, description, expense_date)
        if success:
            QMessageBox.information(dialog, "موفقیت", "هزینه با موفقیت ثبت شد.")
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.critical(dialog, "خطا", "خطا در ثبت هزینه.")