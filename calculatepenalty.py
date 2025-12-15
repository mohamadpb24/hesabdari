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
    جریمه‌ها و وضعیت (Status) اقساط را بر اساس قوانین جدید محاسبه و به‌روزرسانی می‌کند.
    """
    setup_logging()
    logging.info("=================================================")
    logging.info("شروع فرآیند هوشمند تعیین وضعیت و محاسبه جریمه‌ها...")

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

            # --- کوئری هوشمند آپدیت وضعیت و جریمه ---
            query = """
                WITH CalculationBase AS (
                    SELECT
                        inst.ID,
                        inst.Status AS OldStatus,
                        inst.DueAmount,
                        inst.PaidAmount,
                        inst.DueDate,
                        inst.PaymentDate,
                        l.PenaltyRate,
                        -- محاسبه تعداد روزهای گذشته از سررسید (مثبت یعنی معوق، منفی یعنی آینده)
                        DATEDIFF(day, TRY_CONVERT(date, inst.DueDate, 111), TRY_CONVERT(date, ?, 111)) AS DaysPassed,
                        -- محاسبه روزهای مشمول جریمه (کسر ۳ روز تنفس)
                        CASE 
                            WHEN DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111)) > 0 
                            THEN DATEDIFF(day, DATEADD(day, 3, TRY_CONVERT(date, inst.DueDate, 111)), TRY_CONVERT(date, ?, 111))
                            ELSE 0 
                        END AS PenaltyDaysCalc
                    FROM
                        Installments AS inst
                    JOIN
                        Loans AS l ON inst.Loan_ID = l.ID
                ),
                CorrectValues AS (
                    SELECT
                        ID,
                        OldStatus,
                        PenaltyDaysCalc AS NewPenaltyDays,
                        -- محاسبه مبلغ جریمه جدید
                        (ISNULL(DueAmount, 0) * ISNULL(PenaltyRate, 0) / 100) * PenaltyDaysCalc AS NewPenaltyAmount,
                        -- محاسبه کل بدهی جدید
                        ISNULL(DueAmount, 0) + ((ISNULL(DueAmount, 0) * ISNULL(PenaltyRate, 0) / 100) * PenaltyDaysCalc) AS NewTotalAmount,
                        -- محاسبه مانده جدید
                        (ISNULL(DueAmount, 0) + ((ISNULL(DueAmount, 0) * ISNULL(PenaltyRate, 0) / 100) * PenaltyDaysCalc)) - ISNULL(PaidAmount, 0) AS NewPaymentRemain,
                        
                        -- *** منطق تعیین وضعیت (Status) ***
                        CASE
                            -- ۱. اگر قسط تسویه شده (مانده صفر یا کمتر)، وضعیت پرداخت کامل است
                            WHEN (ISNULL(DueAmount, 0) + ((ISNULL(DueAmount, 0) * ISNULL(PenaltyRate, 0) / 100) * PenaltyDaysCalc)) - ISNULL(PaidAmount, 0) <= 0 THEN
                                CASE 
                                    WHEN OldStatus = 36 THEN 36 -- اگر قبلاً تسویه پیش از موعد کل وام خورده، دست نزن
                                    WHEN PaymentDate < DueDate THEN 35 -- پرداخت قبل از موعد
                                    ELSE 32 -- پرداخت کامل سر موعد یا با تاخیر ولی تسویه شده
                                END
                            
                            -- ۲. اگر وضعیت حقوقی است، سیستم اتوماتیک تغییر ندهد (فقط جریمه آپدیت شود)
                            WHEN OldStatus = 40 THEN 40 

                            -- ۳. بررسی زمان و تاخیر برای اقساط باز
                            WHEN DaysPassed < 0 THEN 30 -- هنوز موعدش نرسیده
                            WHEN DaysPassed = 0 THEN 31 -- سررسید امروز است
                            
                            -- دوره تنفس (۱ تا ۳ روز)
                            WHEN DaysPassed BETWEEN 1 AND 3 THEN 
                                CASE 
                                    WHEN ISNULL(PaidAmount, 0) > 0 THEN 33 -- بخشی پرداخت شده (ناقص)
                                    ELSE 37 -- معوق در دوره تنفس
                                END
                            
                            -- مشکوک الوصول (بیش از ۳۵ روز)
                            WHEN DaysPassed > 35 THEN 39 
                            
                            -- معوق عادی (بیش از ۳ روز و کمتر از ۳۵ روز)
                            WHEN DaysPassed > 3 THEN 
                                CASE 
                                    WHEN ISNULL(PaidAmount, 0) > 0 THEN 34 -- بخشی پرداخت شده ولی جریمه دارد
                                    ELSE 38 -- معوق کامل با جریمه
                                END
                                
                            ELSE OldStatus -- حالت پیش‌فرض
                        END AS NewStatus
                    FROM CalculationBase
                )
                -- آپدیت جدول اصلی فقط در صورت وجود تغییر
                UPDATE inst
                SET
                    inst.Status = cv.NewStatus,
                    inst.PenaltyDays = cv.NewPenaltyDays,
                    inst.PenaltyAmount = cv.NewPenaltyAmount,
                    inst.TotalAmount = cv.NewTotalAmount,
                    inst.PaymentRemain = cv.NewPaymentRemain
                FROM
                    Installments AS inst
                JOIN
                    CorrectValues AS cv ON inst.ID = cv.ID
                WHERE
                    inst.Status <> cv.NewStatus
                    OR ISNULL(inst.PenaltyDays, 0) <> cv.NewPenaltyDays
                    OR ISNULL(inst.PenaltyAmount, 0) <> cv.NewPenaltyAmount
                    OR ISNULL(inst.TotalAmount, 0) <> cv.NewTotalAmount
                    OR ISNULL(inst.PaymentRemain, 0) <> cv.NewPaymentRemain;
            """
            
            logging.info("در حال اجرای کوئری همگام‌سازی وضعیت‌ها و جریمه‌ها...")
            # تاریخ امروز ۳ بار برای محاسبه DaysPassed و PenaltyDaysCalc نیاز است
            params = (today_jalali_str, today_jalali_str, today_jalali_str)
            cursor.execute(query, params)
            updated_rows = cursor.rowcount
            
            conn.commit()

            if updated_rows > 0:
                logging.info(f"عملیات با موفقیت انجام شد. تعداد {updated_rows} قسط به‌روزرسانی (تعیین وضعیت/محاسبه جریمه) شدند.")
            else:
                logging.info("اطلاعات تمام اقساط صحیح و به‌روز بود. تغییری اعمال نشد.")

    except configparser.Error as e:
        logging.critical(f"خطا در خواندن فایل کانفیگ: {e}")
    except pyodbc.Error as e:
        logging.critical(f"خطا در اتصال یا اجرای کوئری دیتابیس: {e}")
    except Exception as e:
        logging.critical(f"یک خطای پیش‌بینی نشده رخ داد: {e}", exc_info=True)
    finally:
        logging.info("پایان فرآیند.")
        logging.info("=================================================\n")

if __name__ == "__main__":
    apply_penalties()