# manual_transaction_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFormLayout, QComboBox, QLineEdit, QMessageBox
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
import jdatetime

from db_manager import DatabaseManager
from utils import format_money

class ManualTransactionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.setContentsMargins(30, 25, 30, 25)
        self.build_ui()

    def build_ui(self):
        self.setStyleSheet("background-color: transparent;")

        title_label = QLabel("ایجاد تراکنش دستی")
        title_label.setFont(QFont("B Yekan", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("margin-bottom: 20px;")
        self.main_layout.addWidget(title_label)

        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(15)
        self.form_layout.setLabelAlignment(Qt.AlignRight)

        self.trans_type_combo = QComboBox()
        self.trans_type_combo.addItems([
            "لطفا نوع تراکنش را انتخاب کنید...",
            "انتقال بین صندوق‌ها",
            "پرداخت به مشتری (ایجاد بدهی)",
            "دریافت از مشتری (تسویه بدهی)",
            "افزایش سرمایه"  # <-- گزینه جدید
        ])
        self.trans_type_combo.currentIndexChanged.connect(self.update_form)
        self.form_layout.addRow("نوع تراکنش:", self.trans_type_combo)

        self.source_label = QLabel("از (مبدا):")
        self.source_combo = QComboBox()
        self.destination_label = QLabel("به (مقصد):")
        self.destination_combo = QComboBox()
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ به تومان")
        self.amount_input.textChanged.connect(self._format_amount_input)
        self.date_input = QLineEdit(jdatetime.date.today().strftime('%Y/%m/%d'))
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("مثال: واریز سرمایه توسط شریک...")

        self.form_layout.addRow(self.source_label, self.source_combo)
        self.form_layout.addRow(self.destination_label, self.destination_combo)
        self.form_layout.addRow("مبلغ:", self.amount_input)
        self.form_layout.addRow("تاریخ:", self.date_input)
        self.form_layout.addRow("شرح:", self.description_input)

        self.save_btn = QPushButton("ثبت تراکنش")
        self.save_btn.setFont(QFont("B Yekan", 12, QFont.Bold))
        self.save_btn.setIcon(QIcon.fromTheme("emblem-ok"))
        self.save_btn.setMinimumHeight(45)
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #2c3e50; color: white; }
            QPushButton:hover { background-color: #34495e; }
        """)
        self.save_btn.clicked.connect(self.process_transaction)
        self.form_layout.addRow(self.save_btn)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addStretch()
        self.update_form()

    def _format_amount_input(self, text):
        try:
            clean_text = text.replace("،", "")
            if clean_text.isdigit() and clean_text:
                formatted_text = f"{int(clean_text):,}".replace(",", "،")
                if self.amount_input.text() != formatted_text:
                    self.amount_input.setText(formatted_text)
                    self.amount_input.setCursorPosition(len(formatted_text))
            elif not clean_text:
                self.amount_input.clear()
        except Exception:
            pass

    def refresh_data(self):
        self.trans_type_combo.setCurrentIndex(0)
        self.amount_input.clear()
        self.description_input.clear()
        self.date_input.setText(jdatetime.date.today().strftime('%Y/%m/%d'))
        self.update_form()

    def update_form(self):
        trans_type_index = self.trans_type_combo.currentIndex()
        is_visible = trans_type_index != 0

        # نمایش یا مخفی کردن همه فیلدها
        for i in range(1, self.form_layout.rowCount()):
            self.form_layout.itemAt(i, QFormLayout.FieldRole).widget().setVisible(is_visible)
            label_item = self.form_layout.itemAt(i, QFormLayout.LabelRole)
            if label_item and label_item.widget():
                label_item.widget().setVisible(is_visible)

        self.source_combo.clear()
        self.destination_combo.clear()

        if not is_visible:
            return

        cashboxes = self.db_manager.get_all_cash_boxes()
        customers = self.db_manager.get_all_customers()

        # تنظیمات بر اساس نوع تراکنش
        if trans_type_index == 1: # انتقال بین صندوق‌ها
            self.source_label.setText("از صندوق:")
            self.destination_label.setText("به صندوق:")
            self.source_label.setVisible(True)
            self.source_combo.setVisible(True)
            for box_id, name, balance in cashboxes:
                self.source_combo.addItem(f"{name} ({format_money(balance)})", box_id)
                self.destination_combo.addItem(f"{name} ({format_money(balance)})", box_id)
        
        elif trans_type_index == 2: # پرداخت به مشتری
            self.source_label.setText("از صندوق:")
            self.destination_label.setText("به مشتری:")
            self.source_label.setVisible(True)
            self.source_combo.setVisible(True)
            for box_id, name, balance in cashboxes:
                self.source_combo.addItem(f"{name} ({format_money(balance)})", box_id)
            for customer_id, name in customers:
                self.destination_combo.addItem(name, customer_id)

        elif trans_type_index == 3: # دریافت از مشتری
            self.source_label.setText("از مشتری:")
            self.destination_label.setText("به صندوق:")
            self.source_label.setVisible(True)
            self.source_combo.setVisible(True)
            for customer_id, name in customers:
                self.source_combo.addItem(name, customer_id)
            for box_id, name, balance in cashboxes:
                self.destination_combo.addItem(f"{name} ({format_money(balance)})", box_id)

        elif trans_type_index == 4: # افزایش سرمایه
            self.source_label.setVisible(False) # مبدا خارجی است
            self.source_combo.setVisible(False)
            self.destination_label.setText("به صندوق:")
            for box_id, name, balance in cashboxes:
                self.destination_combo.addItem(f"{name} ({format_money(balance)})", box_id)

    def process_transaction(self):
        trans_type_index = self.trans_type_combo.currentIndex()
        if trans_type_index == 0:
            QMessageBox.warning(self, "خطا", "لطفا نوع تراکنش را انتخاب کنید.")
            return

        source_id = self.source_combo.currentData()
        destination_id = self.destination_combo.currentData()
        amount_str = self.amount_input.text().replace("،", "")
        date = self.date_input.text()
        description = self.description_input.text()

        # اعتبارسنجی برای افزایش سرمایه که مبدا ندارد
        if trans_type_index == 4:
            if not all([destination_id, amount_str, date, description]):
                QMessageBox.warning(self, "خطا", "لطفا تمام فیلدهای لازم را پر کنید.")
                return
            source_id = None # مبدا خارجی است
        else:
            if not all([source_id, destination_id, amount_str, date, description]):
                QMessageBox.warning(self, "خطا", "لطفا تمام فیلدها را پر کنید.")
                return
            if source_id == destination_id:
                QMessageBox.warning(self, "خطا", "مبدا و مقصد نمی‌توانند یکسان باشند.")
                return

        try:
            amount = int(amount_str)
            if amount <= 0: raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ باید یک عدد صحیح و مثبت باشد.")
            return
            
        trans_type_map = {
            1: "transfer",
            2: "manual_payment",
            3: "manual_receipt",
            4: "capital_injection"
        }
        trans_type = trans_type_map[trans_type_index]

        success, message = self.db_manager.add_manual_transaction(
            trans_type, amount, date, source_id, destination_id, description
        )

        if success:
            QMessageBox.information(self, "موفقیت", "تراکنش با موفقیت ثبت شد.")
            self.refresh_data()
        else:
            QMessageBox.critical(self, "خطا", f"خطا در ثبت تراکنش:\n{message}")
