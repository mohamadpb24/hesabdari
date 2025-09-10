# report_generator.py (نسخه نهایی با ساختار درختی کاملاً اصلاح شده)

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
from typing import Dict, Any, List

# --- توابع کمکی و ثبت فونت (بدون تغییر) ---
def format_money(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

def prepare_persian_text(text):
    return get_display(arabic_reshaper.reshape(str(text)))

try:
    pdfmetrics.registerFont(TTFont('Vazir-Bold', 'Vazir-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Vazir', 'Vazir.ttf'))
except Exception:
    print("هشدار: فونت وزیر یافت نشد.")

def get_report_styles():
    styles = {
        'Title': ParagraphStyle(name='Title', fontName='Vazir-Bold', fontSize=18, alignment=TA_CENTER, spaceAfter=15),
        'Subtitle': ParagraphStyle(name='Subtitle', fontName='Vazir', fontSize=12, alignment=TA_CENTER, spaceAfter=20),
        'h3': ParagraphStyle(name='h3', fontName='Vazir-Bold', fontSize=11, alignment=TA_RIGHT, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#34495e')),
        'Normal': ParagraphStyle(name='Normal', fontName='Vazir', fontSize=9, alignment=TA_CENTER),
        'Normal_Right': ParagraphStyle(name='Normal_Right', fontName='Vazir', fontSize=10, alignment=TA_RIGHT),
        'Sub_Normal': ParagraphStyle(name='Sub_Normal', fontName='Vazir', fontSize=8, alignment=TA_RIGHT, rightIndent=10),
        'Header': ParagraphStyle(name='Header', fontName='Vazir-Bold', fontSize=10, alignment=TA_CENTER, textColor=colors.whitesmoke),
    }
    return styles

def create_single_customer_report(customer_data: Dict, loans: List, installments_by_loan: Dict, file_path: str, selected_loan_id=None):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = get_report_styles()
        elements = [Paragraph(prepare_persian_text(f"پرونده مالی مشتری: {customer_data['name']}"), styles['Title'])]
        # ... (کد مربوط به اطلاعات کلی مشتری در ابتدای گزارش)

        if not loans:
            elements.append(Paragraph(prepare_persian_text("هیچ وامی برای این مشتری ثبت نشده است."), styles['Normal_Right']))
            doc.build(elements)
            return True

        for loan in loans:
            if selected_loan_id and selected_loan_id != "all" and loan['id'] != selected_loan_id:
                continue
            
            status = prepare_persian_text("تسویه شده" if loan.get('status') == 'FULLY_SETTLED' else "فعال")
            loan_title_text = f"وام شماره {loan['readable_id']} - مبلغ {format_money(loan['amount'])} تومان - وضعیت: {status}"
            elements.append(Paragraph(prepare_persian_text(loan_title_text), styles['h3']))
            
            installments = installments_by_loan.get(loan['id'], [])
            if installments:
                header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["#", "سررسید", "تاریخ پرداخت", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]]
                data = [header]
                
                table_styles = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey) # --- یک GRID برای کل جدول ---
                ]

                for i, inst in enumerate(installments):
                    main_row_index = len(data)
                    remaining = inst['amount_due'] - inst['amount_paid']
                    
                    row_content = [
                        str(i + 1), str(inst['due_date']), str(inst.get('payment_date') or '-'),
                        format_money(inst['amount_due']), format_money(inst['amount_paid']),
                        format_money(remaining), inst['status']
                    ]
                    data.append([Paragraph(prepare_persian_text(cell), styles['Normal']) for cell in row_content])
                    
                    bg_color = colors.HexColor('#f8f9fa') if i % 2 == 0 else colors.white
                    table_styles.append(('BACKGROUND', (0, main_row_index), (-1, main_row_index), bg_color))

                    payment_details = inst.get('payment_details', [])
                    if payment_details and (len(payment_details) > 1 or (inst['amount_paid'] > 0 and inst['amount_paid'] < inst['amount_due'])):
                        for payment in payment_details:
                            sub_row_index = len(data)
                            sub_row_text = f"پرداخت در تاریخ {payment['payment_date']} به مبلغ {format_money(payment['amount'])}"
                            if payment.get('description'):
                                sub_row_text += f" ({payment['description']})"
                            
                            sub_row_p = Paragraph(prepare_persian_text(sub_row_text), styles['Sub_Normal'])
                            data.append(['', sub_row_p, '', '', '', '', ''])
                            
                            table_styles.append(('SPAN', (1, sub_row_index), (-1, sub_row_index)))
                            table_styles.append(('BACKGROUND', (0, sub_row_index), (-1, sub_row_index), colors.HexColor('#e9ecef')))
                            # حذف ستون اول برای ردیف‌های جزئیات
                            table_styles.append(('SPAN', (0, sub_row_index), (0, sub_row_index)))
                            table_styles.append(('BACKGROUND', (0, sub_row_index), (0, sub_row_index), bg_color))


                table = Table(data, colWidths=[30, 70, 70, 85, 85, 85, 60], repeatRows=1)
                table.setStyle(TableStyle(table_styles))
                elements.append(table)
                elements.append(Spacer(1, 12))
        
        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF مشتری: {e}")
        return False
        
def create_installments_report(installments_data, start_date, end_date, status, file_path):
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
        styles = get_report_styles()
        elements = [Paragraph(prepare_persian_text("گزارش جامع اقساط"), styles['Title'])]
        subtitle = prepare_persian_text(f"از تاریخ {start_date} تا {end_date} - وضعیت: {status}")
        elements.append(Paragraph(subtitle, styles.get('Subtitle', styles['Normal'])))
        elements.append(Spacer(1, 12))

        header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["مشتری", "شماره وام", "کد قسط", "سررسید", "مبلغ قسط", "پرداختی", "مانده", "وضعیت"]]
        data = [header]

        total_due, total_paid = 0, 0
        for inst in installments_data:
            remaining = inst['amount_due'] - inst['amount_paid']
            row = [
                inst['customer_name'], str(inst['loan_readable_id']), inst['readable_id'],
                str(inst['due_date']), format_money(inst['amount_due']), 
                format_money(inst['amount_paid']), format_money(remaining), inst['status']
            ]
            data.append([Paragraph(prepare_persian_text(cell), styles['Normal']) for cell in row])
            total_due += inst['amount_due']
            total_paid += inst['amount_paid']

        table = Table(data, colWidths=[120, 100, 120, 80, 90, 90, 90, 70], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f4f6f7'), colors.white]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
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
        styles = get_report_styles()
        elements = [Paragraph(prepare_persian_text(f"گزارش گردش حساب صندوق: {cashbox_data['name']}"), styles['Title'])]
        # ... (کد مربوط به اطلاعات خلاصه صندوق)

        if transactions:
            header = [Paragraph(prepare_persian_text(h), styles['Header']) for h in ["تاریخ", "نوع", "مبلغ", "طرف حساب", "شرح"]]
            data = [header]

            type_map = {
                "loan_payment": "پرداخت وام", "installment_received": "دریافت قسط",
                "settlement_received": "تسویه کامل", "expense": "هزینه", 
                "capital_injection": "افزایش سرمایه", "manual_payment": "پرداخت دستی",
                "manual_receipt": "دریافت دستی", "transfer": "انتقال وجه"
            }
            
            for trans in transactions:
                amount_text = prepare_persian_text(format_money(trans['amount']))
                if trans.get('destination_id') == cashbox_data['id']:
                    amount_p = Paragraph(f'<font color="green">{amount_text}</font>', styles['Normal'])
                else:
                    amount_p = Paragraph(f'<font color="red">{amount_text}</font>', styles['Normal'])

                row = [
                    Paragraph(prepare_persian_text(str(trans['date'])), styles['Normal']),
                    Paragraph(prepare_persian_text(type_map.get(trans['type'], trans['type'])), styles['Normal']),
                    amount_p,
                    Paragraph(prepare_persian_text(trans.get('customer_name', 'سیستم')), styles['Normal']),
                    Paragraph(prepare_persian_text(trans.get('description', '')), styles['Normal_Right'])
                ]
                data.append(row)
            
            table = Table(data, colWidths=[80, 80, 100, 100, 150], repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f4f6f7'), colors.white]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)

        doc.build(elements)
        return True
    except Exception as e:
        print(f"خطا در ساخت گزارش PDF صندوق: {e}")
        return False