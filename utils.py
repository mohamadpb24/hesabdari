# utils.py

import jdatetime
from PyQt5.QtCore import QDate

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