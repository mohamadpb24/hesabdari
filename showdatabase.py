import tkinter as tk
from tkinter import font, TclError, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_CONFIG = {
    'host': '185.55.224.113',
    'user': 'demodeln_Pezhvak',
    'password': 'hlwO27*52',
    'database': 'demodeln_PezhvakPay'
}

class ModernDatabaseViewer(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Modern Database Viewer (Multi-Delete Enabled)")
        self.geometry("1200x800")
        self.engine = None
        self.connect_to_db()
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Segoe UI", size=10)
        self.current_primary_key = None
        self.create_widgets()
        self.after(100, self.load_tables)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(top_frame, text="Select a table:", font=(self.default_font.name, 11)).pack(side=LEFT, padx=(0,10))
        self.table_selector = ttk.Combobox(top_frame, state="readonly", font=(self.default_font.name, 11))
        self.table_selector.pack(side=LEFT, fill=X, expand=YES)
        self.table_selector.bind("<<ComboboxSelected>>", self.display_table_data)
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=BOTH, expand=YES)
        
        # --- تغییر مهم: فعال کردن انتخاب چندتایی ---
        self.tree = ttk.Treeview(table_container, show="headings", bootstyle="primary", selectmode="extended")
        
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview, bootstyle="round-info")
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview, bootstyle="round-info")
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill=BOTH, expand=YES)
        self.tree.bind("<Delete>", self.delete_selected_record)
        
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.pack(fill=X)
        self.delete_button = ttk.Button(button_frame, text="Delete Selected Record(s)", command=self.delete_selected_record, bootstyle="danger")
        self.delete_button.pack(side=LEFT, padx=5)
        self.status_bar = ttk.Label(self, text="Ready", padding=10, anchor=W, bootstyle="inverse-light")
        self.status_bar.pack(side=BOTTOM, fill=X)

    def connect_to_db(self):
        try:
            driver = "ODBC Driver 17 for SQL Server"
            conn_str = f"mssql+pyodbc://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?driver={driver}&TrustServerCertificate=yes"
            self.engine = create_engine(conn_str, fast_executemany=True)
            self.engine.connect().close()
        except Exception as e:
            ttk.dialogs.Messagebox.show_error(f"Could not connect to the database:\n{e}", "Connection Error")
            self.destroy()

    def load_tables(self):
        try:
            self.status_bar.config(text="Fetching table list...")
            self.update_idletasks()
            query = "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';"
            with self.engine.connect() as connection:
                df = pd.read_sql(query, connection)
            tables = [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" for index, row in df.iterrows()]
            self.table_selector['values'] = tables
            if tables:
                self.table_selector.current(0)
                self.display_table_data()
        except Exception as e:
            ttk.dialogs.Messagebox.show_error(f"An error occurred while fetching tables:\n{e}", "Error")

    def display_table_data(self, event=None):
        full_table_name = self.table_selector.get()
        if not full_table_name: return
        self.status_bar.config(text=f"Loading data from '{full_table_name}'...")
        self.update_idletasks()
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []
        try:
            schema, table = full_table_name.split('.', 1)
            query = f'SELECT * FROM [{schema}].[{table}]'
            df = pd.read_sql(query, self.engine)
            self.tree["columns"] = list(df.columns)
            for col in df.columns: self.tree.heading(col, text=col, anchor=CENTER)
            for index, row in df.iterrows(): self.tree.insert("", "end", values=[str(v) for v in row])
            self.auto_adjust_column_width()
            self.status_bar.config(text=f"Displayed '{full_table_name}' with {len(df)} rows.")
            
            # --- تغییر مهم: دیگر پنجره باز نمی‌شود ---
            self.current_primary_key = self.get_primary_key_info(schema, table)
            if not self.current_primary_key:
                self.status_bar.config(text=f"Warning: Primary Key not found for '{full_table_name}'. Deletion will require manual ID selection.")

        except Exception as e:
            ttk.dialogs.Messagebox.show_error(f"Could not read data from table:\n{e}", "Data Error")

    def ask_for_manual_pk(self, columns):
        dialog = ttk.Toplevel(self)
        dialog.title("Select Unique Identifier")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="No primary key was found.\nSelect a column that uniquely identifies each row:", justify=CENTER).pack(pady=10)
        selected_pk = tk.StringVar()
        pk_selector = ttk.Combobox(dialog, textvariable=selected_pk, values=columns, state="readonly")
        pk_selector.pack(pady=5, padx=10, fill=X)
        if columns: pk_selector.current(0)
        def on_confirm():
            self.current_primary_key = selected_pk.get()
            self.status_bar.config(text=f"Using '{self.current_primary_key}' as unique ID for deletion.")
            dialog.destroy()
        confirm_button = ttk.Button(dialog, text="Confirm", command=on_confirm, bootstyle="success")
        confirm_button.pack(pady=10)
        self.wait_window(dialog)

    def get_primary_key_info(self, schema, table):
        try:
            inspector = inspect(self.engine)
            pk_constraint = inspector.get_pk_constraint(table, schema)
            if pk_constraint and pk_constraint['constrained_columns']:
                return pk_constraint['constrained_columns'][0]
        except Exception as e:
            logging.error(f"Could not determine primary key for {schema}.{table}: {e}")
        return None

    def delete_selected_record(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more records to delete.")
            return

        # --- تغییر مهم: اگر کلید اصلی پیدا نشده بود، همینجا سوال کن ---
        if not self.current_primary_key:
            self.ask_for_manual_pk(list(self.tree["columns"]))
            # اگر کاربر پنجره را ببندد و انتخاب نکند
            if not self.current_primary_key:
                messagebox.showerror("Identifier Not Set", "Unique identifier column is not set. Cannot delete.")
                return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete {len(selected_items)} record(s)?")
        if not confirm: return

        pk_column_index = list(self.tree["columns"]).index(self.current_primary_key)
        full_table_name = self.table_selector.get()
        schema, table = full_table_name.split('.', 1)
        
        records_deleted = 0
        try:
            with self.engine.connect() as connection:
                trans = connection.begin()
                for item in selected_items:
                    record_values = self.tree.item(item, 'values')
                    pk_value = record_values[pk_column_index]
                    query = text(f'DELETE FROM [{schema}].[{table}] WHERE [{self.current_primary_key}] = :pk_val')
                    connection.execute(query, {"pk_val": pk_value})
                trans.commit()
            
            # حذف ردیف‌ها از جدول نمایشی بعد از موفقیت در دیتابیس
            for item in selected_items:
                self.tree.delete(item)
                records_deleted += 1

            self.status_bar.config(text=f"{records_deleted} record(s) were deleted successfully.")
            messagebox.showinfo("Success", f"{records_deleted} record(s) were deleted successfully.")
        except Exception as e:
            messagebox.showerror("Deletion Failed", f"An error occurred: {e}")

    def auto_adjust_column_width(self):
        for col in self.tree["columns"]:
            max_width = self.default_font.measure(col.title())
            for item in self.tree.get_children():
                try:
                    cell_value = self.tree.item(item, 'values')[self.tree["columns"].index(col)]
                    cell_width = self.default_font.measure(str(cell_value))
                    if cell_width > max_width: max_width = cell_width
                except (IndexError, TclError): pass
            self.tree.column(col, width=max_width + 30, stretch=False)

    def on_closing(self):
        if self.engine: self.engine.dispose()
        self.destroy()

if __name__ == "__main__":
    app = ModernDatabaseViewer()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()