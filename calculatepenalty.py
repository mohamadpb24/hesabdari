# نام فایل: daily_penalty_calculator.py

import pyodbc
import configparser
import logging
import os
import jdatetime
from datetime import datetime

# نام فایل کانفیگ که در کنار اسکریپت قرار خواهد گرفت
CONFIG_FILE = 'config.ini'

def setup_config():
    """
    اگر فایل کانفیگ وجود نداشته باشد، یک نمونه از آن را ایجاد می‌کند.
    """
    if not os.path.exists(CONFIG_FILE):
        logging.info(f"فایل {CONFIG_FILE} یافت نشد. در حال ایجاد یک نمونه جدید...")
        config = configparser.ConfigParser()
        config['sqlserver'] = {
            'driver': 'ODBC Driver 17 for SQL Server',
            'server': 'YOUR_SERVER_IP_OR_HOSTNAME',
            'database': 'YOUR_DATABASE_NAME',
            'user': 'YOUR_USERNAME',
            'password': 'YOUR_PASSWORD'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        logging.info(f"فایل {CONFIG_FILE} با موفقیت ایجاد شد. لطفاً اطلاعات اتصال به دیتابیس را در آن وارد کنید و اسکریپت را مجدداً اجرا نمایید.")
        return False
    return True

def setup_logging():
    """
    سیستم لاگ‌گیری را برای ثبت وقایع در یک فایل روزانه راه‌اندازی می‌کند.
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"penalty_log_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def apply_penalties():
    """
    جریمه‌ها را برای تمام اقساط معوق محاسبه و در صورت مغایرت، دیتابیس را به‌روزرسانی می‌کند.
    """
    setup_logging()
    logging.info("=================================================")
    logging.info("شروع فرآیند هوشمند محاسبه و همگام‌سازی جریمه‌ها...")

    if not setup_config():
        return

    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        db_config = config['sqlserver']

        conn_str = (
            f"DRIVER={{{db_config['driver']}}};"
            f"SERVER={db_config['server']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['user']};"
            f"PWD={db_config['password']};"
            f"TrustServerCertificate=yes;"
        )

        logging.info("در حال اتصال به پایگاه داده...")
        with pyodbc.connect(conn_str) as conn:
            logging.info("اتصال با موفقیت برقرار شد.")
            cursor = conn.cursor()

            today_jalali_str = jdatetime.date.today().strftime('%Y/%m/%d')
            logging.info(f"تاریخ امروز (شمسی) برای محاسبه: {today_jalali_str}")

            # --- کوئری نهایی برای آپدیت هر چهار ستون ---
            query = """
                WITH CorrectValues AS (
                    -- مرحله ۱: محاسبه مقادیر صحیح برای تمام اقساط مشمول جریمه
                    SELECT
                        inst.ID,
                        DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111)) AS CorrectPenaltyDays,
                        (ISNULL(inst.DueAmount, 0) * ISNULL(l.PenaltyRate, 0) / 100) * DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111)) AS CorrectPenaltyAmount,
                        ISNULL(inst.DueAmount, 0) + (ISNULL(inst.DueAmount, 0) * ISNULL(l.PenaltyRate, 0) / 100) * DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111)) AS CorrectTotalAmount,
                        (ISNULL(inst.DueAmount, 0) + (ISNULL(inst.DueAmount, 0) * ISNULL(l.PenaltyRate, 0) / 100) * DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111))) - ISNULL(inst.PaidAmount, 0) AS CorrectPaymentRemain
                    FROM
                        Installments AS inst
                    JOIN
                        Loans AS l ON inst.Loan_ID = l.ID
                    WHERE
                        inst.Status <> 'PAID'
                        AND DATEDIFF(day, TRY_CONVERT(date, inst.DueDate, 111), TRY_CONVERT(date, ?, 111)) > 3
                )
                -- مرحله ۲: آپدیت جدول اصلی فقط در صورت وجود مغایرت در هر یک از چهار ستون
                UPDATE inst
                SET
                    inst.PenaltyDays = cv.CorrectPenaltyDays,
                    inst.PenaltyAmount = cv.CorrectPenaltyAmount,
                    inst.TotalAmount = cv.CorrectTotalAmount,
                    inst.PaymentRemain = cv.CorrectPaymentRemain
                FROM
                    Installments AS inst
                JOIN
                    CorrectValues AS cv ON inst.ID = cv.ID
                WHERE
                    ISNULL(inst.PenaltyDays, 0) <> cv.CorrectPenaltyDays
                    OR ISNULL(inst.PenaltyAmount, 0) <> cv.CorrectPenaltyAmount
                    OR ISNULL(inst.TotalAmount, 0) <> cv.CorrectTotalAmount
                    OR ISNULL(inst.PaymentRemain, 0) <> cv.CorrectPaymentRemain;
            """
            
            logging.info("در حال اجرای کوئری همگام‌سازی جریمه‌ها...")
            # تاریخ امروز پنج بار به عنوان پارامتر به کوئری ارسال می‌شود
            params = (today_jalali_str, today_jalali_str, today_jalali_str, today_jalali_str, today_jalali_str)
            cursor.execute(query, params)
            updated_rows = cursor.rowcount
            
            conn.commit()

            if updated_rows > 0:
                logging.info(f"عملیات با موفقیت انجام شد. تعداد {updated_rows} قسط به‌روزرسانی شدند.")
            else:
                logging.info("تمام جریمه‌ها در دیتابیس صحیح و به‌روز بودند. هیچ تغییری لازم نبود.")

    except configparser.Error as e:
        logging.critical(f"خطا در خواندن فایل کانفیگ: {e}")
    except pyodbc.Error as e:
        logging.critical(f"خطا در اتصال یا اجرای کوئری دیتابیس: {e}")
    except Exception as e:
        logging.critical(f"یک خطای پیش‌بینی نشده رخ داد: {e}", exc_info=True)
    finally:
        logging.info("پایان فرآیند همگام‌سازی جریمه‌ها.")
        logging.info("=================================================\n")

if __name__ == "__main__":
    apply_penalties()