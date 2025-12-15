# report_generator.py

import os
import sys
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from bidi.algorithm import get_display
import arabic_reshaper

# =========================================================
# 1. تنظیمات هوشمند فونت
# =========================================================

def find_font_path(font_filename):
    """
    مسیر فایل فونت را در مکان‌های احتمالی جستجو می‌کند.
    """
    # لیست مکان‌های جستجو
    search_paths = [
        os.getcwd(),  # پوشه فعلی برنامه
        os.path.dirname(os.path.abspath(__file__)), # پوشه اسکریپت
        os.path.expanduser("~/.fonts"), # پوشه فونت کاربر لینوکس
        os.path.expanduser("~/.local/share/fonts"), # مسیر دیگر لینوکس
        "/usr/share/fonts", # مسیر سیستمی
        "/usr/share/fonts/truetype/vazir", # مسیر احتمالی نصب پکیج
    ]

    for path in search_paths:
        full_path = os.path.join(path, font_filename)
        if os.path.exists(full_path):
            return full_path
    return None

# تلاش برای بارگذاری فونت‌ها
FONT_REGULAR = 'Vazir'
FONT_BOLD = 'Vazir-Bold'
font_loaded = False

try:
    # جستجوی فونت معمولی
    regular_path = find_font_path('Vazir.ttf') or find_font_path('vazir.ttf')
    if regular_path:
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular_path))
        print(f"✅ فونت معمولی یافت شد: {regular_path}")
        font_loaded = True
    else:
        print("❌ خطا: فایل Vazir.ttf یافت نشد.")
        FONT_REGULAR = 'Helvetica'

    # جستجوی فونت ضخیم
    bold_path = find_font_path('Vazir-Bold.ttf') or find_font_path('vazir-bold.ttf')
    if bold_path:
        pdfmetrics.registerFont(TTFont(FONT_BOLD, bold_path))
        print(f"✅ فونت ضخیم یافت شد: {bold_path}")
    else:
        print("❌ خطا: فایل Vazir-Bold.ttf یافت نشد.")
        FONT_BOLD = 'Helvetica-Bold'

except Exception as e:
    print(f"Critical Font Error: {e}")
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'


def prepare_persian_text(text):
    """
    متن فارسی را برای نمایش صحیح در PDF آماده می‌کند.
    1. تبدیل به رشته
    2. تغییر شکل حروف (Reshape) برای چسبیدن حروف
    3. اعمال الگوریتم Bidi برای راست‌چین شدن
    """
    if text is None:
        return ""
    
    text = str(text)
    
    # اگر متن خالی یا فقط عدد است، نیازی به reshape سنگین ندارد اما bidi لازم است
    if not text.strip():
        return ""

    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

def format_money(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

def get_report_styles():
    styles = getSampleStyleSheet()
    
    # استایل عنوان اصلی
    styles.add(ParagraphStyle(
        name='PersianTitle',
        fontName=FONT_BOLD,  # حتما باید فونت فارسی باشد
        fontSize=18,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=20
    ))
    
    # استایل زیرنویس
    styles.add(ParagraphStyle(
        name='PersianSubtitle',
        fontName=FONT_REGULAR,
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.darkgray
    ))

    # استایل هدر جدول
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName=FONT_BOLD,
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.whitesmoke
    ))

    # استایل سلول‌های معمولی
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName=FONT_REGULAR,
        fontSize=10, # کمی بزرگتر برای خوانایی
        leading=14,
        alignment=TA_CENTER
    ))
    
    # استایل سلول راست‌چین (برای توضیحات)
    styles.add(ParagraphStyle(
        name='TableCellRight',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        alignment=TA_RIGHT
    ))

    # تیترهای داخلی
    styles.add(ParagraphStyle(
        name='H3_Right',
        fontName=FONT_BOLD,
        fontSize=12,
        alignment=TA_RIGHT,
        spaceBefore=15,
        spaceAfter=5,
        textColor=colors.HexColor('#2c3e50')
    ))

    return styles

# =========================================================
# 2. گزارش پرونده مشتری
# =========================================================
def create_single_customer_report(customer_data, loans, installments_by_loan, file_path, selected_loan_id=None):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = get_report_styles()
        elements = []

        title_text = f"پرونده مالی: {customer_data['name']}"
        elements.append(Paragraph(prepare_persian_text(title_text), styles['PersianTitle']))
        
        info_text = f"کد ملی: {customer_data.get('national_code', '-') or '-'}   |   تلفن: {customer_data.get('phone_number', '-') or '-'}"
        elements.append(Paragraph(prepare_persian_text(info_text), styles['PersianSubtitle']))
        elements.append(Spacer(1, 10))

        if not loans:
            elements.append(Paragraph(prepare_persian_text("هیچ وامی یافت نشد."), styles['TableCell']))
            doc.build(elements)
            return True

        for loan in loans:
            # هندل کردن دیکشنری یا تاپل
            if isinstance(loan, dict):
                l_id = loan['ID']; l_code = loan['Code']; l_amount = loan['Amount']; l_status = loan['Status']
            else:
                l_id = loan[0]; l_code = loan[1]; l_amount = loan[2]; l_status = "Unknown"

            if selected_loan_id and selected_loan_id != "all" and str(l_id) != str(selected_loan_id):
                continue

            status_fa = "تسویه شده" if l_status == 'FULLY_SETTLED' else "فعال"
            loan_header = f"وام شماره {l_code}  -  مبلغ: {format_money(l_amount)}  -  وضعیت: {status_fa}"
            elements.append(Paragraph(prepare_persian_text(loan_header), styles['H3_Right']))

            inst_list = installments_by_loan.get(l_id, [])
            if inst_list:
                headers = ["#", "سررسید", "پرداخت", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]
                data = [[Paragraph(prepare_persian_text(h), styles['TableHeader']) for h in headers]]
                
                for idx, inst in enumerate(inst_list):
                    if isinstance(inst, dict):
                        due_date = str(inst['DueDate'])
                        pay_date = str(inst['PaymentDate']) if inst['PaymentDate'] else "-"
                        due_amt = inst['DueAmount']; paid_amt = inst['PaidAmount']; remain = inst['PaymentRemain']
                        status_code = inst['Status']
                    else:
                        continue 

                    status_map = {30: "موعد نرسیده", 31: "سررسید امروز", 32: "پرداخت شده", 
                                  33: "پرداخت ناقص", 34: "ناقص با جریمه", 35: "پرداخت با تاخیر",
                                  36: "پرداخت با جریمه", 37: "معوق (تنفس)", 38: "معوق", 39: "مشکوک", 40: "حقوقی"}
                    st_text = status_map.get(status_code, str(status_code))

                    row = [
                        Paragraph(str(idx + 1), styles['TableCell']),
                        Paragraph(prepare_persian_text(due_date), styles['TableCell']),
                        Paragraph(prepare_persian_text(pay_date), styles['TableCell']),
                        Paragraph(format_money(due_amt), styles['TableCell']),
                        Paragraph(format_money(paid_amt), styles['TableCell']),
                        Paragraph(format_money(remain), styles['TableCell']),
                        Paragraph(prepare_persian_text(st_text), styles['TableCell']),
                    ]
                    data.append(row)

                col_widths = [30, 70, 70, 80, 80, 80, 80]
                table = Table(data, colWidths=col_widths, repeatRows=1)
                
                ts = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]
                for i in range(1, len(data)):
                    bg = colors.whitesmoke if i % 2 == 0 else colors.white
                    ts.append(('BACKGROUND', (0, i), (-1, i), bg))
                
                table.setStyle(TableStyle(ts))
                elements.append(table)
                elements.append(Spacer(1, 15))
            else:
                elements.append(Paragraph(prepare_persian_text("بدون قسط ثبت شده."), styles['TableCellRight']))
                elements.append(Spacer(1, 15))

        doc.build(elements)
        return True

    except Exception as e:
        print(f"Error creating customer report: {e}")
        return False

# =========================================================
# 3. گزارش جامع اقساط
# =========================================================
def create_installments_report(installments_data, start_date, end_date, status, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(A4))
        styles = get_report_styles()
        elements = []

        elements.append(Paragraph(prepare_persian_text("گزارش جامع اقساط"), styles['PersianTitle']))
        subtitle = f"بازه زمانی: {start_date} تا {end_date}  |  فیلتر: {status}"
        elements.append(Paragraph(prepare_persian_text(subtitle), styles['PersianSubtitle']))
        elements.append(Spacer(1, 10))

        headers = ["ردیف", "مشتری", "کد پرونده", "کد قسط", "سررسید", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]
        data = [[Paragraph(prepare_persian_text(h), styles['TableHeader']) for h in headers]]

        total_due = 0; total_paid = 0
        status_map = {30: "موعد نرسیده", 31: "سررسید", 32: "پرداخت شده", 
                      33: "ناقص", 34: "ناقص", 35: "تاخیر",
                      36: "جریمه", 37: "معوق", 38: "معوق", 39: "مشکوک", 40: "حقوقی"}

        for idx, inst in enumerate(installments_data):
            due = float(inst.get('amount_due', 0))
            paid = float(inst.get('paid_amount', 0))
            rem = due - paid
            total_due += due; total_paid += paid
            
            st_code = inst.get('status', 0)
            st_text = status_map.get(st_code, str(st_code))
            
            customer = inst.get('customer_name', '-')
            loan_code = inst.get('loan_readable_id', '-')
            inst_code = inst.get('code', '-')
            due_date = str(inst.get('due_date', '-'))

            row = [
                Paragraph(str(idx + 1), styles['TableCell']),
                Paragraph(prepare_persian_text(customer), styles['TableCell']),
                Paragraph(prepare_persian_text(str(loan_code)), styles['TableCell']),
                Paragraph(prepare_persian_text(str(inst_code)), styles['TableCell']),
                Paragraph(prepare_persian_text(due_date), styles['TableCell']),
                Paragraph(format_money(due), styles['TableCell']),
                Paragraph(format_money(paid), styles['TableCell']),
                Paragraph(format_money(rem), styles['TableCell']),
                Paragraph(prepare_persian_text(st_text), styles['TableCell']),
            ]
            data.append(row)

        # ردیف جمع کل
        total_row = [
            Paragraph(prepare_persian_text("جمع کل"), styles['TableHeader']),
            "", "", "", "",
            Paragraph(format_money(total_due), styles['TableHeader']),
            Paragraph(format_money(total_paid), styles['TableHeader']),
            Paragraph(format_money(total_due - total_paid), styles['TableHeader']),
            ""
        ]
        data.append(total_row)

        col_widths = [30, 130, 80, 80, 70, 90, 90, 90, 80]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2c3e50')),
            ('SPAN', (0, -1), (4, -1)),
        ]
        
        for i in range(1, len(data)-1):
            bg = colors.whitesmoke if i % 2 == 0 else colors.white
            ts.append(('BACKGROUND', (0, i), (-1, i), bg))

        table.setStyle(TableStyle(ts))
        elements.append(table)
        doc.build(elements)
        return True

    except Exception as e:
        print(f"Error creating installments report: {e}")
        return False

# =========================================================
# 4. گزارش صندوق
# =========================================================
def create_cashbox_report(cashbox_data, transactions, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = get_report_styles()
        elements = []

        box_name = cashbox_data.get('name', 'ناشناس')
        elements.append(Paragraph(prepare_persian_text(f"گردش حساب صندوق: {box_name}"), styles['PersianTitle']))
        elements.append(Spacer(1, 10))

        if not transactions:
            elements.append(Paragraph(prepare_persian_text("هیچ تراکنشی یافت نشد."), styles['TableCell']))
            doc.build(elements)
            return True

        headers = ["تاریخ", "نوع", "طرف حساب", "شرح", "مبلغ"]
        data = [[Paragraph(prepare_persian_text(h), styles['TableHeader']) for h in headers]]

        type_map = {
            'LoanPayment': 'پرداخت وام', 'InstallmentPayment': 'دریافت قسط',
            'TransfertoStore': 'انتقال اعتباری', 'StorePayment': 'پرداخت به فروشگاه',
            'Expense': 'هزینه', 'Settlement': 'تسویه وام', 'transfer': 'انتقال وجه',
            'manual_payment': 'پرداخت دستی', 'ManualPayment': 'پرداخت دستی',
            'manual_receipt': 'دریافت دستی', 'ManualReceipt': 'دریافت دستی',
            'capital_injection': 'افزایش سرمایه', 'CapitalInjection': 'افزایش سرمایه'
        }

        output_types = ['LoanPayment', 'ManualPayment', 'manual_payment', 'Expense', 'StorePayment']
        fund_id = cashbox_data.get('id')

        for trans in transactions:
            t_date = str(trans.get('Date', '-'))
            t_raw_type = trans.get('Type', '')
            t_desc = trans.get('Description', '')
            t_amount = float(trans.get('Amount', 0))
            t_party = trans.get('Counterparty', '')
            
            is_income = True
            if t_raw_type in output_types:
                is_income = False
            elif t_raw_type == 'transfer' and trans.get('Fund_ID') == fund_id:
                is_income = False
            
            t_type_fa = type_map.get(t_raw_type, t_raw_type)
            if t_raw_type == 'transfer':
                t_type_fa += " (ورودی)" if is_income else " (خروجی)"

            formatted_amt = format_money(t_amount)
            if is_income:
                amt_str = f"+ {formatted_amt}"
                amt_color = "green"
            else:
                amt_str = f"- {formatted_amt}"
                amt_color = "red"
            
            amt_paragraph = Paragraph(f'<font color="{amt_color}">{amt_str}</font>', styles['TableCell'])

            row = [
                Paragraph(prepare_persian_text(t_date), styles['TableCell']),
                Paragraph(prepare_persian_text(t_type_fa), styles['TableCell']),
                Paragraph(prepare_persian_text(str(t_party)), styles['TableCell']),
                Paragraph(prepare_persian_text(str(t_desc)), styles['TableCellRight']),
                amt_paragraph
            ]
            data.append(row)

        col_widths = [70, 90, 100, 150, 90]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]
        
        for i in range(1, len(data)):
            bg = colors.whitesmoke if i % 2 == 0 else colors.white
            ts.append(('BACKGROUND', (0, i), (-1, i), bg))

        table.setStyle(TableStyle(ts))
        elements.append(table)

        doc.build(elements)
        return True

    except Exception as e:
        print(f"Error creating cashbox report: {e}")
        return False