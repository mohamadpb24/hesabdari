import jdatetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from bidi.algorithm import get_display
import arabic_reshaper

# --- توابع کمکی ---
def format_money_for_report(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

def prepare_persian_text(text):
    # تضمین می‌کند که ورودی همیشه رشته باشد
    return get_display(arabic_reshaper.reshape(str(text)))

# --- توابع کمکی ---
def format_money_for_report(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

def prepare_persian_text(text):
    return get_display(arabic_reshaper.reshape(str(text)))

# --- ثبت فونت ---
try:
    pdfmetrics.registerFont(TTFont('Vazir-Bold', 'Vazir-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Vazir', 'Vazir.ttf'))
except Exception as e:
    print(f"هشدار: فونت وزیر یافت نشد. از فونت جایگزین استفاده می‌شود. خطا: {e}")
    pdfmetrics.registerFont(TTFont('Vazir-Bold', 'tahoma.ttf'))
    pdfmetrics.registerFont(TTFont('Vazir', 'tahoma.ttf'))

class BaseReportTemplate(PageTemplate):
    def __init__(self, page_id, doc):
        self.doc = doc
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        super().__init__(id=page_id, frames=[frame])

    def afterDrawPage(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Vazir', 9)
        # Footer
        footer_text = f"صفحه {doc.page}"
        canvas.drawRightString(doc.width + doc.leftMargin - 1*cm, 1*cm, prepare_persian_text(footer_text))
        # Header Line
        canvas.setStrokeColorRGB(0.2, 0.5, 0.7)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin - 1.5*cm, doc.width + doc.leftMargin, doc.height + doc.topMargin - 1.5*cm)
        canvas.restoreState()

def get_report_styles():
    styles = {
        'Title': ParagraphStyle(name='Title', fontName='Vazir-Bold', fontSize=18, alignment=TA_CENTER, spaceAfter=15),
        'Subtitle': ParagraphStyle(name='Subtitle', fontName='Vazir', fontSize=12, alignment=TA_CENTER, spaceAfter=20),
        'h2': ParagraphStyle(name='h2', fontName='Vazir-Bold', fontSize=14, alignment=TA_RIGHT, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#2c3e50')),
        'h3': ParagraphStyle(name='h3', fontName='Vazir-Bold', fontSize=11, alignment=TA_RIGHT, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#34495e')),
        'Normal': ParagraphStyle(name='Normal', fontName='Vazir', fontSize=9, alignment=TA_CENTER),
        'Normal_Right': ParagraphStyle(name='Normal_Right', fontName='Vazir', fontSize=10, alignment=TA_RIGHT),
        'Normal_Bold_Right': ParagraphStyle(name='Normal_Bold_Right', fontName='Vazir-Bold', fontSize=10, alignment=TA_RIGHT),
        'Sub_Normal': ParagraphStyle(name='Sub_Normal', fontName='Vazir', fontSize=8, alignment=TA_RIGHT, leftIndent=15),
        'Header': ParagraphStyle(name='Header', fontName='Vazir-Bold', fontSize=10, alignment=TA_CENTER, textColor=colors.whitesmoke),
        'Summary': ParagraphStyle(name='Summary', fontName='Vazir-Bold', fontSize=10, alignment=TA_CENTER),
    }
    return styles
# --- تابع ساخت گزارش لیست مشتریان (اصلاح شده) ---
def create_customers_report(customers_data, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()
        styles['h1'].fontName = 'Vazir-Bold'
        styles['Normal'].fontName = 'Vazir'
        styles['h1'].alignment = TA_RIGHT

        elements.append(Paragraph(prepare_persian_text("گزارش لیست مشتریان"), styles['h1']))
        elements.append(Spacer(1, 15))

        today_date = jdatetime.date.today().strftime('%Y/%m/%d')
        date_text = prepare_persian_text(f"تاریخ گزارش: {today_date}")
        elements.append(Paragraph(date_text, styles['Normal']))
        elements.append(Spacer(1, 15))

        header = [prepare_persian_text(h) for h in ["نام و نام خانوادگی", "کد ملی", "شماره تماس", "آدرس", "میزان بدهی (تومان)"]]
        data = [header]

        for customer in customers_data:
            row = [
                prepare_persian_text(customer['name']),
                prepare_persian_text(customer['national_code']),
                prepare_persian_text(customer['phone_number']),
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
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)

        elements.append(table)
        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF: {e}")
        return False


# --- تابع ساخت گزارش پرونده مشتری (اصلاح شده) ---
def create_single_customer_report(customer_data, loans, installments_by_loan, file_path, selected_loan_id=None):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        doc.addPageTemplates([BaseReportTemplate('main_page', doc)])
        elements = []
        styles = get_report_styles()
        
        elements.append(Paragraph(prepare_persian_text(f"پرونده مالی مشتری: {customer_data['name']}"), styles['Title']))
        elements.append(Paragraph(prepare_persian_text(f"تاریخ گزارش: {jdatetime.date.today().strftime('%Y/%m/%d')}"), styles['Subtitle']))
        
        info_data = [
            [Paragraph(prepare_persian_text(customer_data['national_code']), styles['Normal_Right']), Paragraph(prepare_persian_text("کد ملی:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(customer_data['phone_number']), styles['Normal_Right']), Paragraph(prepare_persian_text("شماره تماس:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(customer_data['address']), styles['Normal_Right']), Paragraph(prepare_persian_text("آدرس:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(format_money_for_report(customer_data['total_debt'])), styles['Normal_Bold_Right']), Paragraph(prepare_persian_text("مانده کل بدهی:"), styles['Normal_Bold_Right'])],
        ]
        elements.append(Table(info_data, colWidths=[doc.width/2 - 20, 100], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(Spacer(1, 1*cm))

        if loans:
            elements.append(Paragraph(prepare_persian_text("خلاصه وام‌ها و اقساط"), styles['h2']))
            for loan in loans:
                if selected_loan_id and selected_loan_id != "all" and loan['id'] != selected_loan_id:
                    continue

                status = prepare_persian_text("تسویه شده" if loan.get('is_settled') else "فعال")
                loan_title = prepare_persian_text(f"وام شماره {loan['id']} - مبلغ {format_money_for_report(loan['amount'])} تومان - وضعیت: {status}")
                elements.append(Paragraph(loan_title, styles['h3']))
                
                installments = installments_by_loan.get(loan['id'], [])
                if installments:
                    header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["#", "سررسید", "تاریخ پرداخت", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]]
                    data = [header]
                    
                    table_styles = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]

                    for i, inst in enumerate(installments):
                        remaining = inst['amount_due'] - inst['amount_paid']
                        if remaining <= 0: inst_status = "پرداخت شده"
                        elif inst['amount_paid'] > 0: inst_status = "پرداخت ناقص"
                        else: inst_status = "پرداخت نشده"
                        
                        row_content = [
                            str(i + 1), inst['due_date'], inst['payment_date'] or '-',
                            format_money_for_report(inst['amount_due']), format_money_for_report(inst['amount_paid']),
                            format_money_for_report(remaining), inst_status
                        ]
                        data.append([Paragraph(prepare_persian_text(cell), styles['Normal']) for cell in row_content])
                        current_row_idx = len(data) - 1
                        table_styles.append(('BACKGROUND', (0, current_row_idx), (-1, current_row_idx), colors.HexColor('#f4f6f7') if i % 2 == 0 else colors.white))
                        
                        payment_details = inst.get('payment_details', [])
                        if len(payment_details) > 1:
                            for payment in payment_details:
                                sub_row_text = f"پرداخت در تاریخ {payment['payment_date']} به مبلغ {format_money_for_report(payment['amount'])}"
                                if payment.get('description'):
                                    sub_row_text += f" ({payment['description']})"
                                
                                sub_row_p = Paragraph(prepare_persian_text(sub_row_text), styles['Sub_Normal'])
                                data.append(['', sub_row_p, '', '', '', '', ''])
                                
                                sub_row_idx = len(data) - 1
                                table_styles.append(('SPAN', (1, sub_row_idx), (-1, sub_row_idx)))
                                table_styles.append(('BACKGROUND', (0, sub_row_idx), (-1, sub_row_idx), colors.HexColor('#f8f9fa')))
                                table_styles.append(('GRID', (0, current_row_idx), (-1, sub_row_idx), 1, colors.darkgrey))


                    table = Table(data, colWidths=[30, 70, 70, 85, 85, 85, 60])
                    table.setStyle(TableStyle(table_styles))
                    elements.append(table)
                    elements.append(Spacer(1, 0.5*cm))
        
        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF مشتری: {e}")
        return False


# --- تابع ساخت گزارش اقساط (اصلاح شده) ---
def create_installments_report(installments_data, start_date, end_date, status, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
        doc.addPageTemplates([BaseReportTemplate('main_page_land', doc)])
        elements = []
        styles = get_report_styles()

        elements.append(Paragraph(prepare_persian_text("گزارش جامع اقساط"), styles['Title']))
        subtitle = prepare_persian_text(f"از تاریخ {start_date} تا {end_date} - وضعیت: {status}")
        elements.append(Paragraph(subtitle, styles['Subtitle']))
        
        header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["مشتری", "شماره وام", "سررسید", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]]
        data = [header]

        total_due, total_paid = 0, 0
        for inst in installments_data:
            remaining = inst['amount_due'] - inst['amount_paid']
            if remaining <= 0: inst_status = "پرداخت شده"
            elif inst['amount_paid'] > 0: inst_status = "پرداخت ناقص"
            else: inst_status = "پرداخت نشده"
            
            row = [
                inst['customer_name'], str(inst['loan_id']), inst['due_date'],
                format_money_for_report(inst['amount_due']), format_money_for_report(inst['amount_paid']),
                format_money_for_report(remaining), inst_status
            ]
            data.append([Paragraph(prepare_persian_text(cell), styles['Normal']) for cell in row])
            total_due += inst['amount_due']
            total_paid += inst['amount_paid']

        summary = [
            f"مجموع: {len(installments_data)} قسط", '', '',
            format_money_for_report(total_due), format_money_for_report(total_paid),
            format_money_for_report(total_due - total_paid), ''
        ]
        data.append([Paragraph(prepare_persian_text(cell), styles['Summary']) for cell in summary])
        
        table = Table(data, colWidths=[150, 60, 100, 110, 110, 110, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#f4f6f7'), colors.HexColor('#ffffff')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
            ('SPAN', (0, -1), (2, -1)),
        ]))
        elements.append(table)
        
        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش اقساط: {e}")
        return False
    
def create_cashbox_report(cashbox_data, transactions, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        doc.addPageTemplates([BaseReportTemplate('main_page', doc)])
        elements = []
        styles = get_report_styles()

        # --- Header ---
        elements.append(Paragraph(prepare_persian_text(f"گزارش گردش حساب صندوق: {cashbox_data['name']}"), styles['Title']))
        elements.append(Paragraph(prepare_persian_text(f"تاریخ گزارش: {jdatetime.date.today().strftime('%Y/%m/%d')}"), styles['Subtitle']))
        
        # --- Summary Box ---
        total_income = sum(t['amount'] for t in transactions if t['destination_id'] == cashbox_data['id'])
        total_outcome = sum(t['amount'] for t in transactions if t['source_id'] == cashbox_data['id'])
        
        summary_data = [
            [Paragraph(prepare_persian_text(format_money_for_report(total_income)), styles['Normal_Right']), Paragraph(prepare_persian_text("مجموع واریزها:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(format_money_for_report(total_outcome)), styles['Normal_Right']), Paragraph(prepare_persian_text("مجموع برداشت‌ها:"), styles['Normal_Bold_Right'])],
            [Paragraph(prepare_persian_text(format_money_for_report(cashbox_data['balance'])), styles['Normal_Bold_Right']), Paragraph(prepare_persian_text("مانده نهایی صندوق:"), styles['Normal_Bold_Right'])],
        ]
        summary_table = Table(summary_data, colWidths=[doc.width/2 - 20, 130], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
        elements.append(summary_table)
        elements.append(Spacer(1, 1*cm))

        # --- Transactions Table ---
        if transactions:
            elements.append(Paragraph(prepare_persian_text("لیست کامل تراکنش‌ها"), styles['h2']))
            
            header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["تاریخ", "نوع", "مبلغ (تومان)", "طرف حساب", "شرح"]]
            data = [header]

            for trans in transactions:
                trans_type_map = {
                    "loan_payment": "پرداخت وام", "installment_received": "دریافت قسط",
                    "settlement_received": "تسویه کامل", "expense": "هزینه", "capital_injection": "افزایش سرمایه"
                }
                # --- اصلاح کلیدی: تمام سلول‌ها به پاراگراف تبدیل می‌شوند ---
                display_type = prepare_persian_text(trans_type_map.get(trans['type'], trans['type']))
                
                amount_text = prepare_persian_text(format_money_for_report(trans['amount']))
                if trans.get('destination_id') == cashbox_data['id']: # ورودی
                    amount_p = Paragraph(f'<font color="green">{amount_text}</font>', styles['Normal'])
                else: # خروجی
                    amount_p = Paragraph(f'<font color="red">{amount_text}</font>', styles['Normal'])

                row = [
                    Paragraph(prepare_persian_text(trans['date']), styles['Normal']),
                    Paragraph(display_type, styles['Normal']), # <-- این سلول نیز به پاراگراف تبدیل شد
                    amount_p,
                    Paragraph(prepare_persian_text(trans.get('customer_name', 'سیستم')), styles['Normal']),
                    Paragraph(prepare_persian_text(trans.get('description', '')), styles['Normal_Right'])
                ]
                data.append(row)
            
            table = Table(data, colWidths=[80, 80, 100, 100, 150])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f4f6f7'), colors.HexColor('#ffffff')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF صندوق: {e}")
        return False

















