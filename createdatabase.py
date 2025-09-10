# createdatabase.py (نسخه نهایی با افزودن جدول payment_details)

import mysql.connector
from mysql.connector import Error
import configparser

def get_db_config():
    """اطلاعات اتصال به پایگاه داده را از فایل config.ini می‌خواند."""
    config = configparser.ConfigParser()
    config.read('config.ini')
    return {
        'host': config['mysql']['host'],
        'user': config['mysql']['user'],
        'password': config['mysql']['password'],
        'database': config['mysql'].get('database', 'installment_sales_db_v2')
    }

def create_server_connection(host_name, user_name, user_password):
    """اتصال اولیه به سرور MySQL را برقرار می‌کند."""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password
        )
        print("✅ اتصال به سرور MySQL با موفقیت برقرار شد.")
    except Error as err:
        print(f"❌ خطا در اتصال به سرور: '{err}'")
    return connection

def execute_query(connection, query):
    """
    یک یا چند دستور SQL را اجرا می‌کند.
    این نسخه برای سازگاری بیشتر، دستورات را جدا کرده و تک به تک اجرا می‌کند.
    """
    cursor = connection.cursor()
    try:
        # دستورات SQL را بر اساس نقطه ویرگول (;) از هم جدا می‌کنیم
        sql_commands = query.split(';')
        
        # هر دستور را به صورت جداگانه اجرا می‌کنیم
        for command in sql_commands:
            if command.strip(): # از اجرای دستورات خالی جلوگیری می‌کند
                cursor.execute(command)
                
        connection.commit()
        print("🚀 دستورات SQL با موفقیت اجرا شدند.")
    except Error as err:
        print(f"❌ خطا در اجرای دستور: '{err}'")

def create_database_and_tables():
    """پایگاه داده و تمام جداول جدید را ایجاد می‌کند."""
    db_config = get_db_config()
    db_name = db_config['database']

    connection = create_server_connection(db_config['host'], db_config['user'], db_config['password'])
    if not connection:
        return

    try:
        print(f"ℹ️ در حال حذف و ایجاد دیتابیس '{db_name}'...")
        # اجرای دستورات به صورت جداگانه برای اطمینان بیشتر
        execute_query(connection, f"DROP DATABASE IF EXISTS `{db_name}`")
        execute_query(connection, f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ دیتابیس '{db_name}' با موفقیت ایجاد شد.")
    finally:
        connection.close()

    try:
        connection = mysql.connector.connect(**db_config)
        print(f"✅ اتصال به دیتابیس '{db_name}' برای ساخت جداول برقرار شد.")
    except Error as err:
        print(f"❌ خطا در اتصال به دیتابیس '{db_name}': '{err}'")
        return

    create_tables_queries = """
    -- Table for Users (Customers)
    CREATE TABLE `users` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `user_type` ENUM('WEBSITE', 'OFFLINE') NOT NULL,
        `status` ENUM('REGISTERED', 'IDENTITY_PENDING', 'CREDIT_PENDING', 'CHECK_PENDING', 'CREDIT_ACTIVE', 'HAS_LOAN', 'FULLY_SETTLED', 'REJECTED', 'INACTIVE') NOT NULL,
        `name` VARCHAR(255) NOT NULL,
        `national_code` VARCHAR(10) UNIQUE,
        `phone_number` VARCHAR(15) UNIQUE,
        `email` VARCHAR(255) UNIQUE,
        `password_hash` VARCHAR(255),
        `address` TEXT,
        `total_debt` DECIMAL(15, 0) DEFAULT 0,
        `credit_limit` DECIMAL(15, 0) DEFAULT 0,
        `is_late_fee_applicable` BOOLEAN DEFAULT FALSE,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;

    -- Table for Cash Boxes
    CREATE TABLE `cash_boxes` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `name` VARCHAR(255) NOT NULL,
        `balance` DECIMAL(15, 0) DEFAULT 0,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;

    -- Table for Loans
    CREATE TABLE `loans` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `customer_id` CHAR(36) NOT NULL,
        `cash_box_id` CHAR(36) NOT NULL,
        `status` ENUM('ACTIVE', 'FULLY_SETTLED', 'OVERDUE') NOT NULL,
        `amount` DECIMAL(15, 0) NOT NULL,
        `loan_term` INT NOT NULL,
        `interest_rate` DECIMAL(5, 2) NOT NULL,
        `start_date` DATE NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (`customer_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
        FOREIGN KEY (`cash_box_id`) REFERENCES `cash_boxes`(`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB;

    -- Table for Installments
    CREATE TABLE `installments` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `loan_id` CHAR(36) NOT NULL,
        `status` ENUM('PENDING', 'PAID', 'PARTIALLY_PAID', 'OVERDUE') NOT NULL,
        `due_date` DATE NOT NULL,
        `amount_due` DECIMAL(15, 0) NOT NULL,
        `amount_paid` DECIMAL(15, 0) DEFAULT 0,
        `payment_date` DATE,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB;

    -- *** شروع: جدول جدید و ضروری برای جزئیات پرداخت ***
    CREATE TABLE `payment_details` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `installment_id` CHAR(36) NOT NULL,
        `amount` DECIMAL(15, 0) NOT NULL,
        `payment_date` DATE NOT NULL,
        `cashbox_id` CHAR(36) NOT NULL,
        `description` TEXT,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`installment_id`) REFERENCES `installments`(`id`) ON DELETE CASCADE,
        FOREIGN KEY (`cashbox_id`) REFERENCES `cash_boxes`(`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB;
    -- *** پایان: جدول جدید ***

    -- Table for User Verifications
    CREATE TABLE `user_verifications` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `user_id` CHAR(36) NOT NULL,
        `step_name` VARCHAR(255) NOT NULL,
        `status` ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL,
        `rejection_reason` TEXT,
        `submitted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        `reviewed_at` TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB;

    -- Table for Checks
    CREATE TABLE `checks` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `user_id` CHAR(36) NOT NULL,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `check_image_url` VARCHAR(255),
        `status` ENUM('IMAGE_PENDING', 'IMAGE_APPROVED', 'PHYSICAL_PENDING', 'RECEIVED') NOT NULL,
        `check_date` DATE NOT NULL,
        `check_amount` DECIMAL(15, 0) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB;

    -- Table for Expense Categories
    CREATE TABLE `expense_categories` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `name` VARCHAR(255) NOT NULL UNIQUE,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;

    -- Table for Expenses
    CREATE TABLE `expenses` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `category_id` CHAR(36) NOT NULL,
        `cashbox_id` CHAR(36) NOT NULL,
        `amount` DECIMAL(15, 0) NOT NULL,
        `description` TEXT,
        `expense_date` DATE NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`category_id`) REFERENCES `expense_categories`(`id`) ON DELETE RESTRICT,
        FOREIGN KEY (`cashbox_id`) REFERENCES `cash_boxes`(`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB;

    -- Table for All Financial Transactions
    CREATE TABLE `transactions` (
        `id` CHAR(36) NOT NULL PRIMARY KEY,
        `readable_id` VARCHAR(255) NOT NULL UNIQUE,
        `type` VARCHAR(50) NOT NULL,
        `amount` DECIMAL(15, 0) NOT NULL,
        `date` DATE NOT NULL,
        `source_id` CHAR(36),
        `destination_id` CHAR(36),
        `description` TEXT,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """

    if connection:
        print("ℹ️ در حال ساخت جداول...")
        execute_query(connection, create_tables_queries)
        connection.close()
        print("\n🎉 فرآیند ساخت دیتابیس و جداول با موفقیت به پایان رسید.")

if __name__ == "__main__":
    create_database_and_tables()