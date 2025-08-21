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
            print("اتصال به دیتابیس با موفقیت برقرار شد.")
        except Error as err:
            print(f"خطا در اتصال به دیتابیس: '{err}'")
        return connection
    
    # --- توابع مربوط به مشتریان ---
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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()
    
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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()
    
    def search_customers(self, query_str):
        conn = self.create_connection()
        if conn is None: return []
        query = "SELECT id, name, national_code, phone_number, address FROM customers WHERE name LIKE %s OR national_code LIKE %s OR phone_number LIKE %s"
        search_term = f"%{query_str}%"
        values = (search_term, search_term, search_term)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            customers = cursor.fetchall()
            return customers
        except Error as err:
            print(f"خطا در جستجوی مشتریان: '{err}'"); return []
        finally:
            cursor.close(); conn.close()
    
    # --- توابع مربوط به صندوق‌ها ---
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
            cursor.close(); conn.close()
            
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
            cursor.close(); conn.close()
            
    def get_cash_box_balance(self, box_id):
        conn = self.create_connection()
        if conn is None:
            return 0
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
            cursor.close();
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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()
            
    # --- توابع جدید برای وام و اقساط ---
    def add_loan(self, customer_id, cash_box_id, amount, loan_term, interest_rate, start_date):
        conn = self.create_connection()
        if conn is None: return None
        query = "INSERT INTO loans (customer_id, cash_box_id, amount, loan_term, interest_rate, start_date) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (customer_id, cash_box_id, amount, loan_term, interest_rate, start_date)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
        except Error as err:
            print(f"خطا در اضافه کردن وام: '{err}'"); return None
        finally:
            cursor.close(); conn.close()
            
    def add_installment(self, loan_id, due_date, amount_due):
        conn = self.create_connection()
        if conn is None: return False
        query = "INSERT INTO installments (loan_id, due_date, amount_due) VALUES (%s, %s, %s)"
        values = (loan_id, due_date, amount_due)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except Error as err:
            print(f"خطا در اضافه کردن قسط: '{err}'"); return False
        finally:
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()

    def get_transactions_by_cashbox(self, cashbox_id):
        conn = self.create_connection()
        if conn is None: return []
        # اصلاح کوئری برای فیلتر کردن تراکنش‌ها بر اساس صندوق
        query = """
        SELECT id, type, amount, date, source_id, destination_id, description
        FROM transactions
        WHERE source_id = %s OR destination_id = %s
        """
        values = (cashbox_id, cashbox_id)
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            transactions = cursor.fetchall()
            return transactions
        except Error as err:
            print(f"خطا در خواندن تراکنش‌ها: '{err}'"); return []
        finally:
            cursor.close(); conn.close()

            
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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()


    def get_cash_box_name_by_id(self, box_id):
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
            cursor.close(); conn.close()
            
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
            cursor.close(); conn.close()
            
    def pay_installment(self, installment_id, amount_paid, cash_box_id):
        conn = self.create_connection()
        if conn is None: return False
        
        query_update_installment = "UPDATE installments SET amount_paid = amount_paid + %s WHERE id = %s"
        values_update_installment = (amount_paid, installment_id)
        
        query_update_cashbox = "UPDATE cash_boxes SET balance = balance + %s WHERE id = %s"
        values_update_cashbox = (amount_paid, cash_box_id)
        
        cursor = conn.cursor()
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
            cursor.close(); conn.close()

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
            cursor.close(); conn.close()


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
            cursor.close();
            conn.close()
