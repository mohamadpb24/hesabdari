# utils.py

import jdatetime
from PyQt5.QtCore import QDate
from datetime import datetime as python_datetime # <-- ایمپورت جدید
def format_money(value):
    try:
        # تبدیل مقدار به عدد صحیح و فرمت‌دهی با جداکننده هزارتایی
        # از f-string با فرمت‌دهی محلی استفاده می‌کنیم
        return f"{int(value):,}".replace(",", "،") + " تومان"
    except (ValueError, TypeError):
        # اگر مقدار قابل تبدیل به عدد نبود، همان مقدار را برمی‌گرداند
        return str(value)

def jalali_to_gregorian(jalali_date_str):
    try:
        j_year, j_month, j_day = map(int, jalali_date_str.split('/'))
        g_date = jdatetime.date(j_year, j_month, j_day).togregorian()
        return QDate(g_date.year, g_date.month, g_date.day)
    except (ValueError, IndexError):
        return QDate.currentDate()

def gregorian_to_jalali(gregorian_date):
    g_year, g_month, g_day = gregorian_date.year(), gregorian_date.month(), gregorian_date.day()
    j_date = jdatetime.date.fromgregorian(year=g_year, month=g_month, day=g_day)
    return j_date.strftime('%Y/%m/%d')

def j_daysinmonth(year, month):
    if month < 7:
        return 31
    elif month < 12:
        return 30
    else: # ماه دوازدهم (اسفند)
        # فراخوانی صحیح تابع isleap
        if jdatetime.date(year, 1, 1).isleap():
            return 30
        else:
            return 29

def add_months_jalali(date_jalali, months):
    year = date_jalali.year
    month = date_jalali.month
    day = date_jalali.day
    
    # محاسبه ماه و سال جدید
    total_months = year * 12 + month - 1 + months
    new_year = total_months // 12
    new_month = total_months % 12 + 1
    
    # مدیریت تعداد روزهای ماه با استفاده از تابع جدید
    last_day_of_month = j_daysinmonth(new_year, new_month)
    new_day = min(day, last_day_of_month)
    
    return jdatetime.date(new_year, new_month, new_day)

def normalize_numbers(text):
    """تبدیل اعداد فارسی و جداکننده‌های فارسی به انگلیسی."""
    if not isinstance(text, str):
        text = str(text)
    
    # تبدیل ارقام فارسی به انگلیسی
    mapping = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    normalized_text = text.translate(mapping)
    
    # تبدیل جداکننده‌های هزارتایی و اعشاری فارسی به انگلیسی برای float شدن
    # حذف جداکننده‌های هزارتایی (فارسی و انگلیسی)
    normalized_text = normalized_text.replace("،", "")
    normalized_text = normalized_text.replace(",", "")
    # جایگزینی جداکننده اعشاری فارسی (٫) با نقطه
    normalized_text = normalized_text.replace("٫", ".")
    
    return normalized_text

def jalali_date_to_datetime_with_current_time(jalali_date_str: str) -> python_datetime:
    """
    تبدیل تاریخ شمسی (YYYY/MM/DD) به آبجکت datetime پایتون با ترکیب با زمان فعلی سیستم.
    """
    from jdatetime import datetime as jdatetime_datetime
    
    try:
        # 1. نرمالایز کردن ارقام و پارس کردن تاریخ شمسی
        normalized_date_str = normalize_numbers(jalali_date_str)
        j_parts = [int(p) for p in normalized_date_str.split('/')]
        j_date = jdatetime_datetime(j_parts[0], j_parts[1], j_parts[2]).date()
        
        # 2. گرفتن تاریخ میلادی معادل
        g_date = j_date.togregorian()
        
        # 3. ترکیب با زمان دقیق فعلی
        now = python_datetime.now()
        
        return python_datetime(g_date.year, g_date.month, g_date.day, 
                               now.hour, now.minute, now.second, now.microsecond)
    except Exception:
        # در صورت بروز خطا در پارس کردن، تاریخ و زمان فعلی را برمی‌گرداند.
        return python_datetime.now()





        
