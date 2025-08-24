# db_manager.py
import mysql.connector
from mysql.connector import pooling, Error
import configparser
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Iterator, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    _pool = None

    def __init__(self):
        if DatabaseManager._pool is None:
            try:
                db_config = self._get_db_config()
                DatabaseManager._pool = pooling.MySQLConnectionPool(pool_name="hesabdari_pool", pool_size=5, **db_config)
                logging.info("استخر اتصالات (Connection Pool) با موفقیت ایجاد شد.")
            except Error as err:
                logging.error(f"خطا در ایجاد استخر اتصالات: {err}")
                raise

    def _get_db_config(self) -> Dict[str, str]:
        config = configparser.ConfigParser()
        config.read('config.ini')
        return {
            'host': config['mysql']['host'],
            'user': config['mysql']['user'],
            'password': config['mysql']['password'],
            'database': config['mysql']['database']
        }

    @contextmanager
    def get_connection(self):
        if self._pool is None:
            raise ConnectionError("استخر اتصالات (Connection Pool) مقداردهی اولیه نشده است.")
        connection = self._pool.get_connection()
        try:
            yield connection
        finally:
            if connection.is_connected():
                connection.close()
    
    def _execute_query(self, query: str, params: tuple = None, fetch: Optional[str] = None, dictionary_cursor: bool = True) -> Any:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=dictionary_cursor)
                cursor.execute(query, params or ())
                
                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                    if query.strip().upper().startswith('INSERT'):
                        return cursor.lastrowid
                    return True

                if fetch == 'one':
                    return cursor.fetchone()
                if fetch == 'all':
                    return cursor.fetchall()
        except Error as err:
            logging.error(f"خطا در اجرای کوئری: {query} | خطا: {err}")
            return None if fetch else False

    def _execute_transactional_operations(self, operations: List[Dict[str, Any]]) -> Tuple[bool, str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                conn.start_transaction()
                
                results = {}
                for op in operations:
                    query = op['query']
                    params = op.get('params', ())
                    
                    final_params = []
                    for p in params:
                        if isinstance(p, str) and p in results:
                            final_params.append(results[p])
                        else:
                            final_params.append(p)
                    
                    cursor.execute(query, tuple(final_params))
                    
                    if op.get('fetch_last_id'):
                        results[op['fetch_last_id']] = cursor.lastrowid
                
                conn.commit()
                return True, "عملیات با موفقیت انجام شد."
        except Error as err:
            logging.error(f"خطا در تراکنش: {err}")
            conn.rollback()
            return False, f"خطا در عملیات پایگاه داده: {err}"

    def _execute_query_yield(self, query: str, params: tuple = None) -> Iterator[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True, buffered=False)
                cursor.execute(query, params or ())
                for row in cursor:
                    yield row
        except Error as err:
            logging.error(f"خطا در اجرای کوئری (yield): {query} | خطا: {err}")

    # --- متد اصلاح شده برای گزارش صندوق ---
    def get_transactions_by_cashbox(self, cashbox_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                t.id, t.type, t.amount, t.date, t.description,
                t.source_id, t.destination_id,
                CASE
                    WHEN t.type = 'loan_payment' THEN (SELECT c.name FROM customers c WHERE c.id = t.destination_id)
                    WHEN t.type = 'manual_payment' THEN (SELECT c.name FROM customers c WHERE c.id = t.destination_id)
                    WHEN t.type IN ('installment_received', 'settlement_received') THEN (SELECT c.name FROM customers c WHERE c.id = t.source_id)
                    WHEN t.type = 'manual_receipt' THEN (SELECT c.name FROM customers c WHERE c.id = t.source_id)
                    WHEN t.type = 'transfer' AND t.source_id = %(cashbox_id)s THEN (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.destination_id)
                    WHEN t.type = 'transfer' AND t.destination_id = %(cashbox_id)s THEN (SELECT cb.name FROM cash_boxes cb WHERE cb.id = t.source_id)
                    WHEN t.type = 'expense' THEN 'هزینه داخلی'
                    WHEN t.type = 'capital_injection' THEN 'سرمایه گذار'
                    ELSE 'سیستم'
                END as customer_name -- <<< تغییر کلیدی: بازگرداندن نام مستعار به customer_name
            FROM transactions t
            WHERE 
                t.source_id = %(cashbox_id)s OR t.destination_id = %(cashbox_id)s
            ORDER BY t.date ASC, t.id ASC
        """
        return self._execute_query(query, {'cashbox_id': cashbox_id}, fetch='all')

    # ... (بقیه متدهای کلاس بدون تغییر باقی می‌مانند)
    def get_customers_count(self, search_query: str = "") -> int:
        base_query = "SELECT COUNT(id) as count FROM customers"
        params = []
        if search_query:
            base_query += " WHERE name LIKE %s OR national_code LIKE %s OR phone_number LIKE %s"
            search_term = f"%{search_query}%"
            params = [search_term, search_term, search_term]
        
        result = self._execute_query(base_query, tuple(params), fetch='one')
        return result['count'] if result else 0

    def get_customers_paginated(self, page: int, page_size: int, search_query: str = "") -> List[Dict[str, Any]]:
        offset = (page - 1) * page_size
        base_query = """
            SELECT c.id, c.name, c.national_code, c.phone_number, c.address,
            (
                COALESCE((SELECT SUM(i.amount_due) - SUM(i.amount_paid) FROM installments i JOIN loans l ON i.loan_id = l.id WHERE l.customer_id = c.id), 0) +
                COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.destination_id = c.id AND t.type = 'manual_payment'), 0) -
                COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.source_id = c.id AND t.type = 'manual_receipt'), 0)
            ) as total_debt
            FROM customers c
        """
        params = []
        if search_query:
            base_query += " WHERE c.name LIKE %s OR c.national_code LIKE %s OR c.phone_number LIKE %s"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
            
        base_query += " GROUP BY c.id ORDER BY c.id DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        
        return self._execute_query(base_query, tuple(params), fetch='all')

    def get_single_customer_with_debt(self, customer_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT c.id, c.name, c.national_code, c.phone_number, c.address,
            (
                COALESCE((SELECT SUM(i.amount_due) - SUM(i.amount_paid) FROM installments i JOIN loans l ON i.loan_id = l.id WHERE l.customer_id = c.id), 0) +
                COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.destination_id = c.id AND t.type = 'manual_payment'), 0) -
                COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.source_id = c.id AND t.type = 'manual_receipt'), 0)
            ) as total_debt
            FROM customers c
            WHERE c.id = %s
            GROUP BY c.id
        """
        return self._execute_query(query, (customer_id,), fetch='one')

    def get_all_customers_with_debt_yield(self) -> Iterator[Dict[str, Any]]:
        query = """
            SELECT c.id, c.name, c.national_code, c.phone_number, c.address,
                   COALESCE(SUM(i.amount_due) - SUM(i.amount_paid), 0) as total_debt
            FROM customers c
            LEFT JOIN loans l ON c.id = l.customer_id
            LEFT JOIN installments i ON l.id = i.loan_id
            GROUP BY c.id ORDER BY c.id DESC
        """
        return self._execute_query_yield(query)

    def add_customer(self, name: str, national_code: str, phone_number: str, address: str) -> bool:
        query = "INSERT INTO customers (name, national_code, phone_number, address) VALUES (%s, %s, %s, %s)"
        return self._execute_query(query, (name, national_code, phone_number, address)) is not None

    def update_customer(self, customer_id: int, name: str, national_code: str, phone_number: str, address: str) -> bool:
        query = "UPDATE customers SET name = %s, national_code = %s, phone_number = %s, address = %s WHERE id = %s"
        return self._execute_query(query, (name, national_code, phone_number, address, customer_id))

    def delete_customer(self, customer_id: int) -> bool:
        query = "DELETE FROM customers WHERE id = %s"
        return self._execute_query(query, (customer_id,))
        
    def get_all_customers(self) -> List[Tuple]:
        return self._execute_query("SELECT id, name FROM customers", fetch='all', dictionary_cursor=False)

    def get_all_customers_with_details(self) -> List[Tuple]:
        query = "SELECT id, name, national_code, phone_number, address FROM customers"
        return self._execute_query(query, fetch='all', dictionary_cursor=False)

    def get_full_customer_report_data(self, customer_id: int) -> Tuple[Optional[List], Dict]:
        loans_query = """
            SELECT
                l.id, l.amount, l.loan_term, l.interest_rate, l.start_date,
                (SUM(i.amount_paid) >= SUM(i.amount_due)) as is_settled
            FROM loans l
            LEFT JOIN installments i ON l.id = i.loan_id
            WHERE l.customer_id = %s
            GROUP BY l.id
        """
        loans = self._execute_query(loans_query, (customer_id,), fetch='all')
        if not loans:
            return [], {}

        loan_ids = [loan['id'] for loan in loans]
        if not loan_ids: return loans, {}
        
        format_strings = ','.join(['%s'] * len(loan_ids))

        installments_query = f"SELECT * FROM installments WHERE loan_id IN ({format_strings}) ORDER BY id ASC"
        all_installments = self._execute_query(installments_query, tuple(loan_ids), fetch='all')
        if not all_installments:
            return loans, {}
        
        installment_ids = [inst['id'] for inst in all_installments]
        if not installment_ids:
            for inst in all_installments:
                inst['payment_details'] = []
            installments_by_loan = {loan_id: [i for i in all_installments if i['loan_id'] == loan_id] for loan_id in loan_ids}
            return loans, installments_by_loan

        payment_format_strings = ','.join(['%s'] * len(installment_ids))
        payments_query = f"SELECT * FROM payment_details WHERE installment_id IN ({payment_format_strings}) ORDER BY payment_date ASC"
        all_payment_details = self._execute_query(payments_query, tuple(installment_ids), fetch='all')

        payments_by_installment = {}
        if all_payment_details:
            for payment in all_payment_details:
                inst_id = payment['installment_id']
                if inst_id not in payments_by_installment:
                    payments_by_installment[inst_id] = []
                payments_by_installment[inst_id].append(payment)

        installments_by_loan = {}
        for inst in all_installments:
            inst['payment_details'] = payments_by_installment.get(inst['id'], [])
            loan_id = inst['loan_id']
            if loan_id not in installments_by_loan:
                installments_by_loan[loan_id] = []
            installments_by_loan[loan_id].append(inst)
            
        return loans, installments_by_loan

    def create_loan_and_installments(self, loan_data: Dict, installments_data: List[Dict]) -> Tuple[bool, str]:
        operations = [
            {
                'query': "INSERT INTO loans (customer_id, cash_box_id, amount, loan_term, interest_rate, start_date) VALUES (%s, %s, %s, %s, %s, %s)",
                'params': (loan_data['customer_id'], loan_data['cash_box_id'], loan_data['amount'], loan_data['loan_term'], loan_data['interest_rate'], loan_data['start_date']),
                'fetch_last_id': 'loan_id'
            },
            {
                'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s",
                'params': (loan_data['amount'], loan_data['cash_box_id'])
            },
            {
                'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)",
                'params': ('loan_payment', loan_data['amount'], loan_data['transaction_date'], loan_data['cash_box_id'], loan_data['customer_id'], loan_data['description'])
            }
        ]
        for inst in installments_data:
            operations.append({
                'query': "INSERT INTO installments (loan_id, due_date, amount_due) VALUES (%s, %s, %s)",
                'params': ('loan_id', inst['due_date'], inst['amount_due'])
            })
        
        return self._execute_transactional_operations(operations)

    def get_customer_loans(self, customer_id: int) -> list:
        query = "SELECT id, amount, loan_term, start_date FROM loans WHERE customer_id = %s"
        return self._execute_query(query, (customer_id,), fetch='all', dictionary_cursor=False)
    
    def get_loan_installments(self, loan_id: int) -> list:
        query = "SELECT id, due_date, amount_due, amount_paid, payment_date FROM installments WHERE loan_id = %s ORDER BY id ASC"
        return self._execute_query(query, (loan_id,), fetch='all', dictionary_cursor=False)

    def get_installment_details(self, installment_id: int) -> Optional[Tuple]:
        query = "SELECT id, due_date, amount_due, amount_paid FROM installments WHERE id = %s"
        return self._execute_query(query, (installment_id,), fetch='one', dictionary_cursor=False)
    
    def is_loan_fully_paid(self, loan_id: int) -> bool:
        query = """
            SELECT 
                (SELECT SUM(amount_due) FROM installments WHERE loan_id = %s) AS total_due,
                (SELECT SUM(amount_paid) FROM installments WHERE loan_id = %s) AS total_paid
        """
        result = self._execute_query(query, (loan_id, loan_id), fetch='one')
        if result and result.get('total_due') is not None:
            return (result.get('total_paid') or 0) >= result.get('total_due')
        return False

    def pay_installment(self, customer_id: int, installment_id: int, amount_paid: float, cash_box_id: int, description: str, payment_date: str) -> bool:
        operations = [
            {
                'query': "INSERT INTO payment_details (installment_id, amount, payment_date, cashbox_id, description) VALUES (%s, %s, %s, %s, %s)",
                'params': (installment_id, amount_paid, payment_date, cash_box_id, description)
            },
            {
                'query': "UPDATE installments SET amount_paid = amount_paid + %s, is_paid = (amount_paid >= amount_due), payment_date = IF(payment_date IS NULL, %s, payment_date) WHERE id = %s",
                'params': (amount_paid, payment_date, installment_id)
            },
            {
                'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s",
                'params': (amount_paid, cash_box_id)
            },
            {
                'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)",
                'params': ('installment_received', amount_paid, payment_date, customer_id, cash_box_id, description)
            }
        ]
        success, _ = self._execute_transactional_operations(operations)
        return success

    def get_loan_for_settlement(self, loan_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT amount, interest_rate, start_date, (SELECT SUM(amount_paid) FROM installments WHERE loan_id = l.id) as total_paid FROM loans l WHERE id = %s"
        return self._execute_query(query, (loan_id,), fetch='one')

    def settle_loan(self, loan_id: int, settlement_amount: float, cashbox_id: int, new_total_loan_value: float, customer_id: int, description: str, date: str) -> bool:
        original_total_due_query = "SELECT SUM(amount_due) as total_due FROM installments WHERE loan_id = %s"
        original_total_due_result = self._execute_query(original_total_due_query, (loan_id,))
        original_total_due = original_total_due_result['total_due'] or 0
        forgiven_interest = original_total_due - new_total_loan_value

        operations = []
        if forgiven_interest > 0:
            last_installment_id_query = "SELECT id FROM installments WHERE loan_id = %s ORDER BY id DESC LIMIT 1"
            last_installment = self._execute_query(last_installment_id_query, (loan_id,))
            if last_installment:
                operations.append({
                    'query': "UPDATE installments SET amount_due = amount_due - %s WHERE id = %s",
                    'params': (forgiven_interest, last_installment['id'])
                })

        operations.extend([
            {
                'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s",
                'params': (settlement_amount, cashbox_id)
            },
            {
                'query': "UPDATE installments SET amount_paid = amount_due, is_paid = TRUE WHERE loan_id = %s AND is_paid = FALSE",
                'params': (loan_id,)
            },
            {
                'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)",
                'params': ('settlement_received', settlement_amount, date, customer_id, cashbox_id, description)
            }
        ])
        
        success, _ = self._execute_transactional_operations(operations)
        return success

    def get_installments_by_date_range(self, start_date: str, end_date: str, status: str) -> List[Dict[str, Any]]:
        query = """
            SELECT i.due_date, i.amount_due, i.amount_paid, c.name as customer_name, l.id as loan_id
            FROM installments i
            JOIN loans l ON i.loan_id = l.id
            JOIN customers c ON l.customer_id = c.id
            WHERE i.due_date BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        
        if status == "پرداخت شده":
            query += " AND i.is_paid = TRUE"
        elif status == "پرداخت نشده":
            query += " AND i.amount_paid = 0"
        elif status == "پرداخت ناقص":
            query += " AND i.amount_paid > 0 AND i.is_paid = FALSE"
            
        query += " ORDER BY i.due_date ASC"
        
        return self._execute_query(query, tuple(params), fetch='all')

    def get_all_cash_boxes(self) -> List[Tuple]:
        return self._execute_query("SELECT id, name, balance FROM cash_boxes", fetch='all', dictionary_cursor=False)

    def add_cash_box(self, name: str, initial_balance: float = 0) -> bool:
        query = "INSERT INTO cash_boxes (name, balance) VALUES (%s, %s)"
        return self._execute_query(query, (name, initial_balance)) is not None

    def update_cash_box(self, box_id: int, name: str, balance: float) -> bool:
        query = "UPDATE cash_boxes SET name = %s, balance = %s WHERE id = %s"
        return self._execute_query(query, (name, balance, box_id))

    def delete_cash_box(self, box_id: int) -> bool:
        query = "DELETE FROM cash_boxes WHERE id = %s"
        return self._execute_query(query, (box_id,))

    def get_cash_box_balance(self, box_id: int) -> float:
        query = "SELECT balance FROM cash_boxes WHERE id = %s"
        result = self._execute_query(query, (box_id,), fetch='one')
        return result['balance'] if result else 0

    def get_cash_box_name(self, box_id: int) -> str:
        query = "SELECT name FROM cash_boxes WHERE id = %s"
        result = self._execute_query(query, (box_id,), fetch='one')
        return result['name'] if result else "N/A"

    def add_expense_category(self, name: str) -> bool:
        query = "INSERT INTO expense_categories (name) VALUES (%s)"
        return self._execute_query(query, (name,)) is not None

    def get_all_expense_categories(self) -> List[Dict[str, Any]]:
        query = "SELECT id, name FROM expense_categories ORDER BY name ASC"
        return self._execute_query(query, fetch='all')

    def add_expense(self, category_id: int, cashbox_id: int, amount: float, description: str, expense_date: str) -> bool:
        operations = [
            {
                'query': "INSERT INTO expenses (category_id, cashbox_id, amount, description, expense_date) VALUES (%s, %s, %s, %s, %s)",
                'params': (category_id, cashbox_id, amount, description, expense_date)
            },
            {
                'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s",
                'params': (amount, cashbox_id)
            },
            {
                'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)",
                'params': ('expense', amount, expense_date, cashbox_id, None, f"ثبت هزینه: {description}")
            }
        ]
        success, _ = self._execute_transactional_operations(operations)
        return success

    def get_all_expenses(self) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                e.expense_date,
                ec.name as category_name,
                cb.name as cashbox_name,
                e.amount,
                e.description
            FROM expenses e
            JOIN expense_categories ec ON e.category_id = ec.id
            JOIN cash_boxes cb ON e.cashbox_id = cb.id
            ORDER BY e.expense_date DESC, e.id DESC
        """
        return self._execute_query(query, fetch='all')

    def add_manual_transaction(self, trans_type: str, amount: int, date: str, source_id: Optional[int], destination_id: int, description: str) -> Tuple[bool, str]:
        operations = []
        if trans_type == "transfer":
            operations = [
                {'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s", 'params': (amount, source_id)},
                {'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s", 'params': (amount, destination_id)},
                {'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)", 'params': (trans_type, amount, date, source_id, destination_id, description)}
            ]
        elif trans_type == "manual_payment":
            operations = [
                {'query': "UPDATE cash_boxes SET balance = balance - %s WHERE id = %s", 'params': (amount, source_id)},
                {'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)", 'params': (trans_type, amount, date, source_id, destination_id, description)}
            ]
        elif trans_type == "manual_receipt":
            operations = [
                {'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s", 'params': (amount, destination_id)},
                {'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)", 'params': (trans_type, amount, date, source_id, destination_id, description)}
            ]
        elif trans_type == "capital_injection":
            operations = [
                {'query': "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s", 'params': (amount, destination_id)},
                {'query': "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)", 'params': (trans_type, amount, date, source_id, destination_id, description)}
            ]
        
        if not operations:
            return False, "نوع تراکنش نامعتبر است."
            
        return self._execute_transactional_operations(operations)

    def record_transaction(self, type, amount, date, source_id, destination_id, description):
        query = "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)"
        return self._execute_query(query, (type, amount, date, source_id, destination_id, description)) is not None

    def get_transactions_count(self) -> int:
        query = "SELECT COUNT(id) as count FROM transactions"
        result = self._execute_query(query, fetch='one')
        return result['count'] if result else 0

    def get_transactions_paginated(self, page: int, page_size: int) -> List[Tuple]:
        offset = (page - 1) * page_size
        query = "SELECT id, type, amount, date, source_id, destination_id, description FROM transactions ORDER BY id DESC LIMIT %s OFFSET %s"
        return self._execute_query(query, (page_size, offset), fetch='all', dictionary_cursor=False)

    def get_transactions_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                t.date, t.type, t.amount, t.description
            FROM transactions t
            WHERE 
                (t.type = 'loan_payment' AND t.destination_id = %s) OR
                (t.type IN ('installment_received', 'settlement_received') AND t.source_id = %s) OR
                (t.type = 'manual_payment' AND t.destination_id = %s) OR
                (t.type = 'manual_receipt' AND t.source_id = %s)
            ORDER BY t.date DESC, t.id DESC
        """
        return self._execute_query(query, (customer_id, customer_id, customer_id, customer_id), fetch='all')

    def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        query = """
            SELECT
                (SELECT COALESCE(SUM(balance), 0) FROM cash_boxes) as total_balance,
                (SELECT COALESCE(SUM(amount), 0) FROM loans) as total_loan_principal,
                (SELECT COALESCE(COUNT(id), 0) FROM customers) as total_customers,
                (SELECT COALESCE(SUM(amount_due), 0) FROM installments) as total_due,
                (SELECT COALESCE(SUM(amount_paid), 0) FROM installments) as total_paid,
                (SELECT COALESCE(SUM(amount), 0) FROM expenses) as total_expenses
        """
        base_stats = self._execute_query(query, fetch='one')
        if not base_stats: return None

        stats = dict(base_stats)
        
        total_due = stats.get('total_due', 0) or 0
        total_paid = stats.get('total_paid', 0) or 0
        total_loan_principal = stats.get('total_loan_principal', 0) or 0

        stats['total_receivables'] = total_due - total_paid
        stats['total_projected_profit'] = total_due - total_loan_principal
        
        if total_loan_principal > 0 and total_due > 0:
            principal_repaid_ratio = total_loan_principal / total_due
            principal_repaid = total_paid * principal_repaid_ratio
            stats['realized_profit'] = total_paid - principal_repaid
        else:
            stats['realized_profit'] = 0
            
        stats['unrealized_profit'] = stats['total_projected_profit'] - stats['realized_profit']

        loans_query = """
            SELECT l.id, SUM(i.amount_due) as due, SUM(i.amount_paid) as paid
            FROM loans l LEFT JOIN installments i ON l.id = i.loan_id
            GROUP BY l.id
        """
        loans = self._execute_query(loans_query, fetch='all')
        if loans:
            stats['active_loans'] = sum(1 for loan in loans if (loan.get('paid', 0) or 0) < (loan.get('due', 0) or 0))
            stats['settled_loans'] = sum(1 for loan in loans if (loan.get('paid', 0) or 0) >= (loan.get('due', 0) or 0))
        else:
            stats['active_loans'] = 0
            stats['settled_loans'] = 0

        return stats
