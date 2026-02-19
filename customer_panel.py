from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QAbstractItemView, QFrame,
    QComboBox, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon
from PyQt5.QtCore import Qt
from db_manager import DatabaseManager
from utils import format_money

# --- کلاس جدید برای نمایش دیالوگ تراکنش‌ها ---
class TransactionDialog(QDialog):
    def __init__(self, customer_data, db_manager, parent=None):
        super().__init__(parent)
        self.customer_data = customer_data
        self.db_manager = db_manager
        
        self.setWindowTitle(f"گردش حساب: {customer_data['FullName']}")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #f4f6f9; }
            QTableWidget {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 8px;
                selection-background-color: #e3f2fd;
                selection-color: #2d3436;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLabel { font-family: 'B Yekan'; }
        """)
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. هدر با اطلاعات خلاصه
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #dfe6e9;")
        h_layout = QHBoxLayout(header_frame)
        
        name_lbl = QLabel(f"👤 {self.customer_data['FullName']}")
        name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        
        # نمایش مانده حساب در هدر
        debt = self.customer_data.get('TotalDebt', 0)
        debt_text = format_money(abs(debt))
        status_text = "بدهکار" if debt > 0 else ("بستانکار" if debt < 0 else "تسویه")
        color = "#c0392b" if debt > 0 else ("#27ae60" if debt < 0 else "#7f8c8d")
        
        balance_lbl = QLabel(f"وضعیت فعلی: {debt_text} ({status_text})")
        balance_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        
        h_layout.addWidget(name_lbl)
        h_layout.addStretch()
        h_layout.addWidget(balance_lbl)
        
        layout.addWidget(header_frame)
        
        # 2. جدول تراکنش‌ها
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["تاریخ", "نوع", "مبلغ (ریال)", "توضیحات"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        layout.addWidget(self.table)
        
        # 3. دکمه بستن
        close_btn = QPushButton("بستن")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6; color: white; 
                padding: 8px 20px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        close_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def load_data(self):
        # دریافت اطلاعات از دیتابیس
        transactions = self.db_manager.get_customer_transactions(self.customer_data['ID'])
        
        self.table.setRowCount(0)
        self.table.setRowCount(len(transactions))
        
        for row, trans in enumerate(transactions):
            # تاریخ
            date_item = QTableWidgetItem(str(trans.get('Date', '')))
            self.table.setItem(row, 0, date_item)
            
            # نوع تراکنش
            p_type = trans.get('PaymentType', '-')
            type_item = QTableWidgetItem(p_type)
            self.table.setItem(row, 1, type_item)
            
            # مبلغ
            amount = trans.get('Amount', 0)
            amount_str = format_money(amount)
            amount_item = QTableWidgetItem(amount_str)
            amount_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            
            # توضیحات
            desc_item = QTableWidgetItem(trans.get('Description', ''))
            self.table.setItem(row, 3, desc_item)
            
            # رنگ بندی بر اساس ماهیت تراکنش
            # فرض می‌کنیم اگر توضیحات شامل کلمات خاصی باشد یا نوع آن مشخص باشد رنگ عوض شود
            # اینجا یک منطق ساده می‌گذاریم: همیشه سیاه، مگر اینکه منطق دقیق‌تری داشته باشیم
            # اما برای زیبایی، مبلغ را آبی می‌کنیم
            amount_item.setForeground(QColor("#2980b9"))
            self.table.setItem(row, 2, amount_item)

# --- کلاس اصلی پنل مشتریان (اصلاح شده) ---
class CustomerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setStyleSheet("""
            QWidget {
                font-family: "B Yekan", "Tahoma", sans-serif;
                font-size: 13px;
                color: #2d3436;
            }
            QFrame#StatCard {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dfe6e9;
            }
            QLabel#StatTitle {
                color: #636e72;
                font-size: 11px;
                font-weight: bold;
            }
            QLabel#StatValue {
                color: #2d3436;
                font-size: 16px;
                font-weight: 900;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 6px;
                selection-background-color: #e3f2fd;
                selection-color: #2d3436;
                outline: none;
            }
            QHeaderView::section {
                background-color: #f1f2f6;
                color: #2d3436;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dcdde1;
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f1f2f6;
            }
            QPushButton#ActionBtn {
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
                border: none;
            }
            QPushButton#EditBtn { background-color: #eaf6ff; color: #0984e3; }
            QPushButton#EditBtn:hover { background-color: #dbf0ff; }
            
            QPushButton#TransBtn { background-color: #fff8ea; color: #d35400; }
            QPushButton#TransBtn:hover { background-color: #ffedcc; }
            
            QPushButton#StoreBtn { background-color: #f3e5f5; color: #8e44ad; }
            QPushButton#StoreBtn:hover { background-color: #e1bee7; }

            QLineEdit {
                border: 1px solid #dfe6e9;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
            }
            QLineEdit:focus { border: 1px solid #74b9ff; }
            
            QPushButton#AddBtn {
                background-color: #00b894;
                color: white;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#AddBtn:hover { background-color: #00a884; }
        """)
        
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.lbl_total_customers = self.create_stat_card("کل مشتریان", "0", "#0984e3")
        self.lbl_total_debt = self.create_stat_card("جمع مطالبات", "0", "#d63031")
        self.lbl_active_debtors = self.create_stat_card("بدهکاران", "0", "#e17055")
        
        stats_layout.addWidget(self.lbl_total_customers)
        stats_layout.addWidget(self.lbl_total_debt)
        stats_layout.addWidget(self.lbl_active_debtors)
        
        main_layout.addLayout(stats_layout)

        toolbar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجو...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.refresh_data)
        
        add_btn = QPushButton("+ مشتری جدید")
        add_btn.setObjectName("AddBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: self.show_customer_form(None))
        
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(add_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8) 
        self.table.setHorizontalHeaderLabels([
            "کد", "نام مشتری", "کد ملی", "تلفن", 
            "آدرس", "جنسیت", "وضعیت مالی", "عملیات"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 240)
        
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        main_layout.addWidget(self.table)
        self.layout.addWidget(main_container)

    def create_stat_card(self, title, initial_value, icon_color):
        card = QFrame()
        card.setObjectName("StatCard")
        card.setFixedHeight(60)
        card.setGraphicsEffect(self.get_shadow())
        
        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        line = QFrame()
        line.setFixedWidth(4)
        line.setStyleSheet(f"background-color: {icon_color}; border-top-right-radius: 8px; border-bottom-right-radius: 8px;")
        
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(12, 5, 12, 5)
        text_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("StatTitle")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setObjectName("StatValue")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_value)
        
        main_layout.addWidget(line)
        main_layout.addWidget(text_container)
        main_layout.addStretch()
        
        return card

    def get_stat_value_label(self, card_frame):
        return card_frame.findChild(QLabel, "StatValue")

    def get_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 2)
        return shadow

    def refresh_data(self):
        search_query = self.search_input.text()
        all_customers = self.db_manager.get_customers_paginated(1, 100000, search_query)
        self.update_stats(all_customers)
        self.populate_table(all_customers)

    def update_stats(self, customers):
        total_count = len(customers)
        total_debt_sum = 0
        debtors_count = 0
        
        for c in customers:
            debt = c.get('TotalDebt', 0)
            if debt > 0:
                total_debt_sum += debt
                debtors_count += 1
                
        lbl_count = self.get_stat_value_label(self.lbl_total_customers)
        if lbl_count: lbl_count.setText(f"{total_count}")
        
        lbl_debt = self.get_stat_value_label(self.lbl_total_debt)
        if lbl_debt: lbl_debt.setText(format_money(total_debt_sum))
        
        lbl_active = self.get_stat_value_label(self.lbl_active_debtors)
        if lbl_active: lbl_active.setText(f"{debtors_count}")

    def populate_table(self, customers):
        self.table.setRowCount(0)
        self.table.setRowCount(len(customers))
        
        for row, customer in enumerate(customers):
            self.table.setItem(row, 0, QTableWidgetItem(str(customer.get('Code', ''))))
            
            name_item = QTableWidgetItem(customer.get('FullName', ''))
            name_item.setFont(QFont("B Yekan", 9, QFont.Bold))
            self.table.setItem(row, 1, name_item)
            
            self.table.setItem(row, 2, QTableWidgetItem(str(customer.get('NationalID', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(customer.get('PhoneNumber', ''))))
            
            addr = customer.get('Address', '')
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.table.setItem(row, 4, addr_item)
            
            self.table.setItem(row, 5, QTableWidgetItem(customer.get('Gender', '')))
            
            debt = customer.get('TotalDebt', 0)
            debt_str = format_money(debt)
            debt_item = QTableWidgetItem(debt_str)
            debt_item.setFont(QFont("B Yekan", 9, QFont.Bold))
            debt_item.setTextAlignment(Qt.AlignCenter)
            
            if debt > 0:
                debt_item.setForeground(QColor("#c0392b"))
            elif debt < 0:
                debt_item.setForeground(QColor("#2980b9"))
                debt_item.setText(f"{format_money(abs(debt))} (بستانکار)")
            else:
                debt_item.setForeground(QColor("#27ae60"))
                debt_item.setText("تسویه")
            self.table.setItem(row, 6, debt_item)
            
            actions_widget = QWidget()
            ac_layout = QHBoxLayout(actions_widget)
            ac_layout.setContentsMargins(0, 2, 0, 2)
            ac_layout.setSpacing(4)
            
            btn_edit = QPushButton("ویرایش")
            btn_edit.setObjectName("EditBtn")
            btn_edit.setObjectName("ActionBtn")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda _, c=customer: self.show_customer_form(c))
            
            btn_trans = QPushButton("تراکنش")
            btn_trans.setObjectName("TransBtn")
            btn_trans.setObjectName("ActionBtn")
            btn_trans.setCursor(Qt.PointingHandCursor)
            btn_trans.clicked.connect(lambda _, c=customer: self.show_transactions(c))
            
            ac_layout.addWidget(btn_edit)
            ac_layout.addWidget(btn_trans)
            
            if customer.get('PersonType') != 'تامین کننده':
                btn_store = QPushButton("فروشگاه")
                btn_store.setObjectName("StoreBtn")
                btn_store.setObjectName("ActionBtn")
                btn_store.setCursor(Qt.PointingHandCursor)
                btn_store.clicked.connect(lambda _, c=customer: self.show_convert_to_store_dialog(c))
                ac_layout.addWidget(btn_store)
            
            self.table.setCellWidget(row, 7, actions_widget)
            self.table.setRowHeight(row, 45)

    def show_customer_form(self, customer_data=None):
        is_edit = customer_data is not None
        dialog = QDialog(self)
        dialog.setWindowTitle("اطلاعات مشتری")
        dialog.setMinimumWidth(350)
        dialog.setStyleSheet("""
            QDialog { background-color: white; }
            QLineEdit, QComboBox { padding: 6px; border: 1px solid #dfe6e9; border-radius: 5px; }
            QLabel { font-weight: bold; color: #2d3436; font-size: 12px; }
        """)
        
        layout = QVBoxLayout(dialog)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        name_input = QLineEdit(customer_data.get('FullName', '') if is_edit else "")
        name_input.setPlaceholderText("نام و نام خانوادگی")
        
        nat_input = QLineEdit(customer_data.get('NationalID', '') if is_edit else "")
        nat_input.setPlaceholderText("کد ملی")
        
        phone_input = QLineEdit(customer_data.get('PhoneNumber', '') if is_edit else "")
        phone_input.setPlaceholderText("شماره موبایل")
        
        gender_combo = QComboBox()
        gender_combo.addItems(["آقا", "خانم"])
        if is_edit: gender_combo.setCurrentText(customer_data.get('Gender', 'آقا'))
        
        form_layout.addWidget(QLabel("نام:"))
        form_layout.addWidget(name_input)
        form_layout.addWidget(QLabel("کد ملی:"))
        form_layout.addWidget(nat_input)
        form_layout.addWidget(QLabel("تلفن:"))
        form_layout.addWidget(phone_input)
        form_layout.addWidget(QLabel("جنسیت:"))
        form_layout.addWidget(gender_combo)
        
        save_btn = QPushButton("ثبت اطلاعات")
        save_btn.setStyleSheet("background-color: #00b894; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        save_btn.clicked.connect(lambda: self.save_customer(dialog, is_edit, customer_data, name_input, nat_input, phone_input, gender_combo))
        
        layout.addLayout(form_layout)
        layout.addWidget(save_btn)
        dialog.exec_()

    def save_customer(self, dialog, is_edit, data, name_inp, nat_inp, phone_inp, gender_inp):
        name = name_inp.text()
        nid = nat_inp.text()
        ph = phone_inp.text()
        gen = gender_inp.currentText()
        
        if not all([name, nid, ph]):
            QMessageBox.warning(self, "خطا", "لطفا تمام فیلدها را پر کنید")
            return

        if is_edit:
            success = self.db_manager.update_customer(data['ID'], name, nid, ph, gen)
        else:
            success = self.db_manager.add_customer(name, nid, ph, gen)
            
        if success:
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "خطا", "خطا در برقراری ارتباط با دیتابیس")

    def show_transactions(self, customer_data):
        # اجرای دیالوگ جدید تراکنش‌ها
        dialog = TransactionDialog(customer_data, self.db_manager, self)
        dialog.exec_()

    def show_convert_to_store_dialog(self, customer_data):
        dialog = QDialog(self)
        dialog.setWindowTitle("تبدیل به فروشگاه")
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet("QDialog { background-color: white; } QLineEdit { padding: 6px; border: 1px solid #dfe6e9; border-radius: 5px; }")
        
        layout = QVBoxLayout(dialog)
        
        input_name = QLineEdit(customer_data['FullName'])
        input_addr = QLineEdit(customer_data.get('Address', ''))
        input_ph = QLineEdit(customer_data.get('PhoneNumber', ''))
        
        layout.addWidget(QLabel("نام فروشگاه:"))
        layout.addWidget(input_name)
        layout.addWidget(QLabel("آدرس:"))
        layout.addWidget(input_addr)
        layout.addWidget(QLabel("تلفن:"))
        layout.addWidget(input_ph)
        
        btn = QPushButton("تبدیل")
        btn.setStyleSheet("background-color: #8e44ad; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        btn.clicked.connect(lambda: self.perform_convert(dialog, customer_data['ID'], input_name.text(), input_addr.text(), input_ph.text()))
        
        layout.addWidget(btn)
        dialog.exec_()

    def perform_convert(self, dialog, cid, name, addr, ph):
        success, msg = self.db_manager.convert_person_to_store(cid, name, addr, ph)
        if success:
            QMessageBox.information(self, "موفقیت", "تبدیل انجام شد")
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "خطا", msg)