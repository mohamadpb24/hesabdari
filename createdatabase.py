import mysql.connector
from mysql.connector import Error
import configparser

# A. خواندن تنظیمات دیتابیس از فایل config.ini
def get_db_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return {
        'host': config['mysql']['host'],
        'user': config['mysql']['user'],
        'password': config['mysql']['password'],
        'database': config['mysql']['database']
    }

# B. تعریف تابع برای ایجاد اتصال به سرور MySQL
def create_server_connection(host_name, user_name, user_password):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password
        )
        print("اتصال به سرور MySQL با موفقیت برقرار شد.")
    except Error as err:
        print(f"خطا در اتصال به سرور: '{err}'")
    return connection

# C. تعریف تابع برای اجرای دستورات SQL
def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("دستور SQL با موفقیت اجرا شد.")
    except Error as err:
        print(f"خطا در اجرای دستور: '{err}'")

# D. تعریف تابع اصلی برای ساخت دیتابیس و جداول
def create_database_and_tables():
    db_config = get_db_config()
    db_name = db_config['database']

    # 1. اتصال به سرور MySQL
    connection = create_server_connection(db_config['host'], db_config['user'], db_config['password'])
    if not connection:
        return
    
    # --- تغییر اصلی: حذف دیتابیس قبلی ---
    # این دستور اگر دیتابیس با همین نام وجود داشته باشد، آن را حذف می‌کند
    drop_db_query = f"DROP DATABASE IF EXISTS {db_name}"
    execute_query(connection, drop_db_query)
    
    # 2. ایجاد دیتابیس
    create_db_query = f"CREATE DATABASE IF NOT EXISTS {db_name}"
    execute_query(connection, create_db_query)
    
    # 3. بستن اتصال و ایجاد اتصال جدید با دیتابیس
    connection.close()
    
    # اتصال جدید برای کار روی دیتابیس تازه ساخته شده
    try:
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            passwd=db_config['password'],
            database=db_name
        )
        print(f"اتصال به دیتابیس '{db_name}' با موفقیت برقرار شد.")
    except Error as err:
        print(f"خطا در اتصال به دیتابیس: '{err}'")
        return

    # 4. تعریف کوئری‌های SQL برای ساخت جداول
    create_tables_queries = [
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            national_code VARCHAR(10) UNIQUE,
            phone_number VARCHAR(15),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS cash_boxes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            balance DECIMAL(15, 0) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS loans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT NOT NULL,
            cash_box_id INT NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            loan_term INT NOT NULL,
            interest_rate DECIMAL(5, 2) NOT NULL,
            start_date VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (cash_box_id) REFERENCES cash_boxes(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS installments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            loan_id INT NOT NULL,
            due_date VARCHAR(10) NOT NULL,
            amount_due DECIMAL(15, 0) NOT NULL,
            amount_paid DECIMAL(15, 0) DEFAULT 0,
            is_paid BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            date VARCHAR(10) NOT NULL,
            source_id INT,
            destination_id INT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]

    # 5. اجرای کوئری‌های ساخت جداول
    if connection:
        for query in create_tables_queries:
            execute_query(connection, query)
        connection.close()
        print("تمامی جداول با موفقیت ایجاد شدند.")

if __name__ == "__main__":
    create_database_and_tables()
