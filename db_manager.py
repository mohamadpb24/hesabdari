# db_manager.py (نسخه نهایی سازگار با UUID و کدهای خوانا)


import mysql.connector
from mysql.connector import pooling, Error
import configparser
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Iterator, Tuple
import jdatetime
import uuid
import time


# --- راه‌اندازی لاگ‌گیری برای خطایابی بهتر ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    _pool = None

    def __init__(self):
        if DatabaseManager._pool is None:
            try:
                db_config = self._get_db_config()
                DatabaseManager._pool = pooling.MySQLConnectionPool(pool_name="hesabdari_pool", pool_size=10, **db_config)
                logging.info("✅ استخر اتصالات (Connection Pool) با موفقیت ایجاد شد.")
            except Error as err:
                logging.error(f"❌ خطا در ایجاد استخر اتصالات: {err}")
                raise

    def _get_db_config(self) -> Dict[str, str]:
        """اطلاعات اتصال به پایگاه داده را از فایل config.ini می‌خواند."""
        config = configparser.ConfigParser()
        config.read('config.ini')
        # اطمینان از اینکه نام دیتابیس جدید خوانده می‌شود
        db_config = dict(config['mysql'])
        db_config['database'] = db_config.get('database', 'installment_sales_db_v2')
        return db_config

    @contextmanager
    def get_connection(self):
        """یک اتصال امن از استخر اتصالات فراهم می‌کند."""
        if self._pool is None:
            raise ConnectionError("استخر اتصالات مقداردهی اولیه نشده است.")
        connection = self._pool.get_connection()
        try:
            yield connection
        finally:
            if connection.is_connected():
                connection.close()

    # --- توابع کمکی برای تولید کدهای خوانا ---

    def _generate_readable_id(self, prefix: str, table_name: str, column_name: str = 'readable_id') -> str:
        query = f"SELECT {column_name} FROM `{table_name}` WHERE {column_name} LIKE %s ORDER BY {column_name} DESC LIMIT 1"
        last_id_result = self._execute_query(query, (f"{prefix}-%",), fetch='one')
        if last_id_result and last_id_result.get(column_name):
            last_number = int(last_id_result[column_name].split('-')[1])
            return f"{prefix}-{last_number + 1}"
        return f"{prefix}-10001"

    def _generate_monthly_readable_id(self, prefix: str, table_name: str) -> str:
        now = jdatetime.date.today()
        date_prefix = now.strftime("%y%m")
        full_prefix = f"{prefix}-{date_prefix}-"
        query = f"SELECT readable_id FROM `{table_name}` WHERE readable_id LIKE %s ORDER BY readable_id DESC LIMIT 1"
        last_id_result = self._execute_query(query, (f"{full_prefix}%",), fetch='one')
        if last_id_result and last_id_result.get('readable_id'):
            last_sequence = int(last_id_result['readable_id'].split('-')[2])
            return f"{full_prefix}{last_sequence + 1:04d}"
        return f"{full_prefix}0001"

    # --- توابع اصلی اجرای کوئری ---

    def _execute_query(self, query: str, params: tuple = None, fetch: Optional[str] = None, dictionary_cursor: bool = True) -> Any:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=dictionary_cursor)
                cursor.execute(query, params or ())

                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                    return True

                if fetch == 'one':
                    return cursor.fetchone()
                if fetch == 'all':
                    return cursor.fetchall()
                return cursor
        except Error as err:
            logging.error(f"❌ خطا در اجرای کوئری: {query} | پارامترها: {params} | خطا: {err}")
            return None if fetch else False

    def _execute_transactional_operations(self, operations: List[Dict[str, Any]]) -> Tuple[bool, str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                conn.start_transaction()

                for op in operations:
                    cursor.execute(op['query'], op.get('params', ()))

                conn.commit()
                return True, "عملیات با موفقیت انجام شد."
        except Error as err:
            logging.error(f"❌ خطا در تراکنش: {err}")
            conn.rollback()
            return False, f"خطا در عملیات پایگاه داده: {err}"

    # --- مدیریت کاربران (مشتریان) ---

    def add_customer(self, name: str, national_code: str, phone_number: str, address: str) -> bool:
        new_uuid = str(uuid.uuid4())
        new_readable_id = self._generate_readable_id('C', 'users')
        query = "INSERT INTO users (id, readable_id, user_type, status, name, national_code, phone_number, address) VALUES (%s, %s, 'OFFLINE', 'CREDIT_ACTIVE', %s, %s, %s, %s)"
        return self._execute_query(query, (new_uuid, new_readable_id, name, national_code, phone_number, address))

    def update_customer(self, customer_id: str, name: str, national_code: str, phone_number: str, address: str) -> bool:
        query = "UPDATE users SET name = %s, national_code = %s, phone_number = %s, address = %s WHERE id = %s"
        return self._execute_query(query, (name, national_code, phone_number, address, customer_id))

    def delete_customer(self, customer_id: str) -> bool:
        query = "DELETE FROM users WHERE id = %s"
        return self._execute_query(query, (customer_id,))

    def get_all_customers(self) -> List[Tuple]:
        query = "SELECT id, name FROM users ORDER BY created_at DESC"
        return self._execute_query(query, fetch='all', dictionary_cursor=False)

    def get_customers_paginated(self, page: int, page_size: int, search_query: str = "") -> List[Dict[str, Any]]:
        offset = (page - 1) * page_size
        base_query = """
            SELECT u.id, u.readable_id, u.name, u.national_code, u.phone_number, u.address, u.total_debt
            FROM users u
        """
        params = []
        if search_query:
            base_query += " WHERE u.name LIKE %s OR u.national_code LIKE %s OR u.phone_number LIKE %s"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
            
        base_query += " ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        
        return self._execute_query(base_query, tuple(params), fetch='all')
    
    def get_customers_count(self, search_query: str = "") -> int:
        base_query = "SELECT COUNT(id) as count FROM users"
        params = []
        if search_query:
            base_query += " WHERE name LIKE %s OR national_code LIKE %s OR phone_number LIKE %s"
            search_term = f"%{search_query}%"
            params = [search_term, search_term, search_term]
        
        result = self._execute_query(base_query, tuple(params), fetch='one')
        return result['count'] if result else 0

    # --- مدیریت وام‌ها و اقساط ---
    def create_loan_and_installments(self, loan_data: Dict, installments_data: List[Dict]) -> Tuple[bool, str]:
        loan_uuid = str(uuid.uuid4())
        loan_readable_id = self._generate_monthly_readable_id('L', 'loans')
        
        operations = [
            {'query': "INSERT INTO loans (id, readable_id, customer_id, cash_box_id, status, amount, loan_term, interest_rate, start_date) VALUES (%s, %s, %s, %s, 'ACTIVE', %s, %s, %s, %s)",
             'params': (loan_uuid, loan_readable_id, loan_data['customer_id'], loan_data['cash_box_id'], loan_data['amount'], loan_data['loan_term'], loan_data['interest_rate'], loan_data['start_date'])},
            {'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s",
             'params': (loan_data['amount'], loan_data['cash_box_id'])},
            {'query': "INSERT INTO transactions (id, readable_id, type, amount, date, source_id, destination_id, description) VALUES (%s, %s, 'loan_payment', %s, %s, %s, %s, %s)",
             'params': (str(uuid.uuid4()), f"T-{loan_readable_id}", loan_data['amount'], loan_data['transaction_date'], loan_data['cash_box_id'], loan_data['customer_id'], loan_data['description'])}
        ]

        for i, inst in enumerate(installments_data):
            operations.append({
                'query': "INSERT INTO installments (id, readable_id, loan_id, status, due_date, amount_due) VALUES (%s, %s, %s, 'PENDING', %s, %s)",
                'params': (str(uuid.uuid4()), f"{loan_readable_id}-{i+1:02d}", loan_uuid, inst['due_date'], inst['amount_due'])
            })
        
        return self._execute_transactional_operations(operations)

    def get_customer_loans(self, customer_id: str) -> list:
        query = "SELECT id, readable_id, amount, loan_term FROM loans WHERE customer_id = %s"
        return self._execute_query(query, (customer_id,), fetch='all', dictionary_cursor=False)

    def get_loan_installments(self, loan_id: str) -> list:
        query = "SELECT id, readable_id, due_date, amount_due, amount_paid, payment_date, status FROM installments WHERE loan_id = %s ORDER BY readable_id ASC"
        return self._execute_query(query, (loan_id,), fetch='all', dictionary_cursor=False)

    def get_installment_details(self, installment_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT id, loan_id, readable_id, due_date, amount_due, amount_paid FROM installments WHERE id = %s"
        return self._execute_query(query, (installment_id,), fetch='one')

    def is_loan_fully_paid(self, loan_id: str) -> bool:
        query = "SELECT status FROM loans WHERE id = %s"
        result = self._execute_query(query, (loan_id,), fetch='one')
        return result and result['status'] == 'FULLY_SETTLED'

    def has_paid_installments(self, loan_id: str) -> bool:
        query = "SELECT COUNT(id) as count FROM installments WHERE loan_id = %s AND amount_paid > 0"
        result = self._execute_query(query, (loan_id,), fetch='one')
        return result and result['count'] > 0

    def pay_installment(self, customer_id: str, installment_id: str, amount_paid: float, cash_box_id: str, description: str, payment_date: str) -> Tuple[bool, str]:
        installment_info = self.get_installment_details(installment_id)
        if not installment_info:
            return False, "قسط مورد نظر یافت نشد."

        new_total_paid = installment_info['amount_paid'] + amount_paid
        new_status = 'PAID' if new_total_paid >= installment_info['amount_due'] else 'PARTIALLY_PAID'
        
        # --- شروع تغییرات ---
        # اضافه کردن مهر زمانی برای منحصر به فرد کردن شناسه تراکنش
        trans_readable_id = f"T-INST-{installment_info['readable_id']}-{int(time.time())}"
        # --- پایان تغییرات ---

        operations = [
            {'query': "UPDATE installments SET amount_paid = %s, status = %s, payment_date = %s WHERE id = %s",
             'params': (new_total_paid, new_status, payment_date, installment_id)},
            {'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s",
             'params': (amount_paid, cash_box_id)},
            {'query': "INSERT INTO transactions (id, readable_id, type, amount, date, source_id, destination_id, description) VALUES (%s, %s, 'installment_received', %s, %s, %s, %s, %s)",
             'params': (str(uuid.uuid4()), trans_readable_id, amount_paid, payment_date, customer_id, cash_box_id, description)}
        ]
        
        return self._execute_transactional_operations(operations)

    def get_loan_header_details(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """اطلاعات کامل و محاسباتی یک وام را برای نمایش در هدر پنل اقساط برمی‌گرداند."""
        query = """
            SELECT
                l.id AS loan_uuid,
                l.readable_id AS loan_readable_id,
                l.amount AS total_amount,
                l.loan_term,
                l.interest_rate,
                (SELECT t.date FROM transactions t WHERE t.readable_id = CONCAT('T-', l.readable_id) LIMIT 1) as grant_date,
                u.id AS customer_uuid,
                u.readable_id AS customer_readable_id,
                COALESCE(SUM(i.amount_due), 0) as total_due,
                COALESCE(SUM(i.amount_paid), 0) as total_paid,
                COALESCE(AVG(i.amount_due), 0) as installment_amount
            FROM loans l
            JOIN users u ON l.customer_id = u.id
            LEFT JOIN installments i ON l.id = i.loan_id
            WHERE l.id = %s
            GROUP BY l.id, u.id;
        """
        result = self._execute_query(query, (loan_id,), fetch='one')
        if result:
            result['remaining_balance'] = result['total_due'] - result['total_paid']
        return result    
    
    # --- مدیریت هزینه‌ها ---

    def add_expense_category(self, name: str) -> bool:
        new_uuid = str(uuid.uuid4())
        query = "INSERT INTO expense_categories (id, name) VALUES (%s, %s)"
        return self._execute_query(query, (new_uuid, name))

    def get_all_expense_categories(self) -> List[Dict[str, Any]]:
        query = "SELECT id, name FROM expense_categories ORDER BY name ASC"
        return self._execute_query(query, fetch='all')

    def add_expense(self, category_id: str, cashbox_id: str, amount: float, description: str, expense_date: str) -> bool:
        expense_uuid = str(uuid.uuid4())
        expense_readable_id = self._generate_monthly_readable_id('E', 'expenses')

        operations = [
            {'query': """
                INSERT INTO expenses (id, readable_id, category_id, cashbox_id, amount, description, expense_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
             """, 'params': (expense_uuid, expense_readable_id, category_id, cashbox_id, amount, description, expense_date)},
            
            {'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s", 'params': (amount, cashbox_id)},
            
            {'query': """
                INSERT INTO transactions (id, readable_id, type, amount, date, source_id, description)
                VALUES (%s, %s, 'expense', %s, %s, %s, %s)
             """, 'params': (str(uuid.uuid4()), f"T-{expense_readable_id}", amount, expense_date, cashbox_id, description)}
        ]
        success, _ = self._execute_transactional_operations(operations)
        return success

    def get_all_expenses(self) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                e.readable_id, e.expense_date, ec.name as category_name, cb.name as cashbox_name,
                e.amount, e.description
            FROM expenses e
            JOIN expense_categories ec ON e.category_id = ec.id
            JOIN cash_boxes cb ON e.cashbox_id = cb.id
            ORDER BY e.expense_date DESC, e.created_at DESC
        """
        return self._execute_query(query, fetch='all')
    
    # --- مدیریت صندوق‌ها ---

    def add_cash_box(self, name: str, initial_balance: float = 0) -> bool:
        new_uuid = str(uuid.uuid4())
        new_readable_id = self._generate_readable_id('CB', 'cash_boxes')
        query = "INSERT INTO cash_boxes (id, readable_id, name, balance) VALUES (%s, %s, %s, %s)"
        return self._execute_query(query, (new_uuid, new_readable_id, name, initial_balance))
    
    def update_cash_box(self, box_id: str, name: str, balance: float) -> bool:
        query = "UPDATE cash_boxes SET name = %s, balance = %s WHERE id = %s"
        return self._execute_query(query, (name, balance, box_id))
    
    def delete_cash_box(self, box_id: str) -> bool:
        query = "DELETE FROM cash_boxes WHERE id = %s"
        return self._execute_query(query, (box_id,))

    def get_all_cash_boxes(self) -> List[Tuple]:
        return self._execute_query("SELECT id, name, balance FROM cash_boxes", fetch='all', dictionary_cursor=False)

    def get_cash_box_name(self, box_id: str) -> str:
        query = "SELECT name FROM cash_boxes WHERE id = %s"
        result = self._execute_query(query, (box_id,), fetch='one')
        return result['name'] if result else "N/A"

    def get_transactions_with_running_balance(self, cashbox_id: str) -> List[Dict[str, Any]]:
        transactions_query = """
            SELECT 
                t.*,
                c_source.name as source_customer,
                c_dest.name as dest_customer,
                cb_source.name as source_cashbox,
                cb_dest.name as dest_cashbox
            FROM transactions t
            LEFT JOIN users c_source ON t.source_id = c_source.id AND t.type IN ('installment_received', 'settlement_received', 'manual_receipt')
            LEFT JOIN users c_dest ON t.destination_id = c_dest.id AND t.type IN ('loan_payment', 'manual_payment')
            LEFT JOIN cash_boxes cb_source ON t.source_id = cb_source.id AND t.type = 'transfer'
            LEFT JOIN cash_boxes cb_dest ON t.destination_id = cb_dest.id AND t.type = 'transfer'
            WHERE t.source_id = %(cashbox_id)s OR t.destination_id = %(cashbox_id)s
            ORDER BY t.created_at DESC
        """
        transactions = self._execute_query(transactions_query, {'cashbox_id': cashbox_id}, fetch='all')

        if not transactions:
            return []

        current_balance_result = self._execute_query("SELECT balance FROM cash_boxes WHERE id = %s", (cashbox_id,), fetch='one')
        running_balance = current_balance_result['balance'] if current_balance_result else 0

        for t in transactions:
            t['balance_after'] = running_balance
            
            if t['destination_id'] == cashbox_id:
                running_balance -= t['amount']
            elif t['source_id'] == cashbox_id:
                running_balance += t['amount']
            
            if t['type'] == 'transfer':
                t['counterparty_name'] = t['dest_cashbox'] if t['destination_id'] != cashbox_id else t['source_cashbox']
            elif t['type'] in ['loan_payment', 'manual_payment']:
                t['counterparty_name'] = t['dest_customer']
            elif t['type'] in ['installment_received', 'settlement_received', 'manual_receipt']:
                t['counterparty_name'] = t['source_customer']
            elif t['type'] == 'expense':
                t['counterparty_name'] = "هزینه داخلی"
            elif t['type'] == 'capital_injection':
                t['counterparty_name'] = "سرمایه گذار"

        return transactions[::-1]


    # --- داشبورد و آمار ---

    def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        query = """
            SELECT
                (SELECT COALESCE(SUM(balance), 0) FROM cash_boxes) as total_balance,
                (SELECT COALESCE(SUM(amount), 0) FROM loans WHERE status = 'ACTIVE') as total_loan_principal,
                (SELECT COALESCE(COUNT(id), 0) FROM users) as total_customers,
                (SELECT COALESCE(SUM(amount), 0) FROM expenses) as total_expenses,
                (SELECT COUNT(id) FROM loans WHERE status = 'ACTIVE') as active_loans,
                (SELECT COUNT(id) FROM loans WHERE status = 'FULLY_SETTLED') as settled_loans,
                (SELECT COALESCE(SUM(amount_due), 0) FROM installments) as total_due,
                (SELECT COALESCE(SUM(amount_paid), 0) FROM installments) as total_paid,
                (SELECT COALESCE(SUM(amount), 0) FROM loans) as all_time_principal
        """
        stats = self._execute_query(query, fetch='one')
        if not stats: return None
        
        # اطمینان از اینکه مقادیر None به صفر تبدیل شوند
        total_due = stats.get('total_due') or 0
        total_paid = stats.get('total_paid') or 0
        all_time_principal = stats.get('all_time_principal') or 0

        # محاسبه سود
        stats['total_projected_profit'] = total_due - all_time_principal
        stats['total_receivables'] = total_due - total_paid

        if all_time_principal > 0 and total_due > 0:
            # محاسبه نسبتی از پول پرداخت شده که اصل پول بوده است
            principal_to_due_ratio = all_time_principal / total_due
            principal_repaid = total_paid * principal_to_due_ratio
            stats['realized_profit'] = total_paid - principal_repaid
        else:
            stats['realized_profit'] = 0
            
        stats['unrealized_profit'] = stats['total_projected_profit'] - stats['realized_profit']

        return stats
    

    # --- تابع جدید برای پنل لیست کل تراکنش‌ها ---
    def get_all_transactions_paginated(self, page: int, page_size: int) -> List[Dict[str, Any]]:
        offset = (page - 1) * page_size
        query = """
            SELECT
                t.id, t.readable_id, t.type, t.amount, t.date, t.description,
                t.source_id, t.destination_id,
                -- تعیین Parent ID بر اساس نوع تراکنش
                CASE
                    WHEN t.type IN ('installment_received', 'settlement_received', 'manual_receipt') THEN t.source_id
                    WHEN t.type IN ('loan_payment', 'manual_payment', 'expense', 'transfer', 'capital_injection') THEN t.destination_id
                    ELSE NULL
                END as parent_id,
                -- تعیین نام طرف حساب مبدا
                CASE
                    WHEN t.source_id IS NULL THEN 'سیستم'
                    WHEN t.type IN ('installment_received', 'settlement_received', 'manual_receipt') THEN (SELECT u.name FROM users u WHERE u.id = t.source_id)
                    ELSE (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.source_id)
                END as source_name,
                -- تعیین نام طرف حساب مقصد
                CASE
                    WHEN t.destination_id IS NULL THEN 'سیستم'
                    WHEN t.type IN ('loan_payment', 'manual_payment') THEN (SELECT u.name FROM users u WHERE u.id = t.destination_id)
                    ELSE (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.destination_id)
                END as destination_name
            FROM transactions t
            ORDER BY t.created_at DESC
            LIMIT %s OFFSET %s;
        """
        return self._execute_query(query, (page_size, offset), fetch='all')

    def get_transactions_count(self) -> int:
        query = "SELECT COUNT(id) as count FROM transactions"
        result = self._execute_query(query, fetch='one')
        return result['count'] if result else 0


    def get_all_customers_with_details(self) -> List[Tuple]:
        """تمام مشتریان را برای استفاده در کومبو باکس گزارش‌گیری برمی‌گرداند."""
        query = "SELECT id, name, national_code, phone_number, address, total_debt FROM users ORDER BY name ASC"
        return self._execute_query(query, fetch='all', dictionary_cursor=False)

    def get_full_customer_report_data(self, customer_id: str) -> Tuple[Optional[List], Dict]:
        """اطلاعات کامل وام‌ها، اقساط و جزئیات پرداخت را برای گزارش مشتری برمی‌گرداند."""
        loans_query = "SELECT id, readable_id, amount, loan_term, interest_rate, status FROM loans WHERE customer_id = %s"
        loans = self._execute_query(loans_query, (customer_id,), fetch='all')
        if not loans:
            return [], {}

        loan_ids = [loan['id'] for loan in loans]
        format_strings = ','.join(['%s'] * len(loan_ids))
        installments_query = f"SELECT * FROM installments WHERE loan_id IN ({format_strings}) ORDER BY readable_id ASC"
        all_installments = self._execute_query(installments_query, tuple(loan_ids), fetch='all')
        
        installments_by_loan = {loan['id']: [] for loan in loans}
        if all_installments:
            installment_ids = [inst['id'] for inst in all_installments]
            payment_format_strings = ','.join(['%s'] * len(installment_ids))
            
            # --- اضافه شد: دریافت جزئیات پرداخت ---
            payments_query = f"SELECT * FROM payment_details WHERE installment_id IN ({payment_format_strings}) ORDER BY payment_date ASC"
            all_payment_details = self._execute_query(payments_query, tuple(installment_ids), fetch='all')

            payments_by_installment = {}
            if all_payment_details:
                for payment in all_payment_details:
                    inst_id = payment['installment_id']
                    if inst_id not in payments_by_installment:
                        payments_by_installment[inst_id] = []
                    payments_by_installment[inst_id].append(payment)
            
            for inst in all_installments:
                inst['payment_details'] = payments_by_installment.get(inst['id'], [])
                installments_by_loan[inst['loan_id']].append(inst)
                
        return loans, installments_by_loan


    def get_installments_by_date_range(self, start_date: str, end_date: str, status: str) -> List[Dict[str, Any]]:
        query = """
            SELECT i.readable_id, i.due_date, i.amount_due, i.amount_paid, i.status, u.name as customer_name, l.readable_id as loan_readable_id
            FROM installments i
            JOIN loans l ON i.loan_id = l.id
            JOIN users u ON l.customer_id = u.id
            WHERE i.due_date BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        
        if status == "پرداخت شده": query += " AND i.status = 'PAID'"
        elif status == "پرداخت نشده": query += " AND i.status = 'PENDING'"
        elif status == "پرداخت ناقص": query += " AND i.status = 'PARTIALLY_PAID'"
            
        query += " ORDER BY i.due_date ASC"
        return self._execute_query(query, tuple(params), fetch='all')

    def get_transactions_by_cashbox(self, cashbox_id: str) -> List[Dict[str, Any]]:
        """کوئری اصلاح شده تا تمام فیلدهای لازم برای گزارش را شامل شود."""
        query = """
            SELECT t.date, t.type, t.amount, t.description, t.source_id, t.destination_id,
                   CASE
                       WHEN t.type IN ('installment_received', 'manual_receipt') THEN (SELECT u.name FROM users u WHERE u.id = t.source_id)
                       WHEN t.type IN ('loan_payment', 'manual_payment') THEN (SELECT u.name FROM users u WHERE u.id = t.destination_id)
                       WHEN t.type = 'transfer' AND t.source_id = %(cashbox_id)s THEN (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.destination_id)
                       WHEN t.type = 'transfer' AND t.destination_id = %(cashbox_id)s THEN (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.source_id)
                       ELSE 'سیستم'
                   END as customer_name
            FROM transactions t
            WHERE t.source_id = %(cashbox_id)s OR t.destination_id = %(cashbox_id)s
            ORDER BY t.created_at ASC
        """
        return self._execute_query(query, {'cashbox_id': cashbox_id}, fetch='all')




