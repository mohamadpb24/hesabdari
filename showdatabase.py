import tkinter as tk
from tkinter import font, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import logging
import configparser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModernDatabaseViewer(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Modern Database Viewer (Search & Copy)")
        
        # تنظیم ابعاد و وسط‌چین کردن
        w, h = 1200, 800
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int(ws/2 - w/2), int(hs/2 - h/2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.engine = None
        self.df = pd.DataFrame() # ذخیره دیتای اصلی برای فیلتر سریع
        
        # استایل جدول
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        
        try:
            self.db_config = self._get_db_config()
        except Exception as e:
            messagebox.showerror("Config Error", f"خطا در خواندن فایل config.ini:\n{e}")
            self.destroy()
            return

        self.connect_to_db()
        self.current_identity_col = None
        self.current_primary_key = None
        
        self.create_widgets()
        self.create_context_menu() # منوی راست کلیک
        self.after(200, self.load_tables)

    def _get_db_config(self):
        config = configparser.ConfigParser()
        if not config.read('config.ini'):
            raise Exception("فایل config.ini یافت نشد.")
        if 'sqlserver' not in config:
            raise Exception("بخش [sqlserver] در فایل config.ini یافت نشد.")
        return dict(config['sqlserver'])

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # --- پنل کنترل (بالا) ---
        top_frame = ttk.Labelframe(main_frame, text="Controls", padding=15, bootstyle="info")
        top_frame.pack(fill=X, pady=(0, 15))

        # انتخاب جدول
        ttk.Label(top_frame, text="Select Table:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 5))
        self.table_selector = ttk.Combobox(top_frame, state="readonly", font=("Segoe UI", 10), width=25)
        self.table_selector.pack(side=LEFT, padx=(0, 15))
        self.table_selector.bind("<<ComboboxSelected>>", self.display_table_data)
        
        # دکمه رفرش
        ttk.Button(top_frame, text="↻ Refresh", command=self.display_table_data, bootstyle="outline-info").pack(side=LEFT, padx=(0, 20))

        # --- بخش جستجو (جدید) ---
        ttk.Label(top_frame, text="Search / Filter:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=30, bootstyle="primary")
        self.search_entry.pack(side=LEFT, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.filter_data) # فیلتر لحظه ای
        
        # دکمه پاک کردن جستجو
        ttk.Button(top_frame, text="✖", command=self.clear_search, bootstyle="outline-secondary", width=3).pack(side=LEFT)

        # --- جدول دیتا ---
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=BOTH, expand=YES, pady=(0, 15))

        vsb = ttk.Scrollbar(table_container, orient="vertical", bootstyle="round")
        hsb = ttk.Scrollbar(table_container, orient="horizontal", bootstyle="round")

        self.tree = ttk.Treeview(
            table_container, 
            show="headings", 
            selectmode="extended", 
            yscrollcommand=vsb.set, 
            xscrollcommand=hsb.set,
            bootstyle="info"
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.tree.pack(fill=BOTH, expand=YES)
        
        # اتصال رویدادها
        self.tree.bind("<Delete>", self.delete_selected_record)
        self.tree.bind("<Button-3>", self.show_context_menu) # کلیک راست برای کپی

        # --- پنل پایین ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=X)

        self.delete_button = ttk.Button(
            bottom_frame, text="Delete Selected Record(s)", 
            command=self.delete_selected_record, bootstyle="danger", width=25
        )
        self.delete_button.pack(side=RIGHT)

        self.status_bar = ttk.Label(self, text="Ready", bootstyle="inverse-secondary", padding=5, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)

    def create_context_menu(self):
        """ایجاد منوی راست کلیک"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Cell Value", command=self.copy_cell_value)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Row", command=self.delete_selected_record)

    def connect_to_db(self):
        try:
            cfg = self.db_config
            driver = cfg.get('driver', 'ODBC Driver 17 for SQL Server').replace(' ', '+')
            conn_str = f"mssql+pyodbc://{cfg['user']}:{cfg['password']}@{cfg['server']}/{cfg['database']}?driver={driver}&TrustServerCertificate=yes"
            self.engine = create_engine(conn_str, fast_executemany=True)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.destroy()

    def load_tables(self):
        try:
            query = "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';"
            df = pd.read_sql(query, self.engine)
            tables = [f"{r.TABLE_SCHEMA}.{r.TABLE_NAME}" for i, r in df.iterrows()]
            self.table_selector['values'] = tables
            if tables:
                self.table_selector.current(0)
                self.display_table_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_identity_column(self, schema, table):
        try:
            sql = text(f"SELECT name FROM sys.identity_columns WHERE object_id = OBJECT_ID('{schema}.{table}')")
            with self.engine.connect() as conn:
                result = conn.execute(sql).fetchone()
                if result: return result[0]
        except: pass
        return None

    def get_primary_key(self, schema, table):
        try:
            insp = inspect(self.engine)
            pk = insp.get_pk_constraint(table, schema)
            if pk and pk['constrained_columns']: return pk['constrained_columns'][0]
        except: pass
        return None

    def display_table_data(self, event=None):
        full_name = self.table_selector.get()
        if not full_name: return

        self.clear_search() # پاک کردن سرچ قبلی هنگام تعویض جدول
        self.status_bar.config(text=f"Fetching data from '{full_name}'...")
        self.update_idletasks()

        try:
            schema, table = full_name.split('.', 1)
            self.current_identity_col = self.get_identity_column(schema, table)
            self.current_primary_key = self.get_primary_key(schema, table)

            base_query = f"SELECT * FROM [{schema}].[{table}]"
            
            if self.current_identity_col:
                query = f"{base_query} ORDER BY [{self.current_identity_col}] ASC"
                sort_msg = f"Sorted by Identity: {self.current_identity_col}"
            elif self.current_primary_key:
                query = f"{base_query} ORDER BY [{self.current_primary_key}] ASC"
                sort_msg = f"Sorted by PK: {self.current_primary_key}"
            else:
                query = base_query
                sort_msg = "Unsorted"

            # ذخیره دیتا در متغیر کلاس برای فیلتر کردن
            self.df = pd.read_sql(query, self.engine)
            
            # اگر نامرتب بود، تلاش کن با ستون تاریخ مرتب کنی
            if "Unsorted" in sort_msg:
                 possible_sort = [c for c in self.df.columns if any(x in c.lower() for x in ['date', 'time', 'created', 'id'])]
                 if possible_sort:
                     self.df = self.df.sort_values(by=possible_sort[0], ascending=True)

            self.populate_tree(self.df)
            self.status_bar.config(text=f"Loaded {len(self.df)} rows. {sort_msg}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def populate_tree(self, dataframe):
        """نمایش دیتافریم در جدول (بهینه شده برای سرچ)"""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(dataframe.columns)
        
        # تنظیم هدرها
        for col in dataframe.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, anchor=CENTER, width=100)

        # پر کردن ردیف‌ها
        for index, row in dataframe.iterrows():
            tags = ('even',) if index % 2 == 0 else ('odd',)
            self.tree.insert("", "end", values=[str(v) for v in row], tags=tags)

        self.tree.tag_configure('odd', background='#f8f9fa')
        self.tree.tag_configure('even', background='#ffffff')
        
        self.auto_adjust_column_width()

    def filter_data(self, event=None):
        """فیلتر کردن دیتا بر اساس ورودی کاربر"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.populate_tree(self.df) # نمایش همه اگر خالی بود
            self.status_bar.config(text=f"Showing all {len(self.df)} rows.")
            return

        # جستجوی عبارت در تمام ستون‌ها
        # تبدیل همه به رشته -> تبدیل به حروف کوچک -> بررسی وجود عبارت
        mask = self.df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        filtered_df = self.df[mask]
        
        self.populate_tree(filtered_df)
        self.status_bar.config(text=f"Filtered: {len(filtered_df)} rows found matching '{search_term}'.")

    def clear_search(self):
        self.search_var.set("")
        if not self.df.empty:
            self.populate_tree(self.df)
            self.status_bar.config(text="Search cleared.")

    def show_context_menu(self, event):
        """نمایش منوی راست کلیک روی سطر انتخاب شده"""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if item:
            self.tree.selection_set(item) # انتخاب سطر زیر موس
            self.clicked_item = item
            self.clicked_column = column # آیدی ستون مثل #1
            self.context_menu.post(event.x_root, event.y_root)

    def copy_cell_value(self):
        """کپی مقدار سلول به کلیپ‌بورد"""
        try:
            # تبدیل آیدی ستون (مثلا #1) به ایندکس عدد (0)
            col_index = int(self.clicked_column.replace('#', '')) - 1
            
            # دریافت مقادیر سطر
            values = self.tree.item(self.clicked_item, 'values')
            
            if col_index < len(values):
                val_to_copy = values[col_index]
                self.clipboard_clear()
                self.clipboard_append(val_to_copy)
                self.status_bar.config(text=f"Copied to clipboard: {val_to_copy}")
        except Exception as e:
            logging.error(f"Copy error: {e}")

    def sort_treeview(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try: l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            tags = ('even',) if index % 2 == 0 else ('odd',)
            self.tree.item(k, tags=tags)
        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def auto_adjust_column_width(self):
        fm = font.nametofont("TkDefaultFont")
        for col in self.tree["columns"]:
            max_w = fm.measure(col) + 20
            # فقط 50 تای اول رو چک کن برای سرعت
            for item in self.tree.get_children()[:50]:
                try:
                    val = self.tree.item(item, 'values')[self.tree["columns"].index(col)]
                    w = fm.measure(str(val)) + 20
                    if w > max_w: max_w = w
                except: pass
            self.tree.column(col, width=min(max_w, 400), stretch=False)

    def delete_selected_record(self, event=None):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Warning", "Select a row first.")

        pk_col = self.current_primary_key
        if not pk_col:
            # درخواست دستی شناسه
            cols = list(self.tree["columns"])
            top = ttk.Toplevel(self)
            top.title("Select ID")
            ttk.Label(top, text="Select ID Column:").pack(pady=5)
            cb = ttk.Combobox(top, values=cols, state="readonly")
            cb.pack(pady=5); cb.current(0)
            def on_set():
                nonlocal pk_col; pk_col = cb.get(); top.destroy()
            ttk.Button(top, text="OK", command=on_set).pack(pady=5)
            self.wait_window(top)
            if not pk_col: return

        if not messagebox.askyesno("Confirm", "Delete selected record(s)?"): return

        try:
            full_name = self.table_selector.get()
            schema, table = full_name.split('.', 1)
            pk_idx = self.tree["columns"].index(pk_col)
            
            with self.engine.connect() as conn:
                trans = conn.begin()
                for item in sel:
                    val = self.tree.item(item, 'values')[pk_idx]
                    conn.execute(text(f"DELETE FROM [{schema}].[{table}] WHERE [{pk_col}] = :v"), {"v": val})
                    self.tree.delete(item)
                trans.commit()
            
            # آپدیت کردن دیتافریم اصلی که سرچ درست کار کنه
            # اینجا فقط رفرش میکنیم که ساده ترین راهه برای هماهنگی دیتا
            self.display_table_data() 
            self.status_bar.config(text="Records deleted.")
            
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))

    def on_closing(self):
        if self.engine: self.engine.dispose()
        self.destroy()

if __name__ == "__main__":
    app = ModernDatabaseViewer()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
