# createdatabase.py (نسخه نهایی با رفع کامل باگ multi=True)

import mysql.connector
from mysql.connector import Error
import configparser

def get_db_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return {
        'host': config['mysql']['host'],
        'user': config['mysql']['user'],
        'password': config['mysql']['password'],
        'database': config['mysql']['database']
    }

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

# --- تابع execute_query به طور کامل بازنویسی شد ---
def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        # دستورات SQL را بر اساس نقطه ویرگول (;) از هم جدا می‌کنیم
        sql_commands = query.split(';')
        
        # هر دستور را به صورت جداگانه اجرا می‌کنیم
        for command in sql_commands:
            if command.strip(): # از اجرای دستورات خالی جلوگیری می‌کند
                cursor.execute(command)
                
        connection.commit()
        print("دستورات SQL با موفقیت اجرا شدند.")
    except Error as err:
        print(f"خطا در اجرای دستور: '{err}'")
# --- پایان تغییرات ---


def create_database_and_tables():
    db_config = get_db_config()
    db_name = db_config['database']

    connection = create_server_connection(db_config['host'], db_config['user'], db_config['password'])
    if not connection:
        return
    
    # اجرای دستورات حذف و ایجاد دیتابیس به صورت جداگانه
    execute_query(connection, f"DROP DATABASE IF EXISTS {db_name};")
    execute_query(connection, f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    
    connection.close()
    
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

    create_tables_queries = """
        CREATE TABLE customers (
            id BIGINT NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            national_code VARCHAR(10) UNIQUE,
            phone_number VARCHAR(15),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;

        CREATE TABLE cash_boxes (
            id BIGINT NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            balance DECIMAL(15, 0) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;

        CREATE TABLE loans (
            id BIGINT NOT NULL PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            cash_box_id BIGINT NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            loan_term INT NOT NULL,
            interest_rate DECIMAL(5, 2) NOT NULL,
            start_date VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (cash_box_id) REFERENCES cash_boxes(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;

        CREATE TABLE installments (
            id BIGINT NOT NULL PRIMARY KEY,
            loan_id BIGINT NOT NULL,
            due_date VARCHAR(10) NOT NULL,
            amount_due DECIMAL(15, 0) NOT NULL,
            amount_paid DECIMAL(15, 0) DEFAULT 0,
            payment_date VARCHAR(10) NULL,
            is_paid BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;

        CREATE TABLE payment_details (
            id BIGINT NOT NULL PRIMARY KEY,
            installment_id BIGINT NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            payment_date VARCHAR(10) NOT NULL,
            cashbox_id BIGINT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (installment_id) REFERENCES installments(id) ON DELETE CASCADE,
            FOREIGN KEY (cashbox_id) REFERENCES cash_boxes(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        
        CREATE TABLE expense_categories (
            id BIGINT NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE
        ) ENGINE=InnoDB;

        CREATE TABLE expenses (
            id BIGINT NOT NULL PRIMARY KEY,
            category_id BIGINT NOT NULL,
            cashbox_id BIGINT NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            description TEXT,
            expense_date VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES expense_categories(id),
            FOREIGN KEY (cashbox_id) REFERENCES cash_boxes(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;

        CREATE TABLE transactions (
            id BIGINT NOT NULL PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            amount DECIMAL(15, 0) NOT NULL,
            date VARCHAR(10) NOT NULL,
            source_id BIGINT,
            destination_id BIGINT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
    """

    if connection:
        execute_query(connection, create_tables_queries)
        connection.close()
        print("تمامی جداول با ساختار جدید با موفقیت ایجاد شدند.")

if __name__ == "__main__":
    create_database_and_tables()