# expense_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QComboBox, QInputDialog
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

class ExpensePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.build_ui()

    def build_ui(self):
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت هزینه‌ها")
        title_label.setFont(QFont("B Yekan", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        add_btn = QPushButton("ثبت هزینه جدید")
        add_btn.setFont(QFont("B Yekan", 11))
        add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; color: white; 
                border: none; border-radius: 8px; padding: 10px 15px;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        add_btn.clicked.connect(self.show_add_expense_form)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)

        # Table
        self.expense_table = QTableWidget()
        self.expense_table.setColumnCount(5)
        self.expense_table.setHorizontalHeaderLabels(["تاریخ", "دسته‌بندی", "صندوق پرداختی", "مبلغ", "شرح"])
        self.expense_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.expense_table.setAlternatingRowColors(True)
        self.expense_table.setStyleSheet("""
            QTableWidget { border: none; }
            QHeaderView::section { background-color: #f2f2f2; padding: 5px; border: none; font-weight: bold; }
        """)

        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.expense_table)
        self.refresh_data()

    def refresh_data(self):
        self.expense_table.setRowCount(0)
        expenses = self.db_manager.get_all_expenses()
        for row, expense in enumerate(expenses):
            self.expense_table.insertRow(row)
            self.expense_table.setItem(row, 0, QTableWidgetItem(expense['expense_date']))
            self.expense_table.setItem(row, 1, QTableWidgetItem(expense['category_name']))
            self.expense_table.setItem(row, 2, QTableWidgetItem(expense['cashbox_name']))
            self.expense_table.setItem(row, 3, QTableWidgetItem(format_money(expense['amount'])))
            self.expense_table.setItem(row, 4, QTableWidgetItem(expense['description']))

    def show_add_expense_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("فرم ثبت هزینه")
        dialog.setMinimumWidth(450)
        dialog.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-size: 12px; }
            QLineEdit, QComboBox { 
                padding: 10px; border: 1px solid #ced4da; 
                border-radius: 8px; background-color: #ffffff; 
            }
            QPushButton#saveButton { 
                font-size: 12px; font-weight: bold; padding: 10px 20px; 
                border-radius: 8px; background-color: #28a745; color: white;
            }
            QPushButton#saveButton:hover { background-color: #218838; }
        """)

        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        # Category Row with Add Button
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        category_layout.addWidget(self.category_combo, 1)
        
        add_cat_btn = QPushButton("+")
        add_cat_btn.setFixedSize(30, 30)
        add_cat_btn.clicked.connect(self.show_add_category_dialog)
        category_layout.addWidget(add_cat_btn)
        
        self.load_categories_to_combo()
        
        self.cashbox_combo = QComboBox()
        self.load_cashboxes_to_combo()

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ به تومان")
        # Optional: Add live formatting later if needed
        self.amount_input.textChanged.connect(self.format_amount_input)
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("مثال: خرید لوازم اداری")
        
        today_str = jdatetime.date.today().strftime('%Y/%m/%d')
        self.date_input = QLineEdit(today_str)

        form_layout.addRow("دسته‌بندی هزینه:", category_layout)
        form_layout.addRow("پرداخت از صندوق:", self.cashbox_combo)
        form_layout.addRow("مبلغ:", self.amount_input)
        form_layout.addRow("تاریخ هزینه:", self.date_input)
        form_layout.addRow("شرح هزینه:", self.description_input)

        save_btn = QPushButton("ثبت هزینه", objectName="saveButton")
        save_btn.setIcon(QIcon.fromTheme("emblem-ok"))
        save_btn.clicked.connect(lambda: self.save_expense(dialog))
        
        layout.addLayout(form_layout)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        
        dialog.exec_()

    def show_add_category_dialog(self):
        text, ok = QInputDialog.getText(self, 'افزودن دسته‌بندی', 'نام دسته‌بندی جدید را وارد کنید:')
        if ok and text:
            if self.db_manager.add_expense_category(text):
                QMessageBox.information(self, "موفقیت", f"دسته‌بندی '{text}' با موفقیت اضافه شد.")
                self.load_categories_to_combo()
                # Set the newly added category as current
                index = self.category_combo.findText(text)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            else:
                QMessageBox.warning(self, "خطا", "این نام تکراری است یا در افزودن آن مشکلی رخ داده است.")

    def load_categories_to_combo(self):
        current_cat_id = self.category_combo.currentData()
        self.category_combo.clear()
        categories = self.db_manager.get_all_expense_categories()
        if not categories:
            self.db_manager.add_expense_category("عمومی")
            categories = self.db_manager.get_all_expense_categories()

        for cat in categories:
            self.category_combo.addItem(cat['name'], cat['id'])
        
        # Restore previous selection if possible
        if current_cat_id:
            index = self.category_combo.findData(current_cat_id)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

    def load_cashboxes_to_combo(self):
        self.cashbox_combo.clear()
        cashboxes = self.db_manager.get_all_cash_boxes()
        for box_id, name, balance in cashboxes:
            self.cashbox_combo.addItem(f"{name} ({format_money(balance)})", box_id)

    def format_amount_input(self, text):
            try:
                # حذف جداکننده‌های قبلی برای تبدیل به عدد
                plain_text = text.replace("،", "")
                if plain_text.isdigit() and plain_text:
                    # فرمت‌دهی عدد با جداکننده هزارگان
                    formatted_text = f"{int(plain_text):,}".replace(",", "،")
                    
                    # جلوگیری از حلقه بی‌نهایت با بررسی متن فعلی
                    if self.amount_input.text() != formatted_text:
                        self.amount_input.setText(formatted_text)
                        # انتقال نشانگر به انتهای متن
                        self.amount_input.setCursorPosition(len(formatted_text))
                elif not plain_text:
                    self.amount_input.clear()
            except Exception:
                pass # در صورت بروز خطا، هیچ کاری انجام نده


    def save_expense(self, dialog):
        category_id = self.category_combo.currentData()
        cashbox_id = self.cashbox_combo.currentData()
        amount_str = self.amount_input.text().replace("،", "")
        description = self.description_input.text()
        expense_date = self.date_input.text()

        try:
            amount = int(amount_str)
            if amount <= 0:
                QMessageBox.warning(dialog, "خطا", "مبلغ باید یک عدد مثبت باشد.")
                return
        except ValueError:
            QMessageBox.warning(dialog, "خطا", "لطفاً مبلغ را به صورت عددی وارد کنید.")
            return

        if not all([category_id, cashbox_id, expense_date, description]):
            QMessageBox.warning(dialog, "خطا", "پر کردن تمام فیلدها به جز شرح اختیاری، الزامی است.")
            return
        
        # Check if cashbox has enough balance
        cashbox_balance = self.db_manager.get_cash_box_balance(cashbox_id)
        if amount > cashbox_balance:
            reply = QMessageBox.question(self, 'موجودی ناکافی', 
                                         f"موجودی صندوق کافی نیست. آیا می‌خواهید موجودی منفی شود؟",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        success = self.db_manager.add_expense(category_id, cashbox_id, amount, description, expense_date)
        if success:
            QMessageBox.information(dialog, "موفقیت", "هزینه با موفقیت ثبت شد.")
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.critical(dialog, "خطا", "خطا در ثبت هزینه.")