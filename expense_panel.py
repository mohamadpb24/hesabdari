# expense_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QFormLayout, QMessageBox, QGroupBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFrame
)
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtCore import Qt
import jdatetime
from db_manager import DatabaseManager
from utils import format_money

# =========================================================
# 1. کلاس پنجره ثبت هزینه جدید (Dialog)
# =========================================================
class AddExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.setWindowTitle("ثبت هزینه جدید")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # --- فیلدها ---
        
        # دسته‌بندی (همراه دکمه افزودن)
        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.add_cat_btn = QPushButton("+")
        self.add_cat_btn.setFixedSize(30, 30)
        self.add_cat_btn.setStyleSheet("background-color: #27ae60; color: white; border: none; border-radius: 3px;")
        self.add_cat_btn.clicked.connect(self.show_add_category_dialog)
        cat_layout.addWidget(self.category_combo)
        cat_layout.addWidget(self.add_cat_btn)

        self.fund_combo = QComboBox()
        
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ به ریال/تومان")
        self.amount_input.textChanged.connect(self.format_amount)
        
        self.date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        self.desc_input = QLineEdit()

        form_layout.addRow("دسته‌بندی:", cat_layout)
        form_layout.addRow("از صندوق:", self.fund_combo)
        form_layout.addRow("مبلغ:", self.amount_input)
        form_layout.addRow("تاریخ:", self.date_input)
        form_layout.addRow("شرح:", self.desc_input)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("ثبت نهایی")
        save_btn.setStyleSheet("background-color: #2980b9; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        save_btn.clicked.connect(self.save_expense)
        
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        
        # لود اولیه
        self.load_combos()

    def load_combos(self):
        # دسته‌بندی‌ها
        self.category_combo.clear()
        cats = self.db_manager.get_expense_categories()
        if cats:
            for c in cats:
                try: self.category_combo.addItem(c['name'], c['id'])
                except: self.category_combo.addItem(str(c[1]), c[0])
        else:
            self.category_combo.addItem("---", None)

        # صندوق‌ها
        self.fund_combo.clear()
        funds = self.db_manager.get_all_cash_boxes()
        if funds:
            for f in funds:
                try: 
                    self.fund_combo.addItem(f"{f['Name']} ({format_money(f['Inventory'])})", f['ID'])
                except: 
                    self.fund_combo.addItem(f"{f[1]} ({format_money(f[2])})", f[0])

    def format_amount(self):
        text = self.amount_input.text().replace(",", "")
        if text.isdigit():
            formatted = f"{int(text):,}"
            if self.amount_input.text() != formatted:
                self.amount_input.blockSignals(True)
                self.amount_input.setText(formatted)
                self.amount_input.blockSignals(False)

    def show_add_category_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("دسته‌بندی جدید")
        layout = QVBoxLayout(dialog)
        name_input = QLineEdit()
        name_input.setPlaceholderText("نام دسته‌بندی...")
        save_btn = QPushButton("افزودن")
        save_btn.clicked.connect(lambda: self.save_new_cat(name_input.text(), dialog))
        layout.addWidget(QLabel("نام:"))
        layout.addWidget(name_input)
        layout.addWidget(save_btn)
        dialog.exec_()

    def save_new_cat(self, name, dialog):
        if name:
            self.db_manager.add_expense_category(name)
            dialog.accept()
            self.load_combos()

    def save_expense(self):
        cat_id = self.category_combo.currentData()
        fund_id = self.fund_combo.currentData()
        amt_str = self.amount_input.text().replace(",", "")
        date = self.date_input.text()
        desc = self.desc_input.text()
        
        if not all([cat_id, fund_id, amt_str, date]):
            QMessageBox.warning(self, "خطا", "لطفا فیلدهای ستاره‌دار را پر کنید.")
            return
            
        success = self.db_manager.add_expense(cat_id, fund_id, float(amt_str), desc, date)
        if success:
            QMessageBox.information(self, "موفقیت", "هزینه ثبت شد.")
            self.accept()
        else:
            QMessageBox.critical(self, "خطا", "خطا در ثبت هزینه.")


# =========================================================
# 2. کلاس پنجره ریز تراکنش‌های دسته‌بندی (Dialog)
# =========================================================
class CategoryDetailsDialog(QDialog):
    def __init__(self, category_id, category_name, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.cat_id = category_id
        self.cat_name = category_name
        self.setWindowTitle(f"ریز هزینه‌های: {category_name}")
        self.setMinimumSize(800, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["تاریخ", "مبلغ", "صندوق پرداختی", "شرح", "عملیات"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)
        
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.load_data()

    def load_data(self):
        expenses = self.db_manager.get_expenses_by_category(self.cat_id)
        self.table.setRowCount(0)
        
        if expenses:
            self.table.setRowCount(len(expenses))
            for row, exp in enumerate(expenses):
                # فرض بر این است که خروجی دیکشنری است
                # ID, Amount, date, Description, FundName
                
                self.table.setItem(row, 0, QTableWidgetItem(str(exp['date'])))
                
                amt_item = QTableWidgetItem(format_money(exp['Amount']))
                amt_item.setForeground(QColor("#c0392b"))
                self.table.setItem(row, 1, amt_item)
                
                self.table.setItem(row, 2, QTableWidgetItem(str(exp['FundName'])))
                self.table.setItem(row, 3, QTableWidgetItem(str(exp['Description'])))
                
                # دکمه حذف
                del_btn = QPushButton("حذف")
                del_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 3px; padding: 2px 5px;")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.clicked.connect(lambda _, eid=exp['ID']: self.delete_expense(eid))
                
                w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(2,2,2,2); l.setAlignment(Qt.AlignCenter)
                l.addWidget(del_btn)
                self.table.setCellWidget(row, 4, w)

    def delete_expense(self, exp_id):
        reply = QMessageBox.question(self, "تایید حذف", "آیا مطمئن هستید؟ مبلغ به صندوق برمی‌گردد.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, msg = self.db_manager.delete_expense(exp_id)
            if success:
                self.load_data() # رفرش جدول
            else:
                QMessageBox.critical(self, "خطا", str(msg))


# =========================================================
# 3. پنل اصلی هزینه‌ها (داشبورد)
# =========================================================
class ExpensePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- بخش بالایی: دکمه‌های عملیاتی ---
        top_frame = QFrame()
        top_frame.setStyleSheet(".QFrame { background-color: #ecf0f1; border-radius: 8px; border: 1px solid #bdc3c7; }")
        top_layout = QHBoxLayout(top_frame)
        
        lbl_title = QLabel("مدیریت هزینه‌ها")
        lbl_title.setFont(QFont("B Yekan", 14, QFont.Bold))
        
        btn_add_expense = QPushButton("ثبت هزینه جدید")
        btn_add_expense.setMinimumHeight(40)
        btn_add_expense.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 5px; padding: 0 15px;")
        btn_add_expense.clicked.connect(self.open_add_expense)

        btn_add_cat = QPushButton("مدیریت دسته‌بندی‌ها")
        btn_add_cat.setMinimumHeight(40)
        btn_add_cat.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; border-radius: 5px; padding: 0 15px;")
        # فعلا این دکمه همون دیالوگ ادد اکسپنس رو باز میکنه که توش دکمه دسته بندی هست
        # یا میتونیم یک دیالوگ جدا بسازیم. فعلا برای سادگی:
        btn_add_cat.clicked.connect(self.open_add_expense) 

        top_layout.addWidget(lbl_title)
        top_layout.addStretch()
        top_layout.addWidget(btn_add_cat)
        top_layout.addWidget(btn_add_expense)
        
        layout.addWidget(top_frame)

        # --- بخش میانی: جدول دسته‌بندی‌ها ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["کد", "نام دسته‌بندی", "مجموع هزینه شده", "عملیات"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget { font-size: 13px; border: 1px solid #ddd; }
            QHeaderView::section { background-color: #f7f9f9; padding: 5px; border: none; font-weight: bold; }
        """)
        
        layout.addWidget(self.table)

        # --- بخش پایینی: جمع کل ---
        bot_frame = QFrame()
        bot_frame.setStyleSheet("background-color: #2c3e50; color: white; border-radius: 8px;")
        bot_layout = QHBoxLayout(bot_frame)
        
        self.lbl_grand_total = QLabel("جمع کل هزینه‌ها: 0")
        self.lbl_grand_total.setFont(QFont("B Yekan", 14, QFont.Bold))
        self.lbl_grand_total.setAlignment(Qt.AlignCenter)
        
        bot_layout.addWidget(self.lbl_grand_total)
        
        layout.addWidget(bot_frame)

        # لود داده‌ها
        self.load_categories()

    def showEvent(self, event):
        self.load_categories()
        super().showEvent(event)

    def load_categories(self):
        cats = self.db_manager.get_expense_categories() # فرض: برمی‌گرداند id, name, total
        # اگر get_expense_categories شما ستون total ندارد، باید کوئریش را در db_manager اصلاح کنید
        # کوئری باید SELECT id, name, total, code FROM ExpenseCategories باشد
        
        self.table.setRowCount(0)
        grand_total = 0
        
        if cats:
            self.table.setRowCount(len(cats))
            for row, cat in enumerate(cats):
                # تبدیل دیکشنری/تاپل
                try:
                    c_id = cat['id']
                    c_name = cat['name']
                    c_total = float(cat['total'] or 0)
                    c_code = cat.get('code', '-')
                except:
                    c_id = cat[0]
                    c_name = cat[3] # بسته به ترتیب ستون‌ها در کوئری شما
                    c_total = 0 # اگر ستون total نبود
                
                grand_total += c_total
                
                self.table.setItem(row, 0, QTableWidgetItem(str(c_code)))
                self.table.setItem(row, 1, QTableWidgetItem(str(c_name)))
                
                total_item = QTableWidgetItem(format_money(c_total))
                total_item.setFont(QFont("B Yekan", 11, QFont.Bold))
                self.table.setItem(row, 2, total_item)
                
                # دکمه مشاهده ریز
                view_btn = QPushButton("مشاهده تراکنش‌ها")
                view_btn.setStyleSheet("background-color: #8e44ad; color: white; border-radius: 3px; padding: 4px;")
                view_btn.setCursor(Qt.PointingHandCursor)
                view_btn.clicked.connect(lambda _, cid=c_id, cname=c_name: self.open_category_details(cid, cname))
                
                w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(2,2,2,2); l.setAlignment(Qt.AlignCenter)
                l.addWidget(view_btn)
                self.table.setCellWidget(row, 3, w)

        self.lbl_grand_total.setText(f"جمع کل هزینه‌ها: {format_money(grand_total)} تومان")

    def open_add_expense(self):
        dialog = AddExpenseDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_categories() # رفرش بعد از ثبت

    def open_category_details(self, cat_id, cat_name):
        dialog = CategoryDetailsDialog(cat_id, cat_name, self)
        dialog.exec_()
        self.load_categories() # رفرش بعد از حذف احتمالی