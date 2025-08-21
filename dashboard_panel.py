# dashboard_panel.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class DashboardPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("پنل داشبورد (در حال پیاده‌سازی)")
        label.setFont(QFont("B Yekan", 14, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def refresh_data(self):
        # این تابع بعداً برای بارگذاری اطلاعات آماری تکمیل می‌شود
        pass