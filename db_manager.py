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
from utils import normalize_numbers, jalali_date_to_datetime_with_current_time 
from datetime import datetime ,timedelta
from decimal import Decimal

# مقدار ثابت برای ستون Password (الزام ۳)
DEFAULT_PASSWORD_VALUE = '7o7lflFI7ZLZvWbNXVxg1q0+X70ub69hjVvI38wsbg1I1fBDO7BuF3yHVUp86IgZ'
# مقدار ثابت برای ستون PersonStatus (الزام ۶)
DEFAULT_PERSON_STATUS = 17 
# مقدار ثابت برای ستون UserID (الزام ۵)
DEFAULT_USER_ID_VALUE = 'نرم افزار'

STATUS_PENDING_FUTURE = 30       # موعد نرسیده
STATUS_DUE_TODAY = 31            # سر رسید امروز
STATUS_PAID_FULL = 32            # پرداخت کامل سر موعد یا با تاخیر
STATUS_PARTIALLY_PAID = 33       # پرداخت ناقص (بدون جریمه)
STATUS_PARTIALLY_PAID_PENALTY = 34 # پرداخت ناقص (با جریمه)
STATUS_PAID_EARLY = 35           # پرداخت کامل قبل از موعد
STATUS_LOAN_SETTLED = 36         # تسویه کل وام
STATUS_OVERDUE_GRACE = 37        # معوق در دوره تنفس (۳ روز)
STATUS_OVERDUE_PENALTY = 38      # معوق مشمول جریمه
STATUS_DOUBTFUL = 39             # مشکوک‌الوصول
STATUS_LEGAL_PROCESS = 40        # حقوقی


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

    def _normalize_persian_numbers(self, text: str) -> str:
            """تبدیل اعداد فارسی داخل رشته به انگلیسی (۰-۹ به 0-9)."""
            if not isinstance(text, str):
                text = str(text)
            mapping = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            return text.translate(mapping)



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

    def add_customer(self, name: str, national_code: str, phone_number: str, gender: str) -> bool:
            new_uuid = str(uuid.uuid4())
            new_code = self._get_next_person_code()
            created_date = datetime.now()
            
            # --- ۱. نرمالایز کردن اعداد ---
            normalized_national_code = self._normalize_persian_numbers(national_code)
            normalized_phone_number = self._normalize_persian_numbers(phone_number)
            
            # --- اصلاح شد: نام ستون Password استفاده شد و UserID/PersonStatus اضافه شدند ---
            # فیلدهای پر شده: ID, Code, FullName, NationalID, PhoneNumber, Gender, PersonType, 
            #                IsActive, CreatedDate, UserName, Password, PersonStatus, UserID
            query = """
                INSERT INTO [Persons] 
                    (ID, Code, FullName, NationalID, PhoneNumber, Gender, PersonType, 
                    IsActive, CreatedDate, UserName, Password, PersonStatus, UserID) 
                VALUES (?, ?, ?, ?, ?, ?, N'مشتری', 1, ?, ?, ?, ?, ?)
            """
            
            # مقادیر: [UUID, Code, نام, کد ملی, موبایل, جنسیت, تاریخ ساخت, موبایل (UserName), پسورد, وضعیت, ID نرم افزار]
            params = (
                new_uuid, new_code, name, normalized_national_code, normalized_phone_number, 
                gender, created_date, 
                normalized_phone_number,              # UserName (الزام ۲)
                DEFAULT_PASSWORD_VALUE,               # Password (الزام ۳)
                DEFAULT_PERSON_STATUS,                # PersonStatus (الزام ۶)
                DEFAULT_USER_ID_VALUE                 # UserID (الزام ۵)
            )
            
            return self._execute_query(query, params)

    def update_customer(self, customer_id: str, name: str, national_code: str, phone_number: str, gender: str) -> bool:
            
            # --- ۱. نرمالایز کردن اعداد ---
            normalized_national_code = self._normalize_persian_numbers(national_code)
            normalized_phone_number = self._normalize_persian_numbers(phone_number)
            
            # --- اصلاح شد: Username و Password نیز به‌روزرسانی می‌شوند ---
            query = """
                UPDATE [Persons] 
                SET FullName = ?, NationalID = ?, PhoneNumber = ?, Gender = ?, UserName = ?, Password = ? 
                WHERE ID = ?
            """
            params = (
                name, normalized_national_code, normalized_phone_number, gender, 
                normalized_phone_number,  # UserName (الزام ۲)
                DEFAULT_PASSWORD_VALUE,   # Password (الزام ۳)
                customer_id
            )
            return self._execute_query(query, params)


    def convert_person_to_store(self, person_id: str, store_name: str, store_address: str, store_phone: str) -> bool:
            """
            تبدیل یک شخص به فروشگاه (تامین‌کننده).
            ۱. ثبت اطلاعات در جدول [Pezhvak].[Stores]
            ۲. تغییر PersonType در جدول Persons به 'تامین کننده'
            """
            # ابتدا نام شخص را برای ذخیره در جدول فروشگاه می‌گیریم
            person_data = self._execute_query("SELECT FullName, Code FROM Persons WHERE ID = ?", (person_id,), fetch='one')
            if not person_data:
                return False, "کاربر یافت نشد."
            
            person_name = person_data['FullName']
            
            # تولید ID و کدهای لازم
            store_id = str(uuid.uuid4())
            # تولید یک کد برای فروشگاه (مثلاً بر اساس کد شخص یا رندوم)
            store_code = person_data['Code'] # یا می‌توان یک کد جدید تولید کرد
            
            created_date = datetime.now()
            
            operations = [
                # ۱. درج در جدول Stores
                # دقت کنید که نام جدول طبق درخواست شما [Pezhvak].[Stores] است
                {
                    'query': """
                        INSERT INTO [demodeln_Pezhvak].[Stores] 
                        (id, code, person_id, personname, storename, storeadres, storephone, 
                        storedemand, storetotal, createdate, creatorip, creatorua, isactive)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, 1)
                    """,
                    'params': (
                        store_id, store_code, person_id, person_name, 
                        store_name, store_address, store_phone,
                        created_date, '127.0.0.1', 'DesktopApp'
                    )
                },
                
                # ۲. آپدیت نوع شخص در جدول Persons
                {
                    'query': "UPDATE Persons SET PersonType = N'تامین کننده' WHERE ID = ?",
                    'params': (person_id,)
                }
            ]
            
            return self._execute_transactional_operations(operations)



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
            # --- اصلاح شد: ستون Gender اضافه شد ---
            base_query = """
                SELECT 
                    p.ID, p.Code, p.FullName, p.NationalID, p.PhoneNumber, p.Address, p.Gender,
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
            
            # --- اصلاح شد: ستون Gender به GROUP BY اضافه شد ---
            base_query += """
                GROUP BY p.ID, p.Code, p.FullName, p.NationalID, p.PhoneNumber, p.Address, p.Gender, p.CreatedDate
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


    def get_fund_transactions(self, fund_id: str) -> List[Any]:
        """
        دریافت تراکنش‌های صندوق با نام طرف حساب دقیق (Counterparty).
        ترتیب: قدیمی به جدید (ASC) برای محاسبه دقیق مانده.
        """
        query = """
        SELECT
            p.ID,
            p.Amount,
            p.PaymentDate AS Date,
            p.Description,
            p.PaymentType AS Type,
            p.Fund_ID,
            p.DestinationFund_ID,
            p.Store_ID,

            -- --- تشخیص هوشمند طرف حساب (Counterparty) ---
            CASE
                -- 1. انتقال بین صندوق‌ها
                WHEN p.PaymentType = 'transfer' AND p.Fund_ID = ? THEN (SELECT f.FundName FROM Funds f WHERE f.ID = p.DestinationFund_ID)
                WHEN p.PaymentType = 'transfer' AND p.DestinationFund_ID = ? THEN (SELECT f.FundName FROM Funds f WHERE f.ID = p.Fund_ID)
                
                -- 2. افزایش سرمایه
                WHEN p.PaymentType IN ('capital_injection', 'CapitalInjection') THEN N'افزایش سرمایه'
                
                -- 3. پرداخت به فروشگاه (شامل StorePayment و TransfertoStore)
                -- فرمت نمایش: نام فروشگاه (نام مشتری)
                WHEN p.PaymentType IN ('StorePayment', 'TransfertoStore') THEN 
                    (SELECT s.storename FROM [demodeln_Pezhvak].[Stores] s WHERE s.id = p.Store_ID) +
                    CASE 
                        WHEN pr.FullName IS NOT NULL THEN N' (' + pr.FullName + N')' 
                        ELSE N'' 
                    END

                -- 4. سایر موارد (هزینه، وام، قسط و ...) -> نمایش نام شخص
                ELSE ISNULL(pr.FullName, N'---')
            END as Counterparty

        FROM Payments p
        LEFT JOIN Persons pr ON p.Person_ID = pr.ID
        
        WHERE p.Fund_ID = ? OR p.DestinationFund_ID = ?

        -- مرتب‌سازی صعودی (قدیم به جدید) برای محاسبه صحیح مانده
        ORDER BY p.PaymentDateEn ASC
        """
        
        # پارامترها (ترتیب ؟ ها در کوئری مهم است)
        params = (fund_id, fund_id, fund_id, fund_id)
        
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
            'capital_injection': '7',
            'Validation' : '8',
            'TransfertoStore' : '9',
            'StorePayment' : '10'
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
        # دریافت اطلاعات تکمیلی
        person_info = self._execute_query("SELECT FullName FROM Persons WHERE ID = ?", (loan_data['person_id'],), fetch='one')
        if not person_info: return False, "مشتری یافت نشد."
        person_name = person_info['FullName']

        store_id = loan_data.get('store_id')
        if not store_id: return False, "شناسه فروشگاه ارسال نشده است."
        
        store_info = self._execute_query("SELECT person_id, storename FROM [demodeln_Pezhvak].[Stores] WHERE id = ?", (store_id,), fetch='one')
        if not store_info: return False, "فروشگاه یافت نشد."
        tamin_id = store_info['person_id']
        store_name = store_info['storename']

        # تولید کدها
        loan_uuid = str(uuid.uuid4())
        loan_code = self._generate_loan_code()
        order_uuid = str(uuid.uuid4())
        
        current_gregorian_now = datetime.now()
        o_code = f"O{current_gregorian_now.strftime('%Y%m%d%H%M%S')}"
        
        payment_code_loan = self._get_next_payment_code('LoanPayment') 
        payment_code_transfer = self._get_next_payment_code('TransfertoStore') 
        payment_code_store = self._get_next_payment_code('StorePayment') 
        
        penalty_rate_decimal = Decimal(str(loan_data['penalty_rate']))
        
        current_time_str = current_gregorian_now.strftime("%H:%M:%S")
        odate_shamsi_str = f"{self._normalize_persian_numbers(loan_data['loan_date'])} {current_time_str}"
        
        # IP پیش‌فرض
        default_ip = '127.0.0.1'

        operations = [
            # A. ثبت وام
            {'query': "INSERT INTO [Loans] (ID, Code, Person_ID, Fund_ID, Status, Amount, LoanTerm, InterestRate, PenaltyRate, LoanDate, EndDate, RemainAmount) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?)",
             'params': (loan_uuid, loan_code, loan_data['person_id'], loan_data['fund_id'], loan_data['amount'],
                           loan_data['loan_term'], loan_data['interest_rate'], penalty_rate_decimal,
                           loan_data['loan_date'], loan_data['end_date'], loan_data['remain_amount'])},

            # B. ثبت سفارش
            {
                'query': """
                    INSERT INTO [demodeln_Pezhvak].[Orders]
                    (id, tamin_id, store_id, storname, Ocode, Odesc, odate, odateen, ostatus, oprice, person_id, personname, creatorip, creatorua, Loan_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'E', ?, ?, ?, ?, ?, ?)
                """,
                'params': (order_uuid, tamin_id, store_id, store_name, o_code, "خرید طلا از فروشگاه پژواک",
                    odate_shamsi_str, current_gregorian_now, loan_data['amount'], loan_data['person_id'], person_name, 
                    default_ip, 'DesktopApp', loan_uuid)
            },

            # C. پرداخت ۱ (LoanPayment)
            {
                'query': """
                    INSERT INTO [Payments] 
                    (ID, Code, Fund_ID, Person_ID, Loan_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType, DestinationFund_ID, PersonIP, PaymentDateEn, Store_ID, Order_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code_loan, 
                    None, # fund_id
                    loan_data['person_id'], 
                    loan_uuid, # loan_id
                    None, # installment_id
                    odate_shamsi_str, loan_data['amount'], loan_data['description'], 'LoanPayment',
                    None, # destinationfund_id
                    default_ip, current_gregorian_now, 
                    None, # store_id
                    None  # order_id
                )
            },

            # D. پرداخت ۲ (TransfertoStore)
            {
                'query': """
                    INSERT INTO [Payments] 
                    (ID, Code, Fund_ID, Person_ID, Loan_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType, DestinationFund_ID, PersonIP, PaymentDateEn, Store_ID, Order_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code_transfer, 
                    None, # fund_id
                    loan_data['person_id'], 
                    loan_uuid, # loan_id
                    None, 
                    odate_shamsi_str, loan_data['amount'], f"انتقال اعتبار سفارش {o_code}", 'TransfertoStore',
                    None, 
                    default_ip, current_gregorian_now, 
                    store_id, order_uuid
                )
            },

            # عملیات آپدیت Store Demand (بدهکار شدن به فروشگاه)
            {'query': "UPDATE [demodeln_Pezhvak].[Stores] SET storedemand = storedemand + ? WHERE id = ?", 'params': (loan_data['amount'], store_id)},

            # E. پرداخت ۳ (StorePayment)
            {
                'query': """
                    INSERT INTO [Payments] 
                    (ID, Code, Fund_ID, Person_ID, Loan_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType, DestinationFund_ID, PersonIP, PaymentDateEn, Store_ID, Order_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code_store, 
                    loan_data['fund_id'], # fund_id (کسر از صندوق)
                    loan_data['person_id'], 
                    loan_uuid, # loan_id
                    None, 
                    odate_shamsi_str, loan_data['amount'], "پرداخت نهایی به فروشگاه (کسر از صندوق)", 'StorePayment',
                    None, 
                    default_ip, current_gregorian_now, 
                    store_id, None # order_id (طبق درخواست نال)
                )
            },

            # عملیات تسویه فروشگاه و کسر صندوق
            {'query': "UPDATE [demodeln_Pezhvak].[Stores] SET storedemand = storedemand - ?, storetotal = storetotal + ? WHERE id = ?",
             'params': (loan_data['amount'], loan_data['amount'], store_id)},
             
            {'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (loan_data['amount'], loan_data['fund_id'])}
        ]

        # F. ثبت اقساط
        for i, inst in enumerate(installments_data):
            installment_code = f"{loan_code}-{str(i + 1).zfill(2)}"
            operations.append({
                'query': """
                    INSERT INTO [Installments] 
                        (ID, Code, Loan_ID, Person_ID, Status, DueDate, DueAmount, PaidAmount, 
                         PaymentRemain, PenaltyDays, PenaltyAmount, TotalAmount) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, ?)
                """,
                'params': (str(uuid.uuid4()), installment_code, loan_uuid, loan_data['person_id'], 
                           STATUS_PENDING_FUTURE, inst['due_date'], inst['amount_due'], inst['amount_due'], inst['amount_due'])
            })
            
        return self._execute_transactional_operations(operations)

    def get_installment_payments(self, installment_id: str) -> List[Any]:
            query = """
                SELECT ID, PaymentDate, Amount, Description 
                FROM [Payments] 
                WHERE Installment_ID = ? AND PaymentType = 'InstallmentPayment'
                ORDER BY PaymentDateEn DESC
            """
            return self._execute_query(query, (installment_id,), fetch='all')

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

    def delete_installment_payment(self, payment_id: str) -> Tuple[bool, str]:
            """
            حذف یک پرداخت قسط و برگشت زدن تمام اثرات مالی آن (صندوق، وام، وضعیت قسط).
            """
            # 1. دریافت اطلاعات پرداخت قبل از حذف
            payment_info = self._execute_query(
                "SELECT Amount, Fund_ID, Installment_ID, Person_ID FROM [Payments] WHERE ID = ?", 
                (payment_id,), fetch='one'
            )
            if not payment_info: return False, "تراکنش یافت نشد."

            amount = payment_info['Amount']
            fund_id = payment_info['Fund_ID']
            inst_id = payment_info['Installment_ID']
            
            # 2. دریافت اطلاعات قسط و وام
            inst_info = self._execute_query(
                "SELECT Loan_ID, DueDate, PaidAmount, TotalAmount, PenaltyAmount FROM [Installments] WHERE ID = ?", 
                (inst_id,), fetch='one'
            )
            loan_id = inst_info['Loan_ID']

            operations = []

            # الف) کسر مبلغ از صندوق (چون قبلاً اضافه شده بود، الان باید کم شود چون پرداخت لغو شده)
            if fund_id:
                operations.append({
                    'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?",
                    'params': (amount, fund_id)
                })

            # ب) افزایش مانده وام (بدهی برمی‌گردد)
            operations.append({
                'query': "UPDATE [Loans] SET RemainAmount = RemainAmount + ? WHERE ID = ?",
                'params': (amount, loan_id)
            })

            # ج) اصلاح مقادیر قسط
            new_paid_amount = inst_info['PaidAmount'] - Decimal(str(amount))
            # جلوگیری از منفی شدن (محض احتیاط)
            if new_paid_amount < 0: new_paid_amount = 0
            
            # محاسبه مجدد باقیمانده
            # TotalAmount شامل اصل + سود + جریمه است. 
            # اگر جریمه داشتیم و الان پرداخت حذف میشه، مبلغ جریمه سرجاش میمونه.
            new_payment_remain = inst_info['TotalAmount'] - new_paid_amount

            # د) تعیین وضعیت جدید قسط (Status) بعد از حذف پرداخت
            # باید دوباره منطق تاریخ را بررسی کنیم
            today_g = jdatetime.date.today().togregorian()
            try:
                due_date_str = str(inst_info['DueDate'])
                y, m, d = map(int, self._normalize_persian_numbers(due_date_str).split('/'))
                due_date_g = jdatetime.date(y, m, d).togregorian()
                days_diff = (today_g - due_date_g).days
            except:
                days_diff = 0

            # منطق تعیین وضعیت:
            if new_paid_amount == 0:
                # هیچ پرداختی ندارد
                if days_diff < 0: new_status = 30 # موعد نرسیده
                elif days_diff == 0: new_status = 31 # امروز
                elif days_diff <= 3: new_status = 37 # تنفس
                elif days_diff <= 35: new_status = 38 # معوق
                else: new_status = 39 # مشکوک
            elif new_payment_remain > 0:
                # پرداخت ناقص
                if inst_info['PenaltyAmount'] > 0:
                    new_status = 34
                else:
                    new_status = 33
            else:
                # هنوز کامل پرداخت شده (شاید چند تا پرداخت داشته و یکیش حذف شده)
                new_status = 32

            operations.append({
                'query': """
                    UPDATE [Installments] 
                    SET PaidAmount = ?, PaymentRemain = ?, Status = ? 
                    WHERE ID = ?
                """,
                'params': (new_paid_amount, new_payment_remain, new_status, inst_id)
            })

            # ه) حذف خود رکورد پرداخت از جدول Payments
            operations.append({
                'query': "DELETE FROM [Payments] WHERE ID = ?",
                'params': (payment_id,)
            })

            return self._execute_transactional_operations(operations)

    def get_installment_details(self, installment_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT ID, Loan_ID, DueAmount, PaidAmount, PaymentRemain FROM [Installments] WHERE ID = ?"
        return self._execute_query(query, (installment_id,), fetch='one')

    def pay_installment(self, installment_id: str, amount: float, payment_date: str, fund_id: str, description: str = "") -> Tuple[bool, str]:
        """
        ثبت پرداخت یک قسط، آپدیت مالی و وضعیت‌ها.
        """
        # 1. بررسی ورودی‌ها
        if not payment_date:
            return False, "تاریخ پرداخت الزامی است."
        if amount <= 0:
            return False, "مبلغ پرداخت باید بیشتر از صفر باشد."

        # 2. تبدیل تاریخ شمسی به میلادی برای ذخیره در PaymentDateEn
        try:
            date_parts = self._normalize_persian_numbers(payment_date).split('/')
            y, m, d = map(int, date_parts)
            payment_date_en = jdatetime.date(y, m, d).togregorian()
        except Exception as e:
            return False, f"فرمت تاریخ اشتباه است: {e}"

        # 3. دریافت اطلاعات قسط و وام
        inst = self._execute_query("SELECT * FROM Installments WHERE ID = ?", (installment_id,), fetch='one')
        if not inst: return False, "قسط یافت نشد."
        
        loan_id = inst['Loan_ID']
        person_id = inst['Person_ID']
        
        operations = []

        # الف) ثبت تراکنش در جدول Payments
        # نکته: ما PaymentDateEn را هم ذخیره می‌کنیم تا در مرتب‌سازی‌ها دقیق باشد
        operations.append({
            'query': """
                INSERT INTO Payments (
                    ID, Person_ID, Fund_ID, Amount, PaymentDate, PaymentDateEn, 
                    PaymentType, Description, Installment_ID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            'params': (
                str(uuid.uuid4()), person_id, fund_id, amount, payment_date, payment_date_en,
                'InstallmentPayment', description, installment_id
            )
        })

        # ب) افزایش موجودی صندوق
        operations.append({
            'query': "UPDATE Funds SET Inventory = Inventory + ? WHERE ID = ?",
            'params': (amount, fund_id)
        })

        # ج) کاهش مانده وام
        operations.append({
            'query': "UPDATE Loans SET RemainAmount = RemainAmount - ? WHERE ID = ?",
            'params': (amount, loan_id)
        })

        # د) آپدیت وضعیت خود قسط
        new_paid_amount = float(inst['PaidAmount']) + amount
        # محاسبه مانده جدید (TotalAmount شامل اصل + سود + جریمه است)
        new_payment_remain = float(inst['TotalAmount']) - new_paid_amount
        
        # تعیین وضعیت جدید
        if new_payment_remain <= 0:
            new_payment_remain = 0
            new_status = 32 # پرداخت کامل
            # اگر با تاخیر بوده، شاید بخواهید وضعیت را "تکمیل با تاخیر" بگذارید (اختیاری)
        else:
            # هنوز مانده دارد -> وضعیت ناقص
            if inst['PenaltyAmount'] > 0:
                new_status = 34 # ناقص با جریمه
            else:
                new_status = 33 # ناقص معمولی

        operations.append({
            'query': """
                UPDATE Installments 
                SET PaidAmount = ?, PaymentRemain = ?, Status = ?, PaymentDate = ? 
                WHERE ID = ?
            """,
            'params': (new_paid_amount, new_payment_remain, new_status, payment_date, installment_id)
        })

        # ه) بررسی تسویه کامل وام (اگر همه اقساط پاس شدند)
        # این کار بهتر است در یک تابع جدا انجام شود، اما فعلاً وضعیت وام را چک می‌کنیم
        # اگر مانده وام 0 شد، وضعیت وام را ببند
        # (این بخش پیچیده است و فعلاً می‌گذاریم کاربر دستی تسویه کند یا در آپدیت بعدی اضافه می‌کنیم)

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
        payment_code = self._get_next_payment_code('InstallmentPayment')
        current_gregorian_now = datetime.now()
        current_time_str = current_gregorian_now.strftime("%H:%M:%S")
        payment_date_shamsi_full = f"{jdatetime.date.today().strftime('%Y/%m/%d')} {current_time_str}"
        default_ip = '127.0.0.1'

        operations = [
            {
                'query': """
                    INSERT INTO [Payments] 
                    (id, code, fund_id, person_id, loan_id, installment_id, paymentdate, amount, description, paymenttype, destinationfund_id, personip, paymentdateen, store_id, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code, 
                    fund_id, 
                    person_id, 
                    loan_id, # loan_id
                    None, 
                    payment_date_shamsi_full, settlement_amount, description, 'Settlement',
                    None, 
                    default_ip, current_gregorian_now, 
                    None, None
                )
            },
            {'query': "UPDATE Loans SET Status = 'FULLY_SETTLED', RemainAmount = 0 WHERE ID = ?", 'params': (loan_id,)},
            {'query': "UPDATE Installments SET Status = ?, PaymentRemain = 0 WHERE Loan_ID = ? AND Status NOT IN (32, 35, 36)", 'params': (STATUS_LOAN_SETTLED, loan_id)},
            {'query': "UPDATE Funds SET Inventory = Inventory + ? WHERE ID = ?", 'params': (settlement_amount, fund_id)}
        ]
        
        return self._execute_transactional_operations(operations)

    def get_category_map(self, pid_value: str) -> Dict[int, str]:
            """
            یک دیکشنری از کدها و نام‌ها را برای یک PID خاص از جدول categories برمی‌گرداند.
            مثلاً برای installmentstatus: {30: 'سر رسید نشده', 31: 'سر رسید امروز', ...}
            """
            # فرض بر این است که نام جدول categories و ستون‌ها id, code, PID, name, nott هستند
            query = "SELECT code, name FROM [categories] WHERE PID = ?"
            results = self._execute_query(query, (pid_value,), fetch='all')
            
            status_map = {}
            if results:
                for row in results:
                    try:
                        # تبدیل کد به عدد صحیح برای استفاده راحت‌تر در برنامه
                        code = int(row['code'])
                        name = row['name']
                        status_map[code] = name
                    except (ValueError, KeyError):
                        continue
                        
            return status_map

    def update_installment_statuses(self):
            """وضعیت اقساط پرداخت نشده را بر اساس تاریخ امروز به‌روزرسانی می‌کند."""
            # فقط اقساطی که کامل پرداخت نشده‌اند یا تعیین تکلیف نهایی نشده‌اند را بررسی می‌کنیم
            # کدهای ۳۲, ۳۵, ۳۶ (تسویه شده‌ها) و ۴۰ (حقوقی) تغییر نمی‌کنند
            query = """
                SELECT ID, DueDate, PaidAmount, PenaltyAmount, Status 
                FROM [Installments] 
                WHERE Status NOT IN (?, ?, ?, ?)
            """
            params = (STATUS_PAID_FULL, STATUS_PAID_EARLY, STATUS_LOAN_SETTLED, STATUS_LEGAL_PROCESS)
            installments = self._execute_query(query, params, fetch='all')
            
            if not installments:
                return

            today_g = jdatetime.date.today().togregorian()
            operations = []
            
            for inst in installments:
                try:
                    inst_id = inst['ID']
                    current_status = int(inst['Status']) if inst['Status'] else 30
                    paid_amount = inst['PaidAmount'] or 0
                    penalty_amount = inst['PenaltyAmount'] or 0
                    
                    # پارس کردن تاریخ سررسید
                    due_date_str = str(inst['DueDate'])
                    y, m, d = map(int, self._normalize_persian_numbers(due_date_str).split('/'))
                    due_date_g = jdatetime.date(y, m, d).togregorian()
                    
                    days_diff = (today_g - due_date_g).days
                    new_status = current_status

                    # --- منطق اصلی تعیین وضعیت ---
                    
                    # ۱. اگر پرداختی داشته اما هنوز تسویه نشده (ناقص)
                    if paid_amount > 0:
                        if penalty_amount > 0:
                            new_status = STATUS_PARTIALLY_PAID_PENALTY # ۳۴
                        else:
                            new_status = STATUS_PARTIALLY_PAID # ۳۳
                    
                    # ۲. اگر هیچ پرداختی نداشته (صفر)
                    else:
                        if days_diff < 0:
                            new_status = STATUS_PENDING_FUTURE # ۳۰
                        elif days_diff == 0:
                            new_status = STATUS_DUE_TODAY # ۳۱
                        elif 0 < days_diff <= 3:
                            new_status = STATUS_OVERDUE_GRACE # ۳۷
                        elif 3 < days_diff <= 35:
                            new_status = STATUS_OVERDUE_PENALTY # ۳۸
                        elif days_diff > 35:
                            # اگر قبلاً حقوقی نشده باشد، مشکوک‌الوصول می‌شود
                            if current_status != STATUS_LEGAL_PROCESS:
                                new_status = STATUS_DOUBTFUL # ۳۹

                    # اگر وضعیت تغییر کرده، به لیست آپدیت اضافه کن
                    if new_status != current_status:
                        operations.append({
                            'query': "UPDATE [Installments] SET Status = ? WHERE ID = ?",
                            'params': (new_status, inst_id)
                        })

                except Exception as e:
                    logging.error(f"Error updating status for installment {inst.get('ID')}: {e}")
                    continue

            if operations:
                self._execute_transactional_operations(operations)

    def delete_loan_fully(self, loan_id: str) -> Tuple[bool, str]:
        """
        حذف کامل وام و تمام متعلقات آن بر اساس Loan_ID.
        """
        # 1. بررسی اقساط پرداخت شده
        check_query = "SELECT COUNT(*) as cnt FROM [Installments] WHERE Loan_ID = ? AND PaidAmount > 0"
        res = self._execute_query(check_query, (loan_id,), fetch='one')
        if res and res['cnt'] > 0:
            return False, "این وام دارای اقساط پرداخت شده است و نمی‌توان آن را حذف کرد."

        # 2. دریافت اطلاعات وام
        loan_info = self._execute_query("SELECT Amount, Fund_ID FROM [Loans] WHERE ID = ?", (loan_id,), fetch='one')
        if not loan_info: return False, "وام یافت نشد."
        amount = loan_info['Amount']
        fund_id = loan_info['Fund_ID']

        operations = []

        # 3. اصلاح حساب فروشگاه (پیدا کردن Store_ID از طریق Order مرتبط با Loan_ID)
        # چون به Orders ستون Loan_ID اضافه کردیم، خیلی راحت پیداش میکنیم
        order_info = self._execute_query("SELECT store_id FROM [demodeln_Pezhvak].[Orders] WHERE Loan_ID = ?", (loan_id,), fetch='one')
        
        if order_info:
            store_id = order_info['store_id']
            # چون وام حذف می‌شود:
            # خرید کنسل شده -> StoreTotal کم می‌شود
            # StoreDemand تغییری نمی‌کند (چون هم بدهی ایجاد شد و هم پرداخت شد، اثرش خنثی بود)
            operations.append({
                'query': "UPDATE [demodeln_Pezhvak].[Stores] SET storetotal = storetotal - ? WHERE id = ?",
                'params': (amount, store_id)
            })

        # 4. حذف داده‌ها بر اساس Loan_ID (کاملاً امن و دقیق)
        
        # الف) حذف سفارش‌ها
        operations.append({'query': "DELETE FROM [demodeln_Pezhvak].[Orders] WHERE Loan_ID = ?", 'params': (loan_id,)})
        
        # ب) حذف پرداخت‌ها (شامل کدهای ۱، ۹، ۱۰ و هر پرداختی که مربوط به این وام بوده)
        operations.append({'query': "DELETE FROM [Payments] WHERE Loan_ID = ?", 'params': (loan_id,)})
        
        # ج) حذف اقساط
        operations.append({'query': "DELETE FROM [Installments] WHERE Loan_ID = ?", 'params': (loan_id,)})
        
        # د) حذف خود وام
        operations.append({'query': "DELETE FROM [Loans] WHERE ID = ?", 'params': (loan_id,)})

        # 5. برگشت پول به صندوق
        if fund_id:
            operations.append({
                'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?",
                'params': (amount, fund_id)
            })

        return self._execute_transactional_operations(operations)



    # --- مدیریت هزینه‌ها (Expenses) ---
    def add_expense_category(self, name: str, pid: str = None) -> bool:
        """افزودن یک دسته‌بندی هزینه جدید."""
        cat_id = str(uuid.uuid4())
        code = self._get_next_expense_category_code()
        
        # ستون total به صورت پیش‌فرض 0 است
        query = "INSERT INTO [ExpenseCategories] (id, code, pid, name, total) VALUES (?, ?, ?, ?, 0)"
        return self._execute_query(query, (cat_id, code, pid, name))

    def add_expense(self, category_id: str, fund_id: str, amount: float, description: str, expense_date: str) -> bool:
        expense_uuid = str(uuid.uuid4())
        payment_code = self._get_next_payment_code('Expense')
        
        current_gregorian_now = datetime.now()
        current_time_str = current_gregorian_now.strftime("%H:%M:%S")
        payment_date_shamsi_full = f"{self._normalize_persian_numbers(expense_date)} {current_time_str}"
        default_ip = '127.0.0.1'

        operations = [
            {'query': "INSERT INTO [Expenses] (id, code, cat_id, fund_id, amount, description, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
             'params': (expense_uuid, self._get_next_expense_code(), category_id, fund_id, amount, description, expense_date)},
            
            {'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, fund_id)},
            {'query': "UPDATE [ExpenseCategories] SET total = total + ? WHERE id = ?", 'params': (amount, category_id)},

            {
                'query': """
                    INSERT INTO [Payments] 
                    (ID, Code, Fund_ID, Person_ID, Loan_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType, DestinationFund_ID, PersonIP, PaymentDateEn, Store_ID, Order_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code, 
                    fund_id, 
                    None, # person_id
                    None, # loan_id
                    None, 
                    payment_date_shamsi_full, amount, description, 'Expense',
                    None, 
                    default_ip, current_gregorian_now, 
                    None, None
                )
            }
        ]
        success, _ = self._execute_transactional_operations(operations)
        return success


    def get_expense_categories(self) -> List[Any]:
        """لیست دسته‌بندی‌های هزینه را با تمام جزئیات (شامل جمع کل) برمی‌گرداند."""
        # اصلاح شد: افزودن ستون‌های code و total به کوئری
        query = "SELECT id, code, name, total FROM [ExpenseCategories]"
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

    def _get_next_expense_category_code(self):
            """تولید کد بعدی برای دسته‌بندی هزینه (مثلاً از 100 شروع می‌شود)."""
            query = "SELECT MAX(CAST(code AS INT)) as max_code FROM [ExpenseCategories]"
            result = self._execute_query(query, fetch='one')
            if result and result['max_code']:
                return str(int(result['max_code']) + 1)
            return "100" # کد شروع


    def add_manual_transaction(self, trans_type: str, amount: float, date: str, source_id: str, destination_id: str, description: str) -> Tuple[bool, str]:
        payment_code = self._get_next_payment_code(trans_type)
        operations = []
        
        current_gregorian_now = datetime.now()
        current_time_str = current_gregorian_now.strftime("%H:%M:%S")
        payment_date_shamsi_full = f"{self._normalize_persian_numbers(date)} {current_time_str}"
        default_ip = '127.0.0.1'
        
        # پارامترهای مشترک (ستون‌های 11 تا 15)
        # destinationfund_id (برای transfer پر میشه), personip, paymentdateen, store_id, order_id
        
        if trans_type == 'transfer':
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, source_id)})
            operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, destination_id)})
            operations.append({
                'query': """
                    INSERT INTO [Payments] 
                    (id, code, fund_id, person_id, loan_id, installment_id, paymentdate, amount, description, paymenttype, destinationfund_id, personip, paymentdateen, store_id, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code, 
                    source_id, # fund_id (مبدا)
                    None, None, None, 
                    payment_date_shamsi_full, amount, description, 'transfer',
                    destination_id, # destinationfund_id (مقصد)
                    default_ip, current_gregorian_now, None, None
                )
            })
        
        elif trans_type in ['manual_payment', 'manual_receipt', 'capital_injection']:
            # تنظیم پارامترها بر اساس نوع
            fund_id = source_id if trans_type == 'manual_payment' else destination_id
            person_id = destination_id if trans_type == 'manual_payment' else (source_id if trans_type == 'manual_receipt' else None)
            
            # آپدیت صندوق
            if trans_type == 'manual_payment':
                operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, fund_id)})
            else:
                operations.append({'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, fund_id)})
            
            operations.append({
                'query': """
                    INSERT INTO [Payments] 
                    (ID, Code, Fund_ID, Person_ID, Loan_ID, Installment_ID, PaymentDate, Amount, Description, PaymentType, DestinationFund_ID, PersonIP, PaymentDateEn, Store_ID, Order_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                'params': (
                    str(uuid.uuid4()), payment_code, 
                    fund_id, 
                    person_id, 
                    None, None, 
                    payment_date_shamsi_full, amount, description, trans_type,
                    None, 
                    default_ip, current_gregorian_now, None, None
                )
            })

        return self._execute_transactional_operations(operations)
    
    def delete_manual_transaction(self, payment_id: str) -> Tuple[bool, str]:
        """
        حذف تراکنش‌های دستی (انتقال، دستی، سرمایه) و اصلاح موجودی صندوق‌ها.
        """
        # 1. دریافت اطلاعات تراکنش
        trans = self._execute_query(
            "SELECT Amount, Fund_ID, DestinationFund_ID, PaymentType FROM Payments WHERE ID = ?", 
            (payment_id,), fetch='one'
        )
        if not trans: return False, "تراکنش یافت نشد."

        p_type = trans['PaymentType']
        amount = trans['Amount']
        fund_id = trans['Fund_ID']       # معمولا صندوق مبدا
        dest_id = trans['DestinationFund_ID'] # صندوق مقصد (در انتقال)

        operations = []

        # 2. منطق معکوس کردن پول بر اساس نوع تراکنش
        
        if p_type == 'transfer':
            # در انتقال: پول از مبدا کم شده و به مقصد اضافه شده بود.
            # اصلاح: به مبدا اضافه کن، از مقصد کم کن.
            operations.append({'query': "UPDATE Funds SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, fund_id)})
            operations.append({'query': "UPDATE Funds SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, dest_id)})

        elif p_type == 'manual_payment': # پرداخت دستی
            # پول کم شده بود -> باید برگردد (اضافه شود)
            operations.append({'query': "UPDATE Funds SET Inventory = Inventory + ? WHERE ID = ?", 'params': (amount, fund_id)})

        elif p_type == 'manual_receipt': # دریافت دستی
            # پول اضافه شده بود -> باید کم شود
            # نکته: در manual_receipt در تابع insert، صندوق مقصد (destination) پر شده بود اما fund_id هم گاهی استفاده میشه
            # بیایید چک کنیم add_manual_transaction چطور ثبت کرده.
            # در کد شما: manual_receipt -> Fund_ID = destination_id ثبت شده بود.
            # پس fund_id همان صندوقی است که پول گرفته.
            operations.append({'query': "UPDATE Funds SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, fund_id)})

        elif p_type == 'capital_injection': # افزایش سرمایه
            # پول اضافه شده بود -> باید کم شود
            # در کد شما: Fund_ID = destination_id ثبت شده بود.
            operations.append({'query': "UPDATE Funds SET Inventory = Inventory - ? WHERE ID = ?", 'params': (amount, fund_id)})

        else:
            return False, "این نوع تراکنش سیستمی است و از اینجا قابل حذف نیست."

        # 3. حذف خود رکورد
        operations.append({'query': "DELETE FROM Payments WHERE ID = ?", 'params': (payment_id,)})

        return self._execute_transactional_operations(operations)

    def get_expenses_by_category(self, category_id: str) -> List[Any]:
        """دریافت تمام تراکنش‌های هزینه مربوط به یک دسته‌بندی."""
        query = """
            SELECT e.ID, e.Amount, e.date, e.Description, f.FundName as FundName
            FROM [Expenses] e
            LEFT JOIN [Funds] f ON e.fund_id = f.ID
            WHERE e.cat_id = ?
            ORDER BY e.date DESC
        """
        return self._execute_query(query, (category_id,), fetch='all')

    def delete_expense(self, expense_id: str) -> Tuple[bool, str]:
            """
            حذف یک هزینه و بازگشت پول به صندوق و اصلاح جمع کل دسته‌بندی.
            """
            # الف) دریافت اطلاعات هزینه قبل از حذف
            exp_info = self._execute_query(
                "SELECT Amount, fund_id, cat_id FROM [Expenses] WHERE ID = ?", 
                (expense_id,), fetch='one'
            )
            if not exp_info: return False, "هزینه یافت نشد."
            
            amount = exp_info['Amount']
            fund_id = exp_info['fund_id']
            cat_id = exp_info['cat_id']

            operations = []

            # ب) برگشت پول به صندوق (چون هزینه حذف شده، پول برمی‌گردد)
            operations.append({
                'query': "UPDATE [Funds] SET Inventory = Inventory + ? WHERE ID = ?",
                'params': (amount, fund_id)
            })

            # ج) اصلاح جمع کل دسته‌بندی (Total کم می‌شود)
            operations.append({
                'query': "UPDATE [ExpenseCategories] SET total = total - ? WHERE id = ?",
                'params': (amount, cat_id)
            })

            # د) حذف از جدول Payments (اگر ثبت شده باشد)
            # ما در Payments ستون Order_ID و ... داریم، اما برای هزینه لینک مستقیم نداشتیم
            # مگر اینکه در Description یا روشی دیگر پیدایش کنیم.
            # اما چون PaymentType = 'Expense' است و مبلغ و تاریخ یکی است، سعی می‌کنیم پیدایش کنیم.
            # بهترین کار این است که در آینده ID هزینه را در Payments ذخیره کنیم.
            # فعلاً بر اساس شرط‌های منطقی حذف می‌کنیم:
            # (دقت کنید این روش ممکن است اگر دو هزینه دقیقاً مشابه باشند یکی را اشتباه پاک کند، اما چاره فعلی این است)
            # اگر ستون Expense_ID در پیمنت نداریم، فعلاً این بخش را نادیده می‌گیریم یا هوشمند عمل می‌کنیم.
            # *بهتر است فعلا دستی از پیمنت پاک نکنیم تا خطا ندهد، مگر اینکه ID را داشته باشیم*
            # اما چون موجودی صندوق را اصلاح کردیم، باید پیمنت هم پاک شود تا تراز بماند.
            
            # فرض: حذف آخرین پیمنت هزینه با این مبلغ و صندوق (روش تقریبی)
            operations.append({
                'query': """
                    DELETE FROM [Payments] 
                    WHERE ID IN (
                        SELECT TOP 1 ID FROM [Payments] 
                        WHERE Fund_ID = ? AND Amount = ? AND PaymentType = 'Expense'
                        ORDER BY PaymentDateEn DESC
                    )
                """,
                'params': (fund_id, amount)
            })

            # ه) حذف خود رکورد هزینه
            operations.append({
                'query': "DELETE FROM [Expenses] WHERE ID = ?",
                'params': (expense_id,)
            })

            return self._execute_transactional_operations(operations)


    def get_all_customers_with_details(self) -> List[Any]:
            """
            دریافت لیست مشتریان همراه با مجموع بدهی آن‌ها.
            ترتیب خروجی برای پنل گزارش مهم است: (id, name, national_code, phone, address, total_debt)
            """
            query = """
                SELECT 
                    p.ID, 
                    p.FullName, 
                    p.NationalID, 
                    p.PhoneNumber, 
                    p.Address,
                    -- محاسبه مجموع مانده وام‌های فعال
                    ISNULL((SELECT SUM(l.RemainAmount) FROM Loans l WHERE l.Person_ID = p.ID AND l.Status = 'ACTIVE'), 0) as TotalDebt
                FROM Persons p
                ORDER BY p.FullName
            """
            return self._execute_query(query, fetch='all')


    def get_customer_loans(self, person_id: str) -> List[Any]:
            """دریافت وام‌های یک مشتری خاص برای پر کردن کامبوباکس."""
            # خروجی: loan_id, readable_id (code), amount, term
            query = "SELECT ID, Code, Amount, LoanTerm FROM Loans WHERE Person_ID = ?"
            return self._execute_query(query, (person_id,), fetch='all')


    def get_transactions_by_cashbox(self, cashbox_id: str) -> List[Any]:
        """
        دریافت تراکنش‌های صندوق برای گزارش‌گیری.
        از همان منطق get_fund_transactions استفاده می‌کنیم اما مستقل صدا زده می‌شود.
        """
        return self.get_fund_transactions(cashbox_id)
    

    def get_full_customer_report_data(self, person_id: str):
        """
        دریافت تمام اطلاعات وام‌ها و اقساط یک مشتری برای گزارش پرونده.
        خروجی: (لیست وام‌ها، دیکشنری اقساط به تفکیک وام)
        """
        # 1. دریافت وام‌ها
        loans = self._execute_query("SELECT * FROM Loans WHERE Person_ID = ? ORDER BY LoanDate DESC", (person_id,), fetch='all')
        
        # 2. دریافت اقساط
        installments = self._execute_query("SELECT * FROM Installments WHERE Person_ID = ? ORDER BY DueDate ASC", (person_id,), fetch='all')
        
        # 3. گروه‌بندی اقساط بر اساس ID وام
        installments_by_loan = {}
        
        # مقداردهی اولیه لیست برای هر وام
        if loans:
            for loan in loans:
                # پشتیبانی از دسترسی دیکشنری و تاپل
                l_id = loan['ID'] if isinstance(loan, dict) else loan[0]
                installments_by_loan[l_id] = []
        
        if installments:
            for inst in installments:
                l_id = inst['Loan_ID'] if isinstance(inst, dict) else inst[2] # فرض بر اینکه ایندکس 2 مربوط به Loan_ID است
                if l_id in installments_by_loan:
                    installments_by_loan[l_id].append(inst)
                    
        return loans, installments_by_loan
    

    def get_installments_by_date_range(self, start_date: str, end_date: str, status_filter: str) -> List[Any]:
            """
            دریافت اقساط به همراه کد وام (اصلاح شده).
            """
            s_date = self._normalize_persian_numbers(start_date)
            e_date = self._normalize_persian_numbers(end_date)
            
            # اصلاح کوئری: اضافه کردن JOIN با جدول Loans برای گرفتن کد وام
            base_query = """
                SELECT 
                    i.DueDate,      -- 0
                    i.DueAmount,    -- 1
                    i.PaidAmount,   -- 2
                    i.Status,       -- 3
                    p.FullName,     -- 4
                    p.PhoneNumber,  -- 5
                    i.Code,         -- 6 (کد قسط)
                    l.Code as LoanCode -- 7 (کد وام - جدید اضافه شد)
                FROM Installments i
                JOIN Persons p ON i.Person_ID = p.ID
                JOIN Loans l ON i.Loan_ID = l.ID  -- اتصال به جدول وام‌ها
                WHERE i.DueDate >= ? AND i.DueDate <= ?
            """
            params = [s_date, e_date]

            if status_filter == "پرداخت شده":
                base_query += " AND i.Status IN (32, 35, 36)"
            elif status_filter == "پرداخت نشده":
                base_query += " AND i.Status IN (30, 31, 37, 38, 39, 40)"
            elif status_filter == "پرداخت ناقص":
                base_query += " AND i.Status IN (33, 34)"

            base_query += " ORDER BY i.DueDate ASC"
            
            return self._execute_query(base_query, tuple(params), fetch='all')





