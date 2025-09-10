import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc  # <--- تغییر: استفاده از pyodbc
import pandas as pd

# --- اطلاعات اتصال به دیتابیس SQL Server ---
DB_CONFIG = {
    'host': '185.55.224.113',
    'user': 'demodeln_Pezhvak',
    'password': 'hlwO27*52',
    'database': 'demodeln_PezhvakPay'
}

class DatabaseViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نمایشگر دیتابیس SQL Server")
        self.geometry("800x600")

        self.connection = None
        self.connect_to_db()

        # --- فریم اصلی ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- منوی کشویی برای انتخاب جدول ---
        ttk.Label(main_frame, text="یک جدول را انتخاب کنید:").pack(pady=5)
        self.table_selector = ttk.Combobox(main_frame, state="readonly")
        self.table_selector.pack(pady=5, fill=tk.X)
        self.table_selector.bind("<<ComboboxSelected>>", self.display_table_data)
        
        # --- فریم برای جدول ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # --- ویجت جدول (Treeview) ---
        self.tree = ttk.Treeview(table_frame, show="headings")
        
        # --- اسکرول‌بارها ---
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.load_tables()

    def connect_to_db(self):
        """متصل شدن به دیتابیس SQL Server با pyodbc"""
        try:
            # رشته اتصال مخصوص pyodbc برای SQL Server
            conn_str = (
                # ممکن است لازم باشد 'ODBC Driver 17 for SQL Server' را به نسخه درایور نصب شده روی سیستم خود تغییر دهید
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={DB_CONFIG['host']};"
                f"DATABASE={DB_CONFIG['database']};"
                f"UID={DB_CONFIG['user']};"
                f"PWD={DB_CONFIG['password']};"
                f"TrustServerCertificate=yes;" # برای جلوگیری از خطای SSL
            )
            self.connection = pyodbc.connect(conn_str)
        except pyodbc.Error as err:
            messagebox.showerror("خطای اتصال", f"خطا در اتصال به دیتابیس:\n{err}")
            self.destroy()

    def load_tables(self):
        """گرفتن لیست جداول از دیتابیس SQL Server"""
        if not self.connection:
            return
        try:
            cursor = self.connection.cursor()
            # کوئری استاندارد برای گرفتن نام جداول در SQL Server
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            tables = [row[0] for row in cursor.fetchall()]
            self.table_selector['values'] = tables
            if tables:
                self.table_selector.current(0)
                self.display_table_data() # نمایش خودکار جدول اول
        except pyodbc.Error as err:
            messagebox.showerror("خطا در بارگذاری جداول", f"خطا: {err}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            
    def display_table_data(self, event=None):
        """نمایش اطلاعات جدول انتخاب شده"""
        table_name = self.table_selector.get()
        if not table_name:
            return
            
        # پاک کردن اطلاعات قبلی
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree["columns"] = []
        
        try:
            # استفاده از pandas برای خواندن داده‌ها (سازگار با pyodbc)
            query = f"SELECT * FROM [{table_name}]" # در SQL Server بهتر است نام جدول داخل [] باشد
            df = pd.read_sql(query, self.connection)
            
            # تنظیم ستون‌ها
            self.tree["columns"] = list(df.columns)
            for col in df.columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=120, anchor='center')
            
            # وارد کردن ردیف‌ها
            for index, row in df.iterrows():
                self.tree.insert("", "end", values=list(row))
                
        except (pyodbc.Error, pd.io.sql.DatabaseError) as err:
            messagebox.showerror("خطا در خواندن اطلاعات", f"خطا: {err}")

    def on_closing(self):
        """بستن اتصال دیتابیس هنگام خروج از برنامه"""
        if self.connection:
            self.connection.close()
        self.destroy()

if __name__ == "__main__":
    app = DatabaseViewer()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()