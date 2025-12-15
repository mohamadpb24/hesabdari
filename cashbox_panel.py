# cashbox_panel.py (نسخه نهایی با پس‌زمینه سفید برای گردش حساب)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QDialog, QDoubleSpinBox,
    QScrollArea, QFrame, QGridLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QBrush, QLinearGradient
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPixmap
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

# کلاس‌های سفارشی برای مرتب‌سازی صحیح در جدول
class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # این تابع برای مرتب‌سازی عددی در جدول استفاده می‌شود
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except (ValueError, TypeError):
            return super().__lt__(other)

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # این تابع برای مرتب‌سازی تاریخ در جدول استفاده می‌شود
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)

# کلاس کارت گرافیکی برای هر صندوق
class CashboxCard(QFrame):
    def __init__(self, fund_data, parent_panel):
        super().__init__()
        self.fund_data = fund_data
        self.parent_panel = parent_panel
        self.setGraphicsEffect(self.create_shadow())
        self.init_ui()

    def create_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        return shadow

    def init_ui(self):
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 20px;
                border: 1px solid rgba(200, 200, 200, 0.5);
            }
            QLabel { background: transparent; border: none; }
            QPushButton {
                background-color: rgba(0, 0, 0, 0.05); border: none;
                border-radius: 10px; padding: 8px 15px;
                font-family: "B Yekan"; font-size: 10pt; color: #2c3e50;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.1); }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(10)

        name_label = QLabel(self.fund_data[1])
        name_label.setFont(QFont("B Yekan", 14, QFont.Bold))
        name_label.setStyleSheet("color: #2c3e50;")

        balance_label = QLabel(format_money(self.fund_data[2]))
        balance_label.setFont(QFont("B Yekan", 24, QFont.Bold))
        balance_label.setStyleSheet("color: #34495e;")
        balance_label.setAlignment(Qt.AlignCenter)
        
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        
        transactions_btn = QPushButton("مشاهده تراکنش‌ها")
        transactions_btn.clicked.connect(lambda: self.parent_panel.show_transactions_dialog(self.fund_data))
        
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(lambda: self.parent_panel.show_fund_form(self.fund_data))

        footer_layout.addWidget(transactions_btn)
        footer_layout.addWidget(edit_btn)

        main_layout.addWidget(name_label)
        main_layout.addStretch()
        main_layout.addWidget(balance_label)
        main_layout.addStretch()
        main_layout.addLayout(footer_layout)

# پنل اصلی صندوق‌ها
class CashboxPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: transparent;")
        self.build_ui()

    def build_ui(self):
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #e0eafc, stop:1 #cfdef3);
                border-radius: 15px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 20, 25, 20)

        header_layout = QHBoxLayout()
        title_label = QLabel("مدیریت صندوق‌ها")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        add_btn = QPushButton("افزودن صندوق جدید")
        add_btn.setFont(QFont("B Yekan", 11, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 12px 20px; border-radius: 10px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        add_btn.clicked.connect(lambda: self.show_fund_form())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(25)
        scroll_area.setWidget(self.cards_container)
        
        container_layout.addLayout(header_layout)
        container_layout.addWidget(scroll_area)
        
        self.main_layout.addWidget(container)
        self.refresh_data()
        
    def refresh_data(self):
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        funds = self.db_manager.get_all_cash_boxes()
        row, col = 0, 0
        if funds:
            for fund in funds:
                card = CashboxCard(fund, self)
                self.cards_layout.addWidget(card, row, col)
                col += 1
                if col > 2: col = 0; row += 1
        self.cards_layout.setRowStretch(row + 1, 1)

    def show_fund_form(self, fund_data=None):
        is_edit = fund_data is not None
        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش صندوق" if is_edit else "افزودن صندوق جدید")
        form_layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        balance_input = QDoubleSpinBox()
        balance_input.setRange(-1e12, 1e12)
        balance_input.setGroupSeparatorShown(True)

        if is_edit:
            fund_id, name, balance = fund_data
            name_input.setText(name)
            balance_input.setValue(balance)

        form_layout.addRow("نام صندوق:", name_input)
        form_layout.addRow("موجودی (تومان):", balance_input)
        
        save_btn = QPushButton("ثبت تغییرات" if is_edit else "ثبت صندوق")
        
        def on_save():
            name = name_input.text()
            balance = balance_input.value()
            if not name:
                QMessageBox.warning(dialog, "خطا", "نام صندوق نمی‌تواند خالی باشد.")
                return

            if is_edit:
                success = self.db_manager.update_fund(fund_id, name, balance)
            else:
                success = self.db_manager.add_fund(name, balance)

            if success:
                QMessageBox.information(self, "موفقیت", "عملیات با موفقیت انجام شد.")
                dialog.accept()
                self.refresh_data()
            else:
                QMessageBox.critical(self, "خطا", "خطا در ثبت اطلاعات.")

        save_btn.clicked.connect(on_save)
        form_layout.addRow(save_btn)
        dialog.exec_()
    
    def show_transactions_dialog(self, fund_data):
        try:
            fund_id = fund_data['ID']
            fund_name = fund_data['Name']
        except (TypeError, IndexError, KeyError):
            fund_id = fund_data[0]
            fund_name = fund_data[1]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"تراکنش‌های صندوق: {fund_name}")
        dialog.setMinimumSize(1100, 650)
        
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(7) 
        table.setHorizontalHeaderLabels(["تاریخ", "نوع", "طرف حساب", "شرح", "مبلغ", "مانده صندوق", "عملیات"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("QTableWidget { background-color: white; font-size: 13px; }")
        
        # 1. دریافت تراکنش‌ها (از قدیم به جدید - ASC)
        raw_transactions = self.db_manager.get_fund_transactions(fund_id)
        
        processed_rows = []
        running_balance = 0.0 # شروع محاسبه از صفر
        
        for trans in raw_transactions:
            amount = float(trans['Amount'])
            p_type = str(trans['Type']) # تبدیل به رشته برای اطمینان
            p_id = trans['ID']
            t_fund_id = trans['Fund_ID']
            
            # --- تشخیص دقیق ورودی/خروجی (اصلاح شده) ---
            is_income = False
            
            # لیست تمام حالت‌هایی که پول از صندوق خارج می‌شود (خروجی -)
            output_types = [
                'LoanPayment',        # پرداخت وام
                'Expense',            # هزینه
                'StorePayment',       # پرداخت به فروشگاه
                'ManualPayment',      # پرداخت دستی (حروف بزرگ)
                'manual_payment',     # پرداخت دستی (حروف کوچک)
                'payment_to_customer' # محض احتیاط
            ]
            
            if p_type in output_types:
                is_income = False
            elif p_type == 'transfer' and t_fund_id == fund_id:
                # اگر در انتقال، ما فرستنده باشیم -> خروجی
                is_income = False
            else:
                # بقیه موارد ورودی هستند (+)
                # شامل: InstallmentPayment, Settlement, CapitalInjection, ManualReceipt
                is_income = True

            # --- محاسبه ریاضی (مستقیم) ---
            if is_income:
                running_balance += amount
                sign = "+"
                color_text = QColor("#27ae60") # سبز
            else:
                running_balance -= amount
                sign = "-"
                color_text = QColor("#c0392b") # قرمز

            # --- ترجمه برای نمایش ---
            type_map = {
                'LoanPayment': 'پرداخت وام',
                'InstallmentPayment': 'دریافت قسط',
                'TransfertoStore': 'انتقال اعتباری',
                'StorePayment': 'پرداخت به فروشگاه',
                'Expense': 'هزینه',
                'Settlement': 'تسویه وام',
                'transfer': 'انتقال وجه',
                'manual_payment': 'پرداخت دستی',
                'ManualPayment': 'پرداخت دستی',
                'manual_receipt': 'دریافت دستی',
                'ManualReceipt': 'دریافت دستی',
                'capital_injection': 'افزایش سرمایه',
                'CapitalInjection': 'افزایش سرمایه'
            }
            display_type = type_map.get(p_type, p_type)
            if p_type == 'transfer':
                display_type += " (ورودی)" if is_income else " (خروجی)"

            # ذخیره در لیست موقت
            processed_rows.append({
                'date': trans['Date'],
                'type': display_type,
                'party': trans['Counterparty'] or '-',
                'desc': trans['Description'],
                'amount_str': f"{sign} {format_money(amount)}",
                'amount_color': color_text,
                'balance': running_balance,
                'raw_type': p_type,
                'id': p_id
            })

        # 2. نمایش در جدول (معکوس: جدیدترین‌ها بالا)
        final_rows = processed_rows[::-1]
        table.setRowCount(len(final_rows))
        
        for row, data in enumerate(final_rows):
            table.setItem(row, 0, QTableWidgetItem(str(data['date'])))
            table.setItem(row, 1, QTableWidgetItem(data['type']))
            table.setItem(row, 2, QTableWidgetItem(str(data['party'])))
            table.setItem(row, 3, QTableWidgetItem(str(data['desc'])))
            
            # مبلغ
            amount_item = QTableWidgetItem(data['amount_str'])
            amount_item.setForeground(data['amount_color'])
            amount_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            table.setItem(row, 4, amount_item)
            
            # مانده
            bal_val = data['balance']
            balance_item = QTableWidgetItem(format_money(bal_val))
            balance_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            if bal_val < 0:
                balance_item.setForeground(QColor("#c0392b"))
            else:
                balance_item.setForeground(QColor("black"))
            table.setItem(row, 5, balance_item)

            # دکمه حذف
            editable_types = ['transfer', 'manual_payment', 'manual_receipt', 'capital_injection', 
                              'ManualPayment', 'ManualReceipt', 'CapitalInjection']
            
            if data['raw_type'] in editable_types:
                del_btn = QPushButton("حذف")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 4px; font-size: 11px; padding: 3px;")
                del_btn.clicked.connect(lambda _, pid=data['id'], d=dialog: self.delete_transaction(pid, d))
                
                widget = QWidget(); l = QHBoxLayout(widget); l.setContentsMargins(2,2,2,2); l.setAlignment(Qt.AlignCenter)
                l.addWidget(del_btn)
                table.setCellWidget(row, 6, widget)

        layout.addWidget(table)
        
        # بخش هشدار اختلاف موجودی
        current_inv_db = self.db_manager._execute_query("SELECT Inventory FROM Funds WHERE ID = ?", (fund_id,), fetch='one')
        real_db_balance = float(current_inv_db['Inventory']) if current_inv_db else 0.0
        calculated_balance = processed_rows[-1]['balance'] if processed_rows else 0.0
        
        # اگر اختلاف بیشتر از 1000 تومان بود
        if abs(real_db_balance - calculated_balance) > 1000:
            msg_frame = QWidget()
            msg_layout = QHBoxLayout(msg_frame)
            lbl_warning = QLabel(f"هشدار: موجودی دیتابیس ({format_money(real_db_balance)}) با جمع تراکنش‌ها ({format_money(calculated_balance)}) همخوانی ندارد.")
            lbl_warning.setStyleSheet("color: #c0392b; font-weight: bold;")
            
            fix_btn = QPushButton("همگام‌سازی موجودی")
            fix_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 5px 10px;")
            fix_btn.clicked.connect(lambda: self.fix_fund_balance(fund_id, calculated_balance, dialog))
            
            msg_layout.addWidget(lbl_warning)
            msg_layout.addWidget(fix_btn)
            layout.addWidget(msg_frame)

        dialog.exec_()

    # --- تابع تعمیر موجودی (اختیاری) ---
    def fix_fund_balance(self, fund_id, correct_balance, dialog):
        reply = QMessageBox.question(dialog, "تعمیر موجودی", 
                                     f"آیا می‌خواهید موجودی صندوق را به {format_money(correct_balance)} تغییر دهید؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_manager._execute_query("UPDATE Funds SET Inventory = ? WHERE ID = ?", (correct_balance, fund_id), commit=True)
            QMessageBox.information(dialog, "انجام شد", "موجودی اصلاح شد.")
            dialog.close()


    def delete_transaction(self, payment_id, dialog):
            reply = QMessageBox.question(
                dialog, "تایید حذف",
                "آیا مطمئن هستید که می‌خواهید این تراکنش را حذف کنید؟\nموجودی صندوق اصلاح خواهد شد.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                success, msg = self.db_manager.delete_manual_transaction(payment_id)
                if success:
                    QMessageBox.information(dialog, "موفقیت", "تراکنش حذف شد.")
                    dialog.accept() # بستن و باز کردن مجدد برای رفرش
                    # نکته: برای تجربه بهتر می‌توانیم متد show_transactions_dialog را دوباره صدا بزنیم
                else:
                    QMessageBox.critical(dialog, "خطا", msg)








