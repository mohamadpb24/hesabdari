# cashbox_panel.py (نسخه نهایی و بازطراحی شده)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QDoubleSpinBox,
    QScrollArea, QFrame, QGridLayout
)
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money, add_months_jalali

# کلاس‌های سفارشی برای مرتب‌سازی صحیح در جدول
class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)

# کلاس کارت گرافیکی برای هر صندوق
class CashboxCard(QFrame):
    def __init__(self, cashbox_data, parent_panel):
        super().__init__()
        self.cashbox_data = cashbox_data
        self.parent_panel = parent_panel
        self.init_ui()

    def init_ui(self):
        self.setMinimumHeight(150)
        self.setObjectName("cashboxCard")
        self.setStyleSheet("""
            #cashboxCard {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4e54c8, stop:1 #8f94fb);
                border-radius: 15px; color: white;
            }
            QLabel { background: transparent; color: white; }
            QPushButton {
                font-family: "B Yekan"; font-size: 10pt; color: white;
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px; padding: 8px 12px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); }
        """)
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(20, 20, 20, 20); main_layout.setSpacing(10)
        header_layout = QHBoxLayout()
        name_label = QLabel(self.cashbox_data[1]); name_label.setFont(QFont("B Yekan", 16, QFont.Bold))
        id_label = QLabel(f"ID: {self.cashbox_data[0]}"); id_label.setFont(QFont("B Yekan", 10)); id_label.setStyleSheet("color: #e0e0e0;")
        header_layout.addWidget(name_label); header_layout.addStretch(); header_layout.addWidget(id_label)
        balance_label = QLabel(format_money(self.cashbox_data[2])); balance_label.setFont(QFont("B Yekan", 22, QFont.Bold)); balance_label.setAlignment(Qt.AlignCenter)
        footer_layout = QHBoxLayout(); footer_layout.setSpacing(10)
        transactions_btn = QPushButton("مشاهده تراکنش‌ها"); transactions_btn.setIcon(QIcon.fromTheme("view-list-text")); transactions_btn.clicked.connect(lambda: self.parent_panel.show_transactions_dialog(self.cashbox_data))
        edit_btn = QPushButton("ویرایش"); edit_btn.setIcon(QIcon.fromTheme("document-edit")); edit_btn.clicked.connect(lambda: self.parent_panel.show_add_cashbox_form(self.cashbox_data))
        delete_btn = QPushButton("حذف"); delete_btn.setIcon(QIcon.fromTheme("edit-delete")); delete_btn.clicked.connect(lambda: self.parent_panel.delete_cash_box_confirmation(self.cashbox_data[0]))
        footer_layout.addWidget(transactions_btn); footer_layout.addWidget(edit_btn); footer_layout.addWidget(delete_btn)
        main_layout.addLayout(header_layout); main_layout.addWidget(balance_label); main_layout.addStretch(); main_layout.addLayout(footer_layout)

# پنل اصلی صندوق‌ها
class CashboxPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setSpacing(20)
        self.build_ui()

    def build_ui(self):
        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت صندوق‌ها"); title_label.setFont(QFont("B Yekan", 18, QFont.Bold)); title_label.setStyleSheet("color: #2c3e50;")
        add_btn = QPushButton("افزودن صندوق جدید"); add_btn.setFont(QFont("B Yekan", 11, QFont.Bold)); add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 8px; padding: 10px 15px;} QPushButton:hover { background-color: #2ecc71; }")
        add_btn.clicked.connect(lambda: self.show_add_cashbox_form()) # اصلاح شد: فراخوانی با lambda
        header_layout.addWidget(title_label); header_layout.addStretch(); header_layout.addWidget(add_btn)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.cards_container = QWidget(); self.cards_layout = QGridLayout(self.cards_container); self.cards_layout.setSpacing(20)
        scroll_area.setWidget(self.cards_container)
        self.main_layout.addLayout(header_layout); self.main_layout.addWidget(scroll_area)

    def refresh_data(self):
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        cash_boxes = self.db_manager.get_all_cash_boxes()
        row, col = 0, 0
        for box in cash_boxes:
            card = CashboxCard(box, self)
            self.cards_layout.addWidget(card, row, col)
            col += 1
            if col > 2: col = 0; row += 1
        self.cards_layout.setRowStretch(row + 1, 1)

    def show_add_cashbox_form(self, cashbox_data=None):
        dialog = QDialog(self)
        is_edit = cashbox_data is not None
        title = "ویرایش صندوق" if is_edit else "افزودن صندوق جدید"; dialog.setWindowTitle(title); dialog.setMinimumWidth(400)
        dialog.setStyleSheet("QDialog { background-color: #f8f9fa; } QLabel { font-size: 11pt; } QLineEdit, QDoubleSpinBox { padding: 10px; border: 1px solid #ced4da; border-radius: 8px; background-color: #ffffff; } QPushButton { font-size: 11pt; font-weight: bold; padding: 10px 20px; border-radius: 8px; }")
        form_layout = QFormLayout(dialog); form_layout.setSpacing(15)
        name_input = QLineEdit(); balance_input = QDoubleSpinBox(); balance_input.setRange(-1e12, 1e12); balance_input.setButtonSymbols(QDoubleSpinBox.NoButtons); balance_input.setGroupSeparatorShown(True)
        form_layout.addRow("نام صندوق:", name_input)
        form_layout.addRow("موجودی (تومان):" if is_edit else "موجودی اولیه (تومان):", balance_input)
        if is_edit: box_id, name, balance = cashbox_data; name_input.setText(name); balance_input.setValue(balance)
        save_btn_text = "ثبت تغییرات" if is_edit else "ثبت صندوق"; save_btn = QPushButton(save_btn_text); save_btn.setStyleSheet("background-color: #007bff; color: white;")
        save_btn.clicked.connect(lambda: self.save_cash_box(dialog, name_input.text(), balance_input.value(), cashbox_data))
        form_layout.addRow(save_btn)
        dialog.exec_()
    
    def save_cash_box(self, dialog, name, balance, cashbox_data):
        if not name: QMessageBox.warning(dialog, "خطا", "لطفا نام صندوق را وارد کنید."); return
        success = self.db_manager.update_cash_box(cashbox_data[0], name, balance) if cashbox_data else self.db_manager.add_cash_box(name, balance)
        if success: QMessageBox.information(self, "موفقیت", "عملیات با موفقیت انجام شد."); dialog.accept(); self.refresh_data()
        else: QMessageBox.critical(self, "خطا", "خطا در ثبت اطلاعات. لطفاً مجدداً تلاش کنید.")

    def delete_cash_box_confirmation(self, box_id):
        reply = QMessageBox.question(self, 'تایید حذف', "آیا از حذف این صندوق مطمئن هستید؟\nاین عمل غیرقابل بازگشت است.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_cash_box(box_id): QMessageBox.information(self, "حذف موفق", "صندوق با موفقیت حذف شد."); self.refresh_data()
            else: QMessageBox.critical(self, "خطا", "خطا در حذف صندوق.")
            
    def show_transactions_dialog(self, cashbox_data):
        selected_cashbox_id = cashbox_data[0]
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"گردش حساب صندوق: {cashbox_data[1]}")
        dialog.setGeometry(200, 200, 1200, 700) # پنجره بزرگتر

        # --- استایل شیت جدید و مدرن ---
        dialog.setStyleSheet("""
            QDialog { background-color: #fdfdfe; }
            QTableWidget {
                border: 1px solid #dfe6e9;
                gridline-color: #e0e0e0;
                font-size: 10pt;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #4A5568; /* هدر تیره و مدرن */
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-right: 1px solid #5A6578;
            }
            QHeaderView::section:last { border-right: none; }
            QPushButton {
                font-family: "B Yekan"; font-size: 9pt;
                padding: 5px; border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        transactions_table = QTableWidget()
        transactions_table.setColumnCount(8)
        transactions_table.setHorizontalHeaderLabels(["ID", "تاریخ", "نوع تراکنش", "مبلغ", "طرف حساب", "شرح", "موجودی پس از تراکنش", "عملیات"])
        
        # --- فعال‌سازی قابلیت تغییر اندازه ستون‌ها ---
        header = transactions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive) # قابلیت تغییر اندازه توسط کاربر
        header.setStretchLastSection(False)
        
        transactions_table.setAlternatingRowColors(True)
        transactions_table.setSortingEnabled(True)
        transactions_table.setFont(QFont("B Yekan", 10))
        
        transactions = self.db_manager.get_transactions_with_running_balance(selected_cashbox_id)
        transactions_table.setRowCount(len(transactions))
        
        # تعریف انواع تراکنش‌های ورودی و خروجی برای رنگ‌بندی دقیق
        INCOMING_TYPES = {'installment_received', 'settlement_received', 'capital_injection', 'manual_receipt'}
        OUTGOING_TYPES = {'loan_payment', 'expense', 'manual_payment'}

        for row, transaction in enumerate(transactions):
            trans_type = transaction['type']
            display_type_map = { "loan_payment": "پرداخت وام", "installment_received": "دریافت قسط", "settlement_received": "تسویه کامل", "expense": "هزینه", "capital_injection": "افزایش سرمایه", "manual_payment": "پرداخت دستی", "manual_receipt": "دریافت دستی", "transfer": "انتقال" }
            
            amount_item = NumericTableWidgetItem(format_money(transaction['amount']))
            amount_item.setData(Qt.UserRole, transaction['amount'])
            
            # --- منطق جدید و دقیق برای رنگ‌بندی ---
            if trans_type in INCOMING_TYPES:
                amount_item.setForeground(QColor("#27ae60"))  # سبز برای ورودی‌ها
            elif trans_type in OUTGOING_TYPES:
                amount_item.setForeground(QColor("#c0392b"))  # قرمز برای خروجی‌ها
            elif trans_type == 'transfer':
                if transaction['destination_id'] == selected_cashbox_id:
                    amount_item.setForeground(QColor("#27ae60")) # سبز برای انتقال ورودی
                else:
                    amount_item.setForeground(QColor("#c0392b")) # قرمز برای انتقال خروجی
            
            id_item = NumericTableWidgetItem(str(transaction['id'])); id_item.setData(Qt.UserRole, transaction['id'])
            date_as_string = str(transaction['date'])
            date_obj = jdatetime.datetime.strptime(date_as_string, '%Y-%m-%d').date()
            date_item = DateTableWidgetItem(date_obj.strftime('%Y/%m/%d'))
            date_item.setData(Qt.UserRole, date_obj)
            balance_item = NumericTableWidgetItem(format_money(transaction['balance_after'])); balance_item.setData(Qt.UserRole, transaction['balance_after'])
            
            transactions_table.setItem(row, 0, id_item)
            transactions_table.setItem(row, 1, date_item)
            transactions_table.setItem(row, 2, QTableWidgetItem(display_type_map.get(trans_type, trans_type)))
            transactions_table.setItem(row, 3, amount_item)
            transactions_table.setItem(row, 4, QTableWidgetItem(transaction.get('counterparty_name') or "ناشناس"))
            transactions_table.setItem(row, 5, QTableWidgetItem(transaction['description']))
            transactions_table.setItem(row, 6, balance_item)

            delete_btn = QPushButton("حذف"); delete_btn.setIcon(QIcon.fromTheme("edit-delete"));
            delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            delete_btn.clicked.connect(lambda _, trans_id=transaction['id'], d=dialog, c_data=cashbox_data: self.delete_transaction_confirmation(trans_id, d, c_data))
            transactions_table.setCellWidget(row, 7, delete_btn)
        
        # تنظیم عرض ستون‌ها پس از پر شدن داده‌ها برای عملکرد بهتر
        transactions_table.resizeColumnsToContents()
        transactions_table.setColumnWidth(5, 250) # افزایش عرض ستون شرح

        layout.addWidget(transactions_table)
        dialog.exec_()

    def delete_transaction_confirmation(self, transaction_id, current_dialog, cashbox_data):
        reply = QMessageBox.question(self, 'تایید حذف', "آیا از حذف این تراکنش مطمئن هستید؟\nاین عمل غیرقابل بازگشت است و موجودی‌ها را تغییر می‌دهد.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, message = self.db_manager.delete_transaction_by_id(transaction_id)
            if success:
                QMessageBox.information(self, "حذف موفق", "تراکنش با موفقیت حذف شد.")
                current_dialog.close()
                self.show_transactions_dialog(cashbox_data)
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطا", f"خطا در حذف تراکنش: {message}")