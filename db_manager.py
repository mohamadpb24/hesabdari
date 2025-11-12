# db_manager.py (نسخه نهایی سازگار با مدل جدید دیتابیس مبتنی بر C# و SQL Server)

import pyodbc
import configparser
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
import jdatetime
import uuid
from datetime import datetime
from decimal import Decimal 


# --- راه‌اندازی لاگ‌گیری ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self):
        try:
            self.db_config = self._get_db_config()
            logging.info("✅ کانفیگ اتصال به SQL Server (مدل جدید) با موفقیت خوانده شد.")
        except Exception as e:
            logging.error(f"❌ خطا در خواندن فایل config.ini: {e}")
            raise

    def _get_db_config(self) -> Dict[str, str]:
        config = configparser.ConfigParser()
        config.read('config.ini')
        return dict(config['sqlserver'])

    @contextmanager
    def get_connection(self):
        conn_str = (
            f"DRIVER={{{self.db_config['driver']}}};"
            f"SERVER={self.db_config['server']};"
            f"DATABASE={self.db_config['database']};"
            f"UID={self.db_config['user']};"
            f"PWD={self.db_config['password']};"
            f"TrustServerCertificate=yes;"
        )
        connection = None
        try:
            connection = pyodbc.connect(conn_str)
            yield connection
        except pyodbc.Error as err:
            logging.error(f"❌ خطا در اتصال به SQL Server: {err}")
            raise
        finally:
            if connection:
                connection.close()

    def _get_next_code(self, table_name: str, column_name: str = 'Code') -> int:
        """بیشترین مقدار یک ستون کد را پیدا کرده و عدد بعدی را برمی‌گرداند."""
        query = f"SELECT MAX({column_name}) as max_code FROM [{table_name}]"
        result = self._execute_query(query, fetch='one')
        if result and result.get('max_code') is not None:
            return int(result['max_code']) + 1
        return 1001

    # --- توابع کمکی برای تبدیل ردیف‌ها به دیکشنری ---
    def _row_to_dict(self, cursor, row):
        if row is None: return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))

    def _rows_to_dict_list(self, cursor, rows):
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    # --- اجرای کوئری ---
    def _execute_query(self, query: str, params: tuple = None, fetch: Optional[str] = None, dictionary: bool = True):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())

                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                    return True

                if fetch == 'one':
                    row = cursor.fetchone()
                    return self._row_to_dict(cursor, row) if dictionary and row else row
                if fetch == 'all':
                    rows = cursor.fetchall()
                    return self._rows_to_dict_list(cursor, rows) if dictionary and rows else rows
                return cursor
        except pyodbc.Error as err:
            logging.error(f"❌ خطا در اجرای کوئری: {query} | پارامترها: {params} | خطا: {err}")
            return None if fetch else False

    def _execute_transactional_operations(self, operations: List[Dict[str, Any]]) -> Tuple[bool, str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    for op in operations:
                        cursor.execute(op['query'], op.get('params', ()))
                    conn.commit()
                    return True, "عملیات با موفقیت انجام شد."
                except pyodbc.Error as err:
                    conn.rollback()
                    logging.error(f"❌ خطا در تراکنش: {err}")
                    return False, f"خطا در عملیات پایگاه داده: {err}"
        except pyodbc.Error as conn_err:
            return False, f"خطا در اتصال برای تراکنش: {conn_err}"


    def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        """آمار کلی سیستم را برای نمایش در داشبورد محاسبه می‌کند."""
        query = """
            SELECT
                (SELECT ISNULL(SUM(Inventory), 0) FROM [Funds]) as total_balance,
                (SELECT ISNULL(SUM(Amount), 0) FROM [Loans] WHERE Status = 'ACTIVE') as total_loan_principal,
                (SELECT ISNULL(COUNT(ID), 0) FROM [Persons] WHERE IsActive = 1) as total_customers,
                (SELECT ISNULL(SUM(Amount), 0) FROM [Expenses]) as total_expenses,
                (SELECT COUNT(ID) FROM [Loans] WHERE Status = 'ACTIVE') as active_loans,
                (SELECT COUNT(ID) FROM [Loans] WHERE Status = 'FULLY_SETTLED') as settled_loans,
                (SELECT ISNULL(SUM(DueAmount), 0) FROM [Installments]) as total_due,
                (SELECT ISNULL(SUM(PaidAmount), 0) FROM [Installments]) as total_paid,
                (SELECT ISNULL(SUM(Amount), 0) FROM [Loans]) as all_time_principal
        """
        stats = self._execute_query(query, fetch='one')
        if not stats: return None
        
        # محاسبات سود در پایتون
        total_due = stats.get('total_due') or 0
        total_paid = stats.get('total_paid') or 0
        all_time_principal = stats.get('all_time_principal') or 0

        stats['total_projected_profit'] = total_due - all_time_principal
        stats['total_receivables'] = total_due - total_paid

        if all_time_principal > 0 and total_due > 0:
            principal_to_due_ratio = all_time_principal / total_due
            principal_repaid = total_paid * principal_to_due_ratio
            stats['realized_profit'] = total_paid - principal_repaid
        else:
            stats['realized_profit'] = 0
            
        stats['unrealized_profit'] = stats['total_projected_profit'] - stats['realized_profit']
        return stats

    # --- مدیریت مشتریان (Persons) ---
    
    def _get_next_person_code(self) -> int:
        """
        بیشترین کد شخص را که با پیشوند ۱۰ شروع می‌شود پیدا کرده و عدد بعدی را به صورت امن برمی‌گرداند.
        """
        prefix = "10"
        query = f"SELECT MAX(Code) as max_code FROM [Persons] WHERE CAST(Code AS VARCHAR(20)) LIKE '{prefix}%'"
        result = self._execute_query(query, fetch='one')

        if result and result.get('max_code') is not None:
            last_code_str = str(result['max_code'])
            serial_part_str = last_code_str[len(prefix):]
            
            # --- اصلاح شد: اگر بخش سریال خالی بود، از ۰۰۰۰۱ شروع می‌کنیم ---
            if not serial_part_str:
                return 100001 

            next_serial_int = int(serial_part_str) + 1
            
            # --- اصلاح شد: طول شماره سریال جدید حفظ می‌شود ---
            padded_next_serial = str(next_serial_int).zfill(len(serial_part_str))
            new_code_str = f"{prefix}{padded_next_serial}"
            
            return int(new_code_str)
        else:
            # --- اصلاح شد: شماره‌گذاری از 100001 شروع می‌شود ---
            return 100001

    def add_customer(self, name: str, national_code: str, phone_number: str, address: str) -> bool:
        new_uuid = str(uuid.uuid4())
        # --- اصلاح کلیدی: استفاده از تابع جدید برای تولید کد با پیشوند ۱۰ ---
        new_code = self._get_next_person_code()
        created_date = datetime.now()
        
        query = "INSERT INTO [Persons] (ID, Code, FullName, NationalID, PhoneNumber, Address, IsActive, CreatedDate) VALUES (?, ?, ?, ?, ?, ?, 1, ?)"
        return self._execute_query(query, (new_uuid, new_code, name, national_code, phone_number, address, created_date))


    def update_customer(self, customer_id: str, name: str, national_code: str, phone_number: str, address: str) -> bool:
        query = "UPDATE [Persons] SET FullName = ?, NationalID = ?, PhoneNumber = ?, Address = ? WHERE ID = ?"
        return self._execute_query(query, (name, national_code, phone_number, address, customer_id))

    def get_all_customers(self) -> List[Tuple]:
        query = "SELECT ID, FullName FROM [Persons] WHERE IsActive = 1 ORDER BY FullName"
        return self._execute_query(query, fetch='all', dictionary=False)

        offset = (page - 1) * page_size
        base_query = "SELECT ID, Code, FullName, NationalID, PhoneNumber, Address FROM [Persons] WHERE IsActive = 1"
        params = []
        if search_query:
            base_query += " AND (FullName LIKE ? OR NationalID LIKE ? OR PhoneNumber LIKE ?)"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
        base_query += " ORDER BY Code DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, page_size])
        return self._execute_query(base_query, tuple(params), fetch='all')

    def get_customers_count(self, search_query: str = "") -> int:
        base_query = "SELECT COUNT(ID) as count FROM [Persons] WHERE IsActive = 1"
        params = []
        if search_query:
            base_query += " AND (FullName LIKE ? OR NationalID LIKE ? OR PhoneNumber LIKE ?)"
            search_term = f"%{search_query}%"
            params = [search_term, search_term, search_term]
        result = self._execute_query(base_query, tuple(params), fetch='one')
        return result['count'] if result else 0



    def get_customers_paginated(self, page: int, page_size: int, search_query: str = "") -> List[Dict[str, Any]]:
        offset = (page - 1) * page_size
        # --- اصلاح شد: مجموع بدهی با JOIN محاسبه می‌شود ---
        base_query = """
            SELECT 
                p.ID, p.Code, p.FullName, p.NationalID, p.PhoneNumber, p.Address,
                ISNULL(SUM(l.RemainAmount), 0) as TotalDebt
            FROM 
                [Persons] p
            LEFT JOIN 
                [Loans] l ON p.ID = l.Person_ID AND l.Status = 'ACTIVE'
            WHERE p.IsActive = 1
        """
        params = []
        if search_query:
            base_query += " AND (p.FullName LIKE ? OR p.NationalID LIKE ? OR p.PhoneNumber LIKE ?)"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
        
        base_query += """
            GROUP BY p.ID, p.Code, p.FullName, p.NationalID, p.PhoneNumber, p.Address, p.CreatedDate
            ORDER BY p.CreatedDate DESC 
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, page_size])
        
        return self._execute_query(base_query, tuple(params), fetch='all')

    def get_person_transactions(self, person_id: str) -> list:
        """تمام تراکنش‌های مربوط به یک شخص خاص را از جدول Payments برمی‌گرداند."""
        query = """
            SELECT
                p.PaymentDate,
                p.PaymentType,
                p.Amount,
                p.Description,
                f.FundName
            FROM Payments p
            LEFT JOIN Funds f ON p.Fund_ID = f.ID
            WHERE p.Person_ID = ?
            ORDER BY p.PaymentDate DESC
        """
        return self._execute_query(query, (person_id,), fetch='all')
    # --- مدیریت صندوق‌ها (Funds) ---

    def get_all_cash_boxes(self) -> List[Tuple]:
        """اطلاعات تمام صندوق‌ها (Funds) را برای نمایش در پنل صندوق برمی‌گرداند."""
        query = "SELECT ID, FundName, Inventory FROM [Funds] ORDER BY FundName"
        return self._execute_query(query, fetch='all', dictionary=False)

    def _get_next_fund_code(self) -> int:
        """
        بیشترین کد صندوق را که با پیشوند ۳۰ شروع می‌شود پیدا کرده و عدد بعدی را به صورت امن برمی‌گرداند.
        """
        prefix = "30"
        query = f"SELECT MAX(Code) as max_code FROM [Funds] WHERE CAST(Code AS VARCHAR(20)) LIKE '{prefix}%'"
        result = self._execute_query(query, fetch='one')

        if result and result.get('max_code') is not None:
            last_code_str = str(result['max_code'])
            
            serial_part_str = last_code_str[len(prefix):]
            
            if not serial_part_str:
                return 30001 

            next_serial_int = int(serial_part_str) + 1
            
            # طول شماره سریال جدید حفظ می‌شود
            padded_next_serial = str(next_serial_int).zfill(len(serial_part_str))
            new_code_str = f"{prefix}{padded_next_serial}"
            
            return int(new_code_str)
        else:
            # اگر هیچ صندوقی با این پیشوند وجود نداشته باشد، شماره‌گذاری از 30001 شروع می‌شود
            return 30001

    def add_fund(self, name: str, initial_balance: float = 0) -> bool:
        new_uuid = str(uuid.uuid4())
        # --- اصلاح کلیدی: استفاده از تابع جدید برای تولید کد با پیشوند ۳۰ ---
        new_code = self._get_next_fund_code()

        query = "INSERT INTO [Funds] (ID, Code, FundName, Inventory) VALUES (?, ?, ?, ?)"
        return self._execute_query(query, (new_uuid, new_code, name, initial_balance))


    def update_fund(self, fund_id: str, name: str, balance: float) -> bool:
        query = "UPDATE [Funds] SET FundName = ?, Inventory = ? WHERE ID = ?"
        return self._execute_query(query, (name, balance, fund_id))

    def delete_fund(self, fund_id: str) -> bool:
        query = "DELETE FROM [Funds] WHERE ID = ?"
        return self._execute_query(query, (fund_id,))


    def get_fund_transactions(self, fund_id: str) -> List[Dict[str, Any]]:
        """تراکنش‌های یک صندوق را از جداول پرداخت و هزینه استخراج می‌کند."""
        query = """
        -- بخش اول: تراکنش‌های پرداخت
        SELECT
            p.Amount,
            p.PaymentDate AS Date,
            p.Description,
            p.PaymentType AS Type,
            p.Code AS SortCode, -- اضافه شدن ستون کد برای مرتب‌سازی
            CASE
                WHEN p.PaymentType IN ('LoanPayment', 'ManualPayment', 'Expense', 'manual_payment') THEN N'خروجی'
                WHEN p.PaymentType = 'transfer' AND p.Fund_ID = ? THEN N'خروجی'
                ELSE N'ورودی'
            END as Flow,
            CASE
                WHEN p.PaymentType = 'transfer' AND p.Fund_ID = ? THEN (SELECT f.FundName FROM Funds f WHERE f.ID = p.DestinationFund_ID)
                WHEN p.PaymentType = 'transfer' AND p.DestinationFund_ID = ? THEN (SELECT f.FundName FROM Funds f WHERE f.ID = p.Fund_ID)
                WHEN p.PaymentType = 'capital_injection' THEN N'افزایش سرمایه'
                ELSE ISNULL(pr.FullName, N'سیستم')
            END as Counterparty
        FROM Payments p
        LEFT JOIN Persons pr ON p.Person_ID = pr.ID
        WHERE p.Fund_ID = ? OR p.DestinationFund_ID = ?

        UNION ALL

        -- بخش دوم: تراکنش‌های هزینه
        SELECT
            e.Amount,
            e.Date,
            e.Description,
            'Expense' AS Type,
            CAST(e.Code AS VARCHAR(50)) AS SortCode, -- اضافه شدن ستون کد برای مرتب‌سازی
            N'خروجی' as Flow,
            c.Name as Counterparty
        FROM Expenses e
        JOIN Categories c ON e.Cat_ID = c.ID
        WHERE e.Fund_ID = ?

        -- اصلاح شد: مرتب‌سازی ابتدا بر اساس تاریخ و سپس بر اساس کد
        ORDER BY Date DESC, SortCode DESC
        """
        params = (fund_id, fund_id, fund_id, fund_id, fund_id, fund_id)
        return self._execute_query(query, params, fetch='all')


    # --- مدیریت وام (Loans) و اقساط (Installments) ---

    def _generate_loan_code(self) -> int:
        """
        بیشترین کد وام را که با پیشوند ۲۰ شروع می‌شود پیدا کرده و عدد بعدی را به صورت امن برمی‌گرداند.
        این روش از تغییر پیشوند جلوگیری می‌کند و محدودیتی در تعداد ندارد.
        """
        prefix = "20"
        query = f"SELECT MAX(Code) as max_code FROM [Loans] WHERE CAST(Code AS VARCHAR(20)) LIKE '{prefix}%'"
        result = self._execute_query(query, fetch='one')

        if result and result.get('max_code') is not None:
            # ۱. آخرین کد را به رشته تبدیل می‌کنیم
            last_code_str = str(result['max_code'])
            
            # ۲. بخش سریال (هرچیزی بعد از پیشوند) را جدا می‌کنیم
            serial_part_str = last_code_str[len(prefix):]
            
            # ۳. شماره سریال را یکی اضافه می‌کنیم
            next_serial_int = int(serial_part_str) + 1
            
            # --- اصلاح کلیدی ---
            # ۴. شماره سریال جدید را با صفرهای پیشرو به همان طول قبلی پُر می‌کنیم
            padded_next_serial = str(next_serial_int).zfill(len(serial_part_str))
            
            # ۵. کد جدید را با چسباندن پیشوند و شماره سریال جدید می‌سازیم
            new_code_str = f"{prefix}{padded_next_serial}"
            
            return int(new_code_str)
        else:
            # اگر این اولین وام با این پیشوند باشد، شماره را از ۲۰۰00۱ شروع می‌کنیم
            return 200001

    def _get_next_payment_code(self, payment_type: str) -> str:
        """
        یک کد پرداخت منحصر به فرد بر اساس پیشوند نوع تراکنش، تاریخ شمسی و شماره سریال روزانه ایجاد می‌کند.
        """
        # --- ۱. اصلاح شد: پیشوند افزایش سرمایه به ۷ تغییر کرد ---
        prefix_map = {
            'LoanPayment': '1',
            'InstallmentPayment': '2',
            'manual_payment': '3',
            'manual_receipt': '4',
            'transfer': '5',
            'Expense': '6',
            'capital_injection': '7'  # <-- اصلاح شد
        }
        prefix = prefix_map.get(payment_type, '0') # 0 برای موارد پیش‌بینی نشده

        # ... (بقیه منطق تابع بدون تغییر باقی می‌ماند)
        today_jalali = jdatetime.date.today()
        date_prefix = today_jalali.strftime("%y%m%d")
        
        full_prefix = f"{prefix}-{date_prefix}-"
        query = f"SELECT MAX(Code) as max_code FROM [Payments] WHERE Code LIKE '{full_prefix}%'"
        result = self._execute_query(query, fetch='one')

        if result and result.get('max_code') is not None:
            last_serial = int(result['max_code'].split('-')[-1])
            next_serial = last_serial + 1
            return f"{full_prefix}{next_serial:03d}"
        else:
            return f"{full_prefix}001"

    def create_loan_and_installments(self, loan_data: Dict, installments_data: List[Dict]) -> Tuple[bool, str]:
        loan_uuid = str(uuid.uuid4())
        loan_code = self._generate_loan_code()
        payment_code = self._get_next_payment_code('LoanPayment')

        operations = [
            # ۱. ثبت اطلاعات کلی وام
            {'query': "INSERT INTO [Loans] (ID, Code, Person_ID, Fund_ID, Status, Amount, LoanTerm, InterestRate, PenaltyRate, LoanDate, EndDate, RemainAmount) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?)",
             'params': (loan_uuid, loan_code, loan_data['person_id'], loan_data['fund_id'], loan_data['amount'],
                           loan_data['loan_term'], loan_data['interest_rate'], loan_data['penalty_rate'],
                           loan_data['loan_date'], loan_data['end_date'], loan_data['remain_amount'])},

            # ۲. کاهش موجودی صندوق
            {'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?",
             'params': (loan_data['amount'], loan_data['fund_id'])},

            # ۳. ثبت تراکنش پرداخت وام
            {'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Person_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'LoanPayment')",
             'params': (str(uuid.uuid4()), payment_code, loan_data['fund_id'], loan_data['person_id'], None,
                           loan_data['loan_date'], loan_data['amount'], loan_data['description'])}
        ]

        # ۴. ثبت اقساط با مقادیر اولیه صحیح
        for i, inst in enumerate(installments_data):
            installment_number = str(i + 1).zfill(2)
            installment_code = f"{loan_code}-{installment_number}"
            
            # --- شروع تغییرات کلیدی ---
            # مقادیر اولیه را اینجا تنظیم می‌کنیم
            due_amount = inst['amount_due']
            
            operations.append({
                'query': """
                    INSERT INTO [Installments] 
                        (ID, Code, Loan_ID, Person_ID, Status, DueDate, DueAmount, PaidAmount, 
                         PaymentRemain, PenaltyDays, PenaltyAmount, TotalAmount) 
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?, 0, ?, 0, 0, ?)
                """,
                # مقادیر به ترتیب ستون‌ها:
                # PaymentRemain و TotalAmount هر دو در ابتدا برابر با DueAmount هستند
                'params': (str(uuid.uuid4()), installment_code, loan_uuid, loan_data['person_id'], 
                           inst['due_date'], due_amount, due_amount, due_amount)
            })
            # --- پایان تغییرات کلیدی ---
        
        return self._execute_transactional_operations(operations)
        loan_uuid = str(uuid.uuid4())
        loan_code = self._generate_loan_code()
        # --- اصلاح شد: ارسال نوع پرداخت 'LoanPayment' برای تولید کد با پیشوند ۱ ---
        payment_code = self._get_next_payment_code('LoanPayment')

        operations = [
            {'query': "INSERT INTO [Loans] (ID, Code, Person_ID, Fund_ID, Status, Amount, LoanTerm, InterestRate, PenaltyRate, LoanDate, EndDate, RemainAmount) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?)",
             'params': (loan_uuid, loan_code, loan_data['person_id'], loan_data['fund_id'], loan_data['amount'],
                           loan_data['loan_term'], loan_data['interest_rate'], loan_data['penalty_rate'],
                           loan_data['loan_date'], loan_data['end_date'], loan_data['remain_amount'])},

            {'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?",
             'params': (loan_data['amount'], loan_data['fund_id'])},

            {'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Person_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'LoanPayment')",
             'params': (str(uuid.uuid4()), payment_code, loan_data['fund_id'], loan_data['person_id'], None,
                           loan_data['loan_date'], loan_data['amount'], loan_data['description'])}
        ]

        for i, inst in enumerate(installments_data):
            installment_number = str(i + 1).zfill(2)
            installment_code = f"{loan_code}-{installment_number}"
            operations.append({
                'query': "INSERT INTO [Installments] (ID, Code, Loan_ID, Person_ID, Status, DueDate, DueAmount, PaidAmount, PaymentRemain) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, 0, ?)",
                'params': (str(uuid.uuid4()), installment_code, loan_uuid, loan_data['person_id'], inst['due_date'], inst['amount_due'], inst['amount_due'])
            })
        
        return self._execute_transactional_operations(operations)

        # عملیات ثبت اقساط
        for inst in installments_data:
            operations.append({
                'query': "INSERT INTO [Installments] (ID, Loan_ID, Person_ID, Status, DueDate, DueAmount, PaidAmount, PaymentRemain) VALUES (?, ?, ?, 'PENDING', ?, ?, 0, ?)",
                'params': (str(uuid.uuid4()), loan_uuid, loan_data['person_id'], inst['due_date'], inst['amount_due'], inst['amount_due'])
            })
        
        return self._execute_transactional_operations(operations)

    def get_customer_loans(self, person_id: str) -> list:
        query = "SELECT ID, Code, Amount, LoanTerm FROM [Loans] WHERE Person_ID = ?"
        return self._execute_query(query, (person_id,), fetch='all', dictionary=False)

    def get_loan_installments(self, loan_id: str) -> list:
        """
        اطلاعات کامل اقساط یک وام، شامل جزئیات جریمه را برمی‌گرداند.
        """
        # --- اصلاح کلیدی: ستون‌های جدید به کوئری اضافه شده‌اند ---
        query = """
            SELECT
                ID, Code, DueDate, DueAmount, PaidAmount, PaymentDate, Status,
                PaymentRemain, PenaltyDays, PenaltyAmount, TotalAmount
            FROM [Installments]
            WHERE Loan_ID = ?
            ORDER BY DueDate ASC
        """
        installments = self._execute_query(query, (loan_id,), fetch='all', dictionary=True)
        # همیشه یک لیست خالی برگردان تا از خطاهای بعدی جلوگیری شود
        return installments if installments else []


    def get_installment_details(self, installment_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT ID, Loan_ID, DueAmount, PaidAmount, PaymentRemain FROM [Installments] WHERE ID = ?"
        return self._execute_query(query, (installment_id,), fetch='one')

    def pay_installment(self, person_id: str, installment_id: str, amount_paid: float, fund_id: str, description: str, payment_date: str) -> Tuple[bool, str]:
        """
        پرداخت برای یک قسط را ثبت کرده و مقادیر بدهی را بر اساس منطق جدید به‌روزرسانی می‌کند.
        """
        # مرحله ۱: دریافت آخرین وضعیت قسط از دیتابیس
        # (جریمه‌ها توسط اسکریپت روزانه از قبل آپدیت شده‌اند)
        inst_details = self._execute_query(
            "SELECT ID, Loan_ID, DueAmount, PaidAmount, PenaltyAmount FROM [Installments] WHERE ID = ?",
            (installment_id,),
            fetch='one'
        )
        if not inst_details:
            return False, "قسط یافت نشد."

        # مقادیر را برای جلوگیری از خطا در صورت NULL بودن، با صفر جایگزین می‌کنیم
        due_amount = inst_details.get('DueAmount') or Decimal(0)
        paid_amount_before = inst_details.get('PaidAmount') or Decimal(0)
        penalty_amount = inst_details.get('PenaltyAmount') or Decimal(0)
        
        amount_paid_now = Decimal(str(amount_paid))

        # مرحله ۲: محاسبه مقادیر جدید بر اساس منطق شما
        # الف) محاسبه کل مبلغ پرداخت شده جدید
        new_paid_amount = paid_amount_before + amount_paid_now

        # ب) محاسبه بدهی کل (توتال امانت)
        new_total_amount = due_amount + penalty_amount

        # ج) محاسبه باقیمانده نهایی (پیمنت ریمین)
        new_payment_remain = new_total_amount - new_paid_amount

        # د) تعیین وضعیت جدید قسط
        new_status = 'PAID' if new_payment_remain <= 0 else 'PARTIALLY_PAID'
        
        # تولید کد پرداخت جدید
        payment_code = self._get_next_payment_code('InstallmentPayment')

        # مرحله ۳: آماده‌سازی عملیات برای ثبت در دیتابیس به صورت یک تراکنش واحد
        operations = [
            # ۱. ثبت جزئیات پرداخت در جدول Payments
            {'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Person_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'InstallmentPayment')",
             'params': (str(uuid.uuid4()), payment_code, fund_id, person_id, installment_id, payment_date, amount_paid_now, description)},
            
            # ۲. به‌روزرسانی جدول اقساط با تمام مقادیر محاسبه شده جدید
            {'query': "UPDATE [Installments] SET PaidAmount = ?, TotalAmount = ?, PaymentRemain = ?, Status = ?, PaymentDate = ? WHERE ID = ?",
             'params': (new_paid_amount, new_total_amount, new_payment_remain, new_status, payment_date, installment_id)},
            
            # ۳. افزایش موجودی صندوق
            {'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount_paid_now, fund_id)},

            # ۴. کاهش باقیمانده کل وام
            {'query': "UPDATE [Loans] SET RemainAmount = RemainAmount - ? WHERE ID = ?",
             'params': (amount_paid_now, inst_details['Loan_ID'])}
        ]
        
        return self._execute_transactional_operations(operations)

    def get_loan_header_details(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """اطلاعات کامل و محاسباتی یک وام را برای نمایش در هدر پنل اقساط برمی‌گرداند."""
        query = """
            SELECT
                l.ID as loan_uuid,
                l.Code as loan_code,
                l.Amount as total_amount,
                l.LoanTerm as loan_term,
                l.InterestRate as interest_rate,
                l.LoanDate as loan_date,
                l.RemainAmount as remaining_balance,
                p.ID as person_uuid,
                p.Code as person_code,
                p.FullName as person_name,
                (SELECT ISNULL(AVG(i.DueAmount), 0) FROM [Installments] i WHERE i.Loan_ID = l.ID) as installment_amount
            FROM [Loans] l
            JOIN [Persons] p ON l.Person_ID = p.ID
            WHERE l.ID = ?
        """
        return self._execute_query(query, (loan_id,), fetch='one')
  
    def get_loan_for_settlement(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """اطلاعات مورد نیاز برای محاسبه تسویه وام را برمی‌گرداند."""
        query = """
            SELECT
                l.Amount as principal_amount,
                l.InterestRate as interest_rate,
                l.LoanDate as loan_date,
                (SELECT ISNULL(SUM(p.Amount), 0) FROM Payments p WHERE p.Installment_ID IN (SELECT ID FROM Installments WHERE Loan_ID = l.ID)) as total_paid
            FROM Loans l
            WHERE l.ID = ?
        """
        return self._execute_query(query, (loan_id,), fetch='one')  
  
    def settle_loan(self, loan_id: str, person_id: str, fund_id: str, settlement_amount: float, description: str) -> Tuple[bool, str]:
        """وام را به طور کامل تسویه کرده و تمام اقساط باقی‌مانده را به‌روزرسانی می‌کند."""
        payment_code = self._get_next_payment_code('InstallmentPayment') # Type 1 for incoming
        today_date = jdatetime.date.today().strftime('%Y/%m/%d')

        operations = [
            # ۱. ثبت پرداخت مبلغ تسویه در جدول Payments
            {'query': "INSERT INTO Payments (ID, Code, Fund_ID, Person_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, 'Settlement')",
             'params': (str(uuid.uuid4()), payment_code, fund_id, person_id, today_date, settlement_amount, description)},
            
            # ۲. به‌روزرسانی وضعیت وام به تسویه شده
            {'query': "UPDATE Loans SET Status = 'FULLY_SETTLED', RemainAmount = 0 WHERE ID = ?",
             'params': (loan_id,)},
            
            # ۳. به‌روزرسانی تمام اقساط پرداخت نشده به وضعیت پرداخت شده
            {'query': "UPDATE Installments SET Status = 'PAID', PaymentRemain = 0 WHERE Loan_ID = ? AND Status != 'PAID'",
             'params': (loan_id,)},

            # ۴. افزایش موجودی صندوق
            {'query': "UPDATE Funds SET Inventory = Inventory + ? WHERE ID = ?",
             'params': (settlement_amount, fund_id)}
        ]
        
        return self._execute_transactional_operations(operations)  

    # --- مدیریت هزینه‌ها (Expenses) ---
    def add_expense_category(self, name: str) -> bool:
        """یک دسته‌بندی هزینه جدید به جدول Categories اضافه می‌کند."""
        new_uuid = str(uuid.uuid4())
        # فرض می‌شود برای دسته‌بندی‌ها نیز یک کد منحصر به فرد نیاز است
        new_code = self._get_next_code('Categories')
        query = "INSERT INTO [Categories] (ID, Code, Name) VALUES (?, ?, ?)"
        return self._execute_query(query, (new_uuid, new_code, name))

    def add_expense(self, category_id: str, fund_id: str, amount: float, description: str, expense_date: str) -> bool:
        """هزینه را ثبت کرده و یک تراکنش پرداخت متناظر با آن با پیشوند نوع ۶ ایجاد می‌کند."""
        expense_uuid = str(uuid.uuid4())
        # --- اصلاح شد: تولید کد برای خود هزینه ---
        expense_code = self._get_next_expense_code()
        payment_code = self._get_next_payment_code('Expense')

        operations = [
            # --- اصلاح شد: ستون Code به کوئری اضافه شد ---
            {'query': "INSERT INTO [Expenses] (ID, Code, Cat_ID, Fund_ID, Amount, Date, Description) VALUES (?, ?, ?, ?, ?, ?, ?)",
             'params': (expense_uuid, expense_code, category_id, fund_id, amount, expense_date, description)},
            
            {'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?",
             'params': (amount, fund_id)},
            
            {'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Amount, PaymentDate, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, 'Expense')",
             'params': (str(uuid.uuid4()), payment_code, fund_id, amount, expense_date, description)}
        ]
        success, _ = self._execute_transactional_operations(operations)
        return success


    def get_all_expense_categories(self) -> List[Dict[str, Any]]:
        query = "SELECT ID, Name FROM [Categories] ORDER BY Name ASC"
        return self._execute_query(query, fetch='all')

    def get_all_expenses(self) -> List[Dict[str, Any]]:
        query = """
            SELECT e.Date, c.Name as category_name, f.FundName as cashbox_name, e.Amount, e.Description
            -- --- اصلاح شد: نام جدول از Expense به Expenses تغییر کرد ---
            FROM [Expenses] e
            JOIN [Categories] c ON e.Cat_ID = c.ID
            JOIN [Funds] f ON e.Fund_ID = f.ID
            ORDER BY e.Date DESC
        """
        return self._execute_query(query, fetch='all')

    def _get_next_expense_code(self) -> int:
        """
        بیشترین کد هزینه را که با پیشوند ۴۰ شروع می‌شود پیدا کرده و عدد بعدی را به صورت امن برمی‌گرداند.
        """
        prefix = "40"
        query = f"SELECT MAX(Code) as max_code FROM [Expenses] WHERE CAST(Code AS VARCHAR(20)) LIKE '{prefix}%'"
        result = self._execute_query(query, fetch='one')

        if result and result.get('max_code') is not None:
            last_code_str = str(result['max_code'])
            
            serial_part_str = last_code_str[len(prefix):]
            
            if not serial_part_str:
                return 40001 

            next_serial_int = int(serial_part_str) + 1
            
            padded_next_serial = str(next_serial_int).zfill(len(serial_part_str))
            new_code_str = f"{prefix}{padded_next_serial}"
            
            return int(new_code_str)
        else:
            # اگر هیچ هزینه‌ای با این پیشوند وجود نداشته باشد، شماره‌گذاری از 40001 شروع می‌شود
            return 40001

    def get_expense_categories_with_total(self) -> list:
        """لیست دسته‌بندی‌های هزینه را به همراه مجموع هزینه‌های هر دسته برمی‌گرداند."""
        query = """
            SELECT 
                c.ID, 
                c.Name, 
                ISNULL(SUM(e.Amount), 0) as TotalAmount
            FROM Categories c
            LEFT JOIN Expenses e ON c.ID = e.Cat_ID
            GROUP BY c.ID, c.Name
            ORDER BY c.Name;
        """
        return self._execute_query(query, fetch='all')

    def get_expenses_by_category(self, category_id: str) -> list:
        """تمام هزینه‌های مربوط به یک دسته‌بندی خاص را برمی‌گرداند."""
        query = """
            SELECT 
                e.Date,
                e.Amount,
                e.Description,
                f.FundName
            FROM Expenses e
            LEFT JOIN Funds f ON e.Fund_ID = f.ID
            WHERE e.Cat_ID = ?
            ORDER BY e.Date DESC;
        """
        return self._execute_query(query, (category_id,), fetch='all')
    # --- پنل تراکنش‌های دستی ---

    def add_manual_transaction(self, trans_type: str, amount: float, date: str, source_id: str, destination_id: str, description: str) -> Tuple[bool, str]:
        # --- این تابع اکنون از منطق جدید کدگذاری استفاده می‌کند ---
        payment_code = self._get_next_payment_code(trans_type)
        operations = []

        if trans_type == 'transfer':
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, source_id)})
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, destination_id)})
            operations.append({'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, DestinationFund_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, 'transfer')",
                               'params': (str(uuid.uuid4()), payment_code, source_id, destination_id, date, amount, description)})
        
        elif trans_type == 'manual_payment':
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, source_id)})
            operations.append({'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Person_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, 'ManualPayment')",
                               'params': (str(uuid.uuid4()), payment_code, source_id, destination_id, date, amount, description)})

        elif trans_type == 'manual_receipt':
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, destination_id)})
            operations.append({'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, Person_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, ?, 'ManualReceipt')",
                               'params': (str(uuid.uuid4()), payment_code, destination_id, source_id, date, amount, description)})

        elif trans_type == 'capital_injection':
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, destination_id)})
            
            # --- اصلاح شد: یک علامت سوال (?) به کوئری اضافه شد ---
            operations.append({
                'query': "INSERT INTO [Payments] (ID, Code, Fund_ID, PaymentDate, Amount, Description, PaymentType) VALUES (?, ?, ?, ?, ?, ?, 'CapitalInjection')",
                'params': (str(uuid.uuid4()), payment_code, destination_id, date, amount, description)
            })

        return self._execute_transactional_operations(operations)
    
















