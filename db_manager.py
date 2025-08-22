import mysql.connector
from mysql.connector import Error
import configparser

class DatabaseManager:
    def __init__(self):
        self.db_config = self.get_db_config()
        
    def get_db_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        return {
            'host': config['mysql']['host'],
            'user': config['mysql']['user'],
            'password': config['mysql']['password'],
            'database': config['mysql']['database']
        }

    def create_connection(self):
        connection = None
        try:
            connection = mysql.connector.connect(**self.db_config)
        except Error as err:
            print(f"خطا در اتصال به دیتابیس: '{err}'")
        return connection

    # *** تابع settle_loan با منطق جدید و اصلاح شده برای سود بخشیده شده ***
    def settle_loan(self, loan_id, settlement_amount, cashbox_id, new_total_loan_value):
        conn = self.create_connection()
        if conn is None: return False
        
        cursor = conn.cursor(dictionary=True)
        try:
            conn.autocommit = False
            
            # 1. دریافت مجموع بدهی اولیه
            cursor.execute("SELECT SUM(amount_due) as total_due FROM installments WHERE loan_id = %s", (loan_id,))
            original_total_due = cursor.fetchone()['total_due'] or 0

            # 2. محاسبه سود بخشیده شده
            forgiven_interest = original_total_due - new_total_loan_value

            # 3. اصلاح مبلغ بدهی آخرین قسط برای کسر سود بخشیده شده
            if forgiven_interest > 0:
                # پیدا کردن آخرین قسط
                cursor.execute("SELECT id FROM installments WHERE loan_id = %s ORDER BY id DESC LIMIT 1", (loan_id,))
                last_installment = cursor.fetchone()
                if last_installment:
                    last_installment_id = last_installment['id']
                    update_due_query = "UPDATE installments SET amount_due = amount_due - %s WHERE id = %s"
                    cursor.execute(update_due_query, (forgiven_interest, last_installment_id))

            # 4. به‌روزرسانی موجودی صندوق
            update_cashbox_query = "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s"
            cursor.execute(update_cashbox_query, (settlement_amount, cashbox_id))
            
            # 5. به‌روزرسانی تمام اقساط باز به عنوان "پرداخت شده"
            update_installments_query = """
                UPDATE installments SET amount_paid = amount_due, is_paid = TRUE 
                WHERE loan_id = %s AND amount_paid < amount_due
            """
            cursor.execute(update_installments_query, (loan_id,))
            
            conn.commit()
            return True
        except Error as err:
            conn.rollback()
            print(f"خطا در تسویه وام: '{err}'")
            return False
        finally:
            conn.autocommit = True
            if conn.is_connected():
                cursor.close()
                conn.close()

    # ... (بقیه توابع کلاس بدون تغییر باقی می‌مانند) ...
    def get_customers_with_debt(self):
        conn = self.create_connection()
        if conn is None: return []
        
        query = """
            SELECT 
                c.id, c.name, c.national_code, c.phone_number, c.address,
                COALESCE(SUM(i.amount_due) - SUM(i.amount_paid), 0) as total_debt
            FROM customers c
            LEFT JOIN loans l ON c.id = l.customer_id
            LEFT JOIN installments i ON l.id = i.loan_id
            GROUP BY c.id, c.name, c.national_code, c.phone_number, c.address
            ORDER BY c.id DESC
        """
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query)
            customers = cursor.fetchall()
            return customers
        except Error as err:
            print(f"خطا در خواندن مشتریان با بدهی: '{err}'")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_transactions_by_customer(self, customer_id):
        conn = self.create_connection()
        if conn is None: return []
        
        query = """
            SELECT 
                t.date, t.type, t.amount, t.description,
                t.source_id, t.destination_id
            FROM transactions t
            WHERE 
                (t.type = 'loan_payment' AND t.destination_id = %(customer_id)s) OR
                (t.type IN ('installment_received', 'settlement_received') AND t.source_id = %(customer_id)s)
            ORDER BY t.date DESC, t.id DESC
        """
        values = {'customer_id': customer_id}
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, values)
            transactions = cursor.fetchall()
            return transactions
        except Error as err:
            print(f"خطا در خواندن تراکنش‌های مشتری: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_customer_loans_for_report(self, customer_id):
        conn = self.create_connection()
        if conn is None: return []
        query = """
            SELECT
                l.id, l.amount, l.loan_term, l.interest_rate, l.start_date,
                (SUM(i.amount_paid) >= SUM(i.amount_due)) as is_settled
            FROM loans l
            LEFT JOIN installments i ON l.id = i.loan_id
            WHERE l.customer_id = %(customer_id)s
            GROUP BY l.id
        """
        values = {'customer_id': customer_id}
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, values)
            return cursor.fetchall()
        except Error as err:
            print(f"خطا در خواندن وام‌های مشتری برای گزارش: '{err}'")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_dashboard_stats(self):
        conn = self.create_connection()
        if conn is None: return None
        
        stats = {}
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    (SELECT COALESCE(SUM(balance), 0) FROM cash_boxes) as total_balance,
                    (SELECT COALESCE(SUM(amount), 0) FROM loans) as total_loan_principal,
                    (SELECT COALESCE(COUNT(id), 0) FROM customers) as total_customers,
                    (SELECT COALESCE(SUM(amount_due), 0) FROM installments) as total_due,
                    (SELECT COALESCE(SUM(amount_paid), 0) FROM installments) as total_paid
            """
            cursor.execute(query)
            base_stats = cursor.fetchone()

            stats['total_balance'] = base_stats['total_balance']
            stats['total_loan_principal'] = base_stats['total_loan_principal']
            stats['total_customers'] = base_stats['total_customers']
            total_due = base_stats['total_due']
            total_paid = base_stats['total_paid']
            
            stats['total_receivables'] = total_due - total_paid

            total_projected_profit = total_due - stats['total_loan_principal']
            stats['total_projected_profit'] = total_projected_profit if total_projected_profit > 0 else 0

            if stats['total_loan_principal'] > 0:
                principal_repaid_ratio = stats['total_loan_principal'] / total_due if total_due > 0 else 0
                principal_repaid = total_paid * principal_repaid_ratio
                realized_profit = total_paid - principal_repaid
            else:
                realized_profit = 0
            stats['realized_profit'] = realized_profit if realized_profit > 0 else 0

            stats['unrealized_profit'] = stats['total_projected_profit'] - stats['realized_profit']

            cursor.execute("""
                SELECT l.id, SUM(i.amount_due) as due, SUM(i.amount_paid) as paid
                FROM loans l LEFT JOIN installments i ON l.id = i.loan_id
                GROUP BY l.id
            """)
            loans = cursor.fetchall()
            stats['active_loans'] = sum(1 for loan in loans if (loan['paid'] or 0) < (loan['due'] or 0))
            stats['settled_loans'] = sum(1 for loan in loans if (loan['paid'] or 0) >= (loan['due'] or 0))

            return stats
        except Error as err:
            print(f"خطا در محاسبه آمار داشبورد: '{err}'")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_transactions_by_cashbox(self, cashbox_id):
        conn = self.create_connection()
        if conn is None: return []
        
        query = """
            SELECT 
                t.id, t.type, t.amount, t.date, t.description,
                t.source_id, t.destination_id,
                CASE
                    WHEN t.type = 'loan_payment' THEN (SELECT c.name FROM customers c WHERE c.id = t.destination_id)
                    WHEN t.type IN ('installment_received', 'settlement_received') THEN (SELECT c.name FROM customers c WHERE c.id = t.source_id)
                    ELSE 'سیستم'
                END as customer_name
            FROM transactions t
            WHERE 
                (t.type = 'loan_payment' AND t.source_id = %(cashbox_id)s) OR
                (t.type IN ('installment_received', 'settlement_received') AND t.destination_id = %(cashbox_id)s)
            ORDER BY t.date DESC, t.id DESC
        """
        values = {'cashbox_id': cashbox_id}
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, values)
            transactions = cursor.fetchall()
            return transactions
        except Error as err:
            print(f"خطا در خواندن تراکنش‌ها: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def add_customer(self, name, national_code, phone_number, address):
        conn = self.create_connection()
        if conn is None: return False
        query = "INSERT INTO customers (name, national_code, phone_number, address) VALUES (%s, %s, %s, %s)"
        values = (name, national_code, phone_number, address)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در اضافه کردن مشتری: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_all_customers(self):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT id, name FROM customers" 
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            customers = cursor.fetchall()
            return customers
        except Error as err:
            print(f"خطا در خواندن مشتریان: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_customer_name(self, customer_id):
        conn = self.create_connection()
        if conn is None: return "ناشناس"
        query = "SELECT name FROM customers WHERE id = %s"
        values = (customer_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            result = cursor.fetchone()
            return result[0] if result else "ناشناس"
        except Error as err:
            print(f"خطا در خواندن نام مشتری: '{err}'"); return "ناشناس"
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def update_customer(self, customer_id, name, national_code, phone_number, address):
        conn = self.create_connection()
        if conn is None: return False
        query = "UPDATE customers SET name = %s, national_code = %s, phone_number = %s, address = %s WHERE id = %s"
        values = (name, national_code, phone_number, address, customer_id)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در ویرایش مشتری: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def delete_customer(self, customer_id):
        conn = self.create_connection()
        if conn is None: return False
        query = "DELETE FROM customers WHERE id = %s"
        values = (customer_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در حذف مشتری: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def search_customers(self, query_str):
        conn = self.create_connection()
        if conn is None: return []
        query = """
            SELECT 
                c.id, c.name, c.national_code, c.phone_number, c.address,
                COALESCE(SUM(i.amount_due) - SUM(i.amount_paid), 0) as total_debt
            FROM customers c
            LEFT JOIN loans l ON c.id = l.customer_id
            LEFT JOIN installments i ON l.id = i.loan_id
            WHERE c.name LIKE %s OR c.national_code LIKE %s OR c.phone_number LIKE %s
            GROUP BY c.id, c.name, c.national_code, c.phone_number, c.address
        """
        search_term = f"%{query_str}%"
        values = (search_term, search_term, search_term)
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, values)
            customers = cursor.fetchall()
            return customers
        except Error as err:
            print(f"خطا در جستجوی مشتریان: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def add_cash_box(self, name, initial_balance=0):
        conn = self.create_connection()
        if conn is None: return False
        query = "INSERT INTO cash_boxes (name, balance) VALUES (%s, %s)"
        values = (name, initial_balance)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در اضافه کردن صندوق: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
            
    def get_all_cash_boxes(self):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT id, name, balance FROM cash_boxes"
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            cash_boxes = cursor.fetchall()
            return cash_boxes
        except Error as err:
            print(f"خطا در خواندن صندوق‌ها: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
            
    def get_cash_box_balance(self, box_id):
        conn = self.create_connection()
        if conn is None: return 0
        query = "SELECT balance FROM cash_boxes WHERE id = %s"
        values = (box_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Error as err:
            print(f"خطا در خواندن موجودی صندوق: '{err}'");
            return 0
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def update_cash_box(self, box_id, name, balance):
        conn = self.create_connection()
        if conn is None: return False
        query = "UPDATE cash_boxes SET name = %s, balance = %s WHERE id = %s"
        values = (name, balance, box_id)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در ویرایش صندوق: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def delete_cash_box(self, box_id):
        conn = self.create_connection()
        if conn is None: return False
        query = "DELETE FROM cash_boxes WHERE id = %s"
        values = (box_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در حذف صندوق: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def add_loan(self, customer_id, cash_box_id, amount, loan_term, interest_rate, start_date):
        conn = self.create_connection()
        if conn is None: return None
        query = "INSERT INTO loans (customer_id, cash_box_id, amount, loan_term, interest_rate, start_date) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (customer_id, cash_box_id, amount, loan_term, interest_rate, start_date)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            loan_id = cursor.lastrowid
            return loan_id
        except Error as err:
            print(f"خطا در اضافه کردن وام: '{err}'"); return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
            
    def add_installment(self, loan_id, due_date, amount_due):
        conn = self.create_connection()
        if conn is None: return False
        query = "INSERT INTO installments (loan_id, due_date, amount_due, is_paid) VALUES (%s, %s, %s, FALSE)"
        values = (loan_id, due_date, amount_due)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در اضافه کردن قسط: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def update_cash_box_balance(self, box_id, amount):
        conn = self.create_connection()
        if conn is None: return False
        query = "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s"
        values = (amount, box_id)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در به‌روزرسانی موجودی صندوق: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def record_transaction(self, type, amount, date, source_id, destination_id, description):
        conn = self.create_connection()
        if conn is None: return False
        query = "INSERT INTO transactions (type, amount, date, source_id, destination_id, description) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (type, amount, date, source_id, destination_id, description)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در ثبت تراکنش: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_cash_box_name(self, box_id):
        conn = self.create_connection()
        if conn is None: return "ناشناس"
        query = "SELECT name FROM cash_boxes WHERE id = %s"
        values = (box_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            result = cursor.fetchone()
            return result[0] if result else "ناشناس"
        except Error as err:
            print(f"خطا در خواندن نام صندوق: '{err}'"); return "ناشناس"
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_all_transactions(self):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT * FROM transactions"
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            transactions = cursor.fetchall()
            return transactions
        except Error as err:
            print(f"خطا در خواندن تراکنش‌ها: '{err}'"); return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_customer_loans(self, customer_id):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT id, amount, loan_term, start_date FROM loans WHERE customer_id = %s"
        values = (customer_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            loans = cursor.fetchall()
            return loans
        except Error as err:
            print(f"خطا در خواندن وام‌های مشتری: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_loan_installments(self, loan_id):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT id, due_date, amount_due, amount_paid FROM installments WHERE loan_id = %s"
        values = (loan_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            installments = cursor.fetchall()
            return installments
        except Error as err:
            print(f"خطا در خواندن اقساط وام: '{err}'"); return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_loan_details_by_id(self, loan_id):
        conn = self.create_connection()
        if conn is None: return None
        query = "SELECT customer_id, amount, loan_term, interest_rate FROM loans WHERE id = %s"
        values = (loan_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            loan_details = cursor.fetchone()
            return loan_details
        except Error as err:
            print(f"خطا در خواندن جزئیات وام: '{err}'"); return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
            
    def pay_installment(self, installment_id, amount_paid, cash_box_id):
        conn = self.create_connection()
        if conn is None: return False
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT amount_due FROM installments WHERE id = %s", (installment_id,))
        installment = cursor.fetchone()
        if not installment: return False
        
        query_update_installment = """
            UPDATE installments 
            SET amount_paid = amount_paid + %s, 
                is_paid = (amount_paid + %s >= amount_due)
            WHERE id = %s
        """
        values_update_installment = (amount_paid, amount_paid, installment_id)
        
        query_update_cashbox = "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s"
        values_update_cashbox = (amount_paid, cash_box_id)
        
        try:
            conn.autocommit = False
            cursor.execute(query_update_installment, values_update_installment)
            cursor.execute(query_update_cashbox, values_update_cashbox)
            conn.commit()
            return True
        except Error as err:
            conn.rollback()
            print(f"خطا در پرداخت قسط: '{err}'"); return False
        finally:
            conn.autocommit = True
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_installment_details(self, installment_id):
        conn = self.create_connection()
        if conn is None: return None
        query = "SELECT id, due_date, amount_due, amount_paid FROM installments WHERE id = %s"
        values = (installment_id,)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            installment_details = cursor.fetchone()
            return installment_details
        except Error as err:
            print(f"خطا در خواندن جزئیات قسط: '{err}'"); return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_loan_for_settlement(self, loan_id):
        conn = self.create_connection()
        if conn is None: return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            loan_query = "SELECT amount, interest_rate, start_date FROM loans WHERE id = %s"
            cursor.execute(loan_query, (loan_id,))
            loan_details = cursor.fetchone()

            if not loan_details:
                return None

            paid_query = "SELECT SUM(amount_paid) FROM installments WHERE loan_id = %s"
            cursor.execute(paid_query, (loan_id,))
            total_paid = cursor.fetchone()['SUM(amount_paid)'] or 0
            
            loan_details['total_paid'] = total_paid
            return loan_details

        except Error as err:
            print(f"خطا در دریافت اطلاعات تسویه: '{err}'")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def is_loan_fully_paid(self, loan_id):
        conn = self.create_connection()
        if conn is None: return False
        
        query = """
            SELECT 
                (SELECT SUM(amount_due) FROM installments WHERE loan_id = %s) AS total_due,
                (SELECT SUM(amount_paid) FROM installments WHERE loan_id = %s) AS total_paid
        """
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, (loan_id, loan_id))
            result = cursor.fetchone()
            if result and result['total_due'] is not None:
                return result['total_paid'] >= result['total_due']
            return False
        except Error as err:
            print(f"خطا در بررسی وضعیت وام: '{err}'")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_all_customers_with_details(self):
        conn = self.create_connection()
        if conn is None:
            return []
        query = "SELECT id, name, national_code, phone_number, address FROM customers"
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            customers = cursor.fetchall()
            return customers
        except Error as err:
            print(f"خطا در خواندن مشتریان: '{err}'");
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()