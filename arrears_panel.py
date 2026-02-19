from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QMessageBox, QGraphicsDropShadowEffect, QAbstractItemView
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
import jdatetime
from db_manager import DatabaseManager
from utils import format_money

class ArrearsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        
        # لی‌اوت اصلی
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # استایل مدرن
        self.setStyleSheet("""
            QWidget { font-family: "B Yekan"; font-size: 13px; color: #2d3436; }
            QFrame#FilterBox { background-color: white; border-radius: 8px; border: 1px solid #dfe6e9; }
            QTableWidget { background-color: white; border-radius: 8px; border: 1px solid #dfe6e9; outline: none; }
            QHeaderView::section { background-color: #f1f2f6; border: none; padding: 10px; font-weight: bold; color: #636e72; }
            QTableWidget::item { padding: 5px; border-bottom: 1px solid #f1f2f6; }
            QLabel#StatValue { font-size: 20px; font-weight: 900; }
            QLineEdit { padding: 8px; border: 1px solid #dfe6e9; border-radius: 5px; min-width: 120px; }
            QLineEdit:focus { border: 1px solid #3498db; }
            QPushButton { border-radius: 5px; padding: 8px 15px; font-weight: bold; cursor: pointer; }
            QPushButton#FilterBtn { background-color: #3498db; color: white; }
            QPushButton#FilterBtn:hover { background-color: #2980b9; }
            QPushButton#TodayBtn { background-color: #e74c3c; color: white; }
            QPushButton#TodayBtn:hover { background-color: #c0392b; }
        """)
        
        self.setup_ui()
        # به صورت پیش‌فرض معوقات تا امروز را لود کن
        self.set_filter_until_today()

    def setup_ui(self):
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(20)
        
        # --- ۱. کارت‌های آمار ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.lbl_total_arrears = self.create_stat_card("مبلغ کل معوقات", "0 ریال", "#c0392b")
        self.lbl_count_arrears = self.create_stat_card("تعداد پرونده‌های باز", "0 فقره", "#e67e22")
        
        stats_layout.addWidget(self.lbl_total_arrears)
        stats_layout.addWidget(self.lbl_count_arrears)
        stats_layout.addStretch() # هل دادن کارت‌ها به راست
        
        main_layout.addLayout(stats_layout)
        
        # --- ۲. فیلترها ---
        filter_frame = QFrame()
        filter_frame.setObjectName("FilterBox")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(10)
        
        # ورودی‌های تاریخ (متنی ساده برای راحتی)
        self.txt_start = QLineEdit()
        self.txt_start.setPlaceholderText("از تاریخ (1402/01/01)")
        self.txt_start.setAlignment(Qt.AlignCenter)
        
        self.txt_end = QLineEdit()
        self.txt_end.setPlaceholderText("تا تاریخ")
        self.txt_end.setAlignment(Qt.AlignCenter)
        
        btn_filter = QPushButton("نمایش گزارش")
        btn_filter.setObjectName("FilterBtn")
        btn_filter.clicked.connect(self.refresh_report)
        
        btn_today_back = QPushButton("معوقات تا امروز")
        btn_today_back.setObjectName("TodayBtn")
        btn_today_back.clicked.connect(self.set_filter_until_today)

        filter_layout.addWidget(QLabel("بازه زمانی:"))
        filter_layout.addWidget(self.txt_start)
        filter_layout.addWidget(QLabel("تا"))
        filter_layout.addWidget(self.txt_end)
        filter_layout.addWidget(btn_filter)
        filter_layout.addWidget(btn_today_back)
        filter_layout.addStretch()
        
        main_layout.addWidget(filter_frame)
        
        # --- ۳. جدول ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "نام مشتری", "شماره تماس", "تاریخ سررسید", 
            "تاخیر (روز)", "مبلغ قسط", "مانده پرداخت نشده", "وضعیت"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # نام
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # تاخیر
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # مانده
        
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        main_layout.addWidget(self.table)
        self.layout.addWidget(container)

    def create_stat_card(self, title, initial_val, color):
        card = QFrame()
        card.setStyleSheet(f"background-color: white; border-radius: 10px; border-right: 5px solid {color};")
        card.setFixedHeight(80)
        card.setFixedWidth(250)
        
        # سایه
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 12px;")
        
        lbl_val = QLabel(initial_val)
        lbl_val.setObjectName("StatValue")
        lbl_val.setStyleSheet(f"color: {color};")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card

    def set_filter_until_today(self):
        """تنظیم خودکار تاریخ برای دیدن تمام معوقات از گذشته تا امروز"""
        today = jdatetime.date.today().strftime("%Y/%m/%d")
        # تاریخ شروع: ۱۰ سال پیش (تا همه اقساط قدیمی هم بیاید)
        past = "1390/01/01" 
        
        self.txt_start.setText(past)
        self.txt_end.setText(today)
        self.refresh_report()

    def refresh_report(self):
        s_date = self.txt_start.text()
        e_date = self.txt_end.text()
        
        if not s_date or not e_date:
            QMessageBox.warning(self, "خطا", "لطفا بازه تاریخ را وارد کنید")
            return
            
        data = self.db_manager.get_arrears_report(s_date, e_date)
        self.populate_table(data)

    def populate_table(self, data):
        self.table.setRowCount(0)
        self.table.setRowCount(len(data))
        
        total_arrears_sum = 0
        today_g = jdatetime.date.today().togregorian()
        
        for row, item in enumerate(data):
            # محاسبه تاخیر
            due_date_str = str(item['DueDate'])
            try:
                # تبدیل تاریخ شمسی استرینگ به میلادی برای محاسبه ریاضی
                y, m, d = map(int, self.db_manager._normalize_persian_numbers(due_date_str).split('/'))
                due_date_g = jdatetime.date(y, m, d).togregorian()
                days_late = (today_g - due_date_g).days
            except:
                days_late = 0
            
            # 1. نام
            self.table.setItem(row, 0, QTableWidgetItem(item['FullName']))
            
            # 2. تلفن
            self.table.setItem(row, 1, QTableWidgetItem(item['PhoneNumber']))
            
            # 3. سررسید
            self.table.setItem(row, 2, QTableWidgetItem(due_date_str))
            
            # 4. تاخیر (مهم)
            late_text = f"{days_late} روز" if days_late > 0 else "---"
            late_item = QTableWidgetItem(late_text)
            late_item.setTextAlignment(Qt.AlignCenter)
            if days_late > 0:
                late_item.setForeground(QColor("#c0392b")) # قرمز جیغ
                late_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            self.table.setItem(row, 3, late_item)
            
            # 5. مبلغ قسط
            self.table.setItem(row, 4, QTableWidgetItem(format_money(item['DueAmount'])))
            
            # 6. مانده (برای محاسبه جمع کل)
            remain = item['PaymentRemain']
            total_arrears_sum += remain
            
            remain_item = QTableWidgetItem(format_money(remain))
            remain_item.setFont(QFont("B Yekan", 10, QFont.Bold))
            remain_item.setForeground(QColor("#c0392b"))
            self.table.setItem(row, 5, remain_item)
            
            # 7. وضعیت
            status_text = "ناقص" if remain < item['DueAmount'] else "پرداخت نشده"
            if days_late > 0:
                status_text += f" (معوق)"
            self.table.setItem(row, 6, QTableWidgetItem(status_text))
            
        # آپدیت کارت‌های بالا
        self.lbl_total_arrears.findChild(QLabel, "StatValue").setText(format_money(total_arrears_sum))
        self.lbl_count_arrears.findChild(QLabel, "StatValue").setText(f"{len(data)} فقره")