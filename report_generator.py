import jdatetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from bidi.algorithm import get_display
import arabic_reshaper

# --- توابع کمکی ---
def format_money_for_report(value):
    try:
        return f"{int(value):,}".replace(",", "،")
    except (ValueError, TypeError):
        return str(value)

def prepare_persian_text(text):
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

# ثبت فونت
try:
    pdfmetrics.registerFont(TTFont('Vazir-Bold', 'Vazir-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Vazir', 'Vazir.ttf'))
except Exception as e:
    print(f"هشدار: فونت Vazir.ttf یافت نشد. از فونت جایگزین استفاده می‌شود. خطا: {e}")
    pdfmetrics.registerFont(TTFont('Vazir-Bold', 'tahoma.ttf'))
    pdfmetrics.registerFont(TTFont('Vazir', 'tahoma.ttf'))


# --- تابع ساخت گزارش لیست مشتریان ---
def create_customers_report(customers_data, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()
        styles['h1'].fontName = 'Vazir-Bold'
        styles['Normal'].fontName = 'Vazir'
        styles['h1'].alignment = TA_RIGHT

        report_title = prepare_persian_text("گزارش لیست مشتریان")
        elements.append(Paragraph(report_title, styles['h1']))
        elements.append(Spacer(1, 15))

        today_date = jdatetime.date.today().strftime('%Y/%m/%d')
        date_text = prepare_persian_text(f"تاریخ گزارش: {today_date}")
        elements.append(Paragraph(date_text, styles['Normal']))
        elements.append(Spacer(1, 15))

        header = ["نام و نام خانوادگی", "کد ملی", "شماره تماس", "آدرس", "میزان بدهی (تومان)"]
        data = [[prepare_persian_text(h) for h in header]]

        for customer in customers_data:
            row = [
                prepare_persian_text(customer['name']),
                str(customer['national_code']),
                str(customer['phone_number']),
                prepare_persian_text(customer['address']),
                prepare_persian_text(format_money_for_report(customer['total_debt']))
            ]
            data.append(row)

        table = Table(data, colWidths=[150, 100, 100, 250, 120])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Vazir-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Vazir'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ])
        table.setStyle(style)

        for i in range(1, len(data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#edf2f7'))

        elements.append(table)
        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF: {e}")
        return False


# *** تابع ساخت پرونده مشتری با ظاهر و منطق نهایی و اصلاح شده ***
def create_single_customer_report(customer_data, loans, installments_by_loan, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []

        # تعریف استایل‌های فارسی
        styles = {
            'Title': ParagraphStyle(name='Title', fontName='Vazir-Bold', fontSize=18, alignment=TA_CENTER, spaceAfter=20),
            'h2': ParagraphStyle(name='h2', fontName='Vazir-Bold', fontSize=14, alignment=TA_RIGHT, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#2c3e50')),
            'h3': ParagraphStyle(name='h3', fontName='Vazir-Bold', fontSize=11, alignment=TA_RIGHT, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#34495e')),
            'Normal': ParagraphStyle(name='Normal', fontName='Vazir', fontSize=10, alignment=TA_RIGHT),
            'Normal_Bold_Right': ParagraphStyle(name='Normal_Bold_Right', fontName='Vazir-Bold', fontSize=10, alignment=TA_RIGHT),
        }
        
        # --- اطلاعات کلی ---
        title_text = prepare_persian_text(f"پرونده مالی مشتری: {customer_data['name']}")
        elements.append(Paragraph(title_text, styles['Title']))

        # --- اطلاعات شخصی ---
        elements.append(Paragraph(prepare_persian_text("اطلاعات شخصی"), styles['h2']))
        
        info_data = [
            [Paragraph(prepare_persian_text(customer_data['national_code']), styles['Normal']), Paragraph(prepare_persian_text("کد ملی:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(customer_data['phone_number']), styles['Normal']), Paragraph(prepare_persian_text("شماره تماس:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(customer_data['address']), styles['Normal']), Paragraph(prepare_persian_text("آدرس:"), styles['Normal_Bold_Right'])],
        ]
        info_table = Table(info_data, colWidths=[doc.width - 120, 100])
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # --- لیست وام‌ها و اقساط آن‌ها ---
        if loans:
            elements.append(Paragraph(prepare_persian_text("خلاصه وام‌ها و اقساط"), styles['h2']))
            
            for index, loan in enumerate(loans):
                elements.append(Spacer(1, 15))
                
                status = "تسویه شده" if loan.get('is_settled') else "فعال"
                loan_title_text = f"وام شماره {index + 1} - مبلغ {format_money_for_report(loan['amount'])} تومان - وضعیت: {status}"
                elements.append(Paragraph(prepare_persian_text(loan_title_text), styles['h3']))
                
                installments = installments_by_loan.get(loan['id'], [])
                if installments:
                    inst_header = ["تاریخ سررسید", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]
                    inst_data = [[prepare_persian_text(h) for h in inst_header]]
                    
                    for inst in installments:
                        remaining = inst[2] - inst[3]
                        inst_status = "پرداخت شده" if remaining <= 0 else "پرداخت نشده"
                        
                        inst_row = [
                            prepare_persian_text(inst[1]),
                            prepare_persian_text(format_money_for_report(inst[2])),
                            prepare_persian_text(format_money_for_report(inst[3])),
                            prepare_persian_text(format_money_for_report(remaining)),
                            prepare_persian_text(inst_status)
                        ]
                        inst_data.append(inst_row)
                    
                    inst_table = Table(inst_data, colWidths=[100, 100, 100, 100, 80])
                    inst_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Vazir-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Vazir'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4f6f7')),
                    ]))
                    elements.append(inst_table)

        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF مشتری: {e}")
        return False