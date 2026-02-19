import customtkinter as ctk
import pyodbc
import jdatetime
import pandas as pd
import numpy_financial as npf
from tkinter import messagebox
import arabic_reshaper
from bidi.algorithm import get_display

# ==========================================
# تنظیمات دیتابیس (اطلاعات خود را اینجا وارد کنید)
# ==========================================
DB_CONFIG = {
    "server": ".",           # نام سرور (مثلا . یا localhost)
    "database": "Pezhvak_Local", # نام دیتابیس
    "username": "sa",        # نام کاربری SQL
    "password": "Qwer1234"        # رمز عبور SQL
}

# تنظیمات ظاهری کلی
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- توابع کمکی ---
def fix_text(text):
    """متن فارسی را برای نمایش صحیح در تکینتر آماده میکند"""
    if not text: return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def format_money(value):
    """عدد را به فرمت سه رقم سه رقم تبدیل میکند"""
    return f"{int(value):,}"

class ModernFinanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(fix_text("محاسبه گر سود مرکب حرفه‌ای"))
        self.geometry("1280x850")
        
        # تعریف فونت‌های اختصاصی
        self.font_ui = ctk.CTkFont(family="Tahoma", size=14)
        self.font_table_header = ctk.CTkFont(family="Tahoma", size=14, weight="bold")
        self.font_table_row = ctk.CTkFont(family="Consolas", size=15) # فونت اعداد خوانا
        self.font_big_number = ctk.CTkFont(family="Arial", size=32, weight="bold")
        self.font_card_title = ctk.CTkFont(family="Tahoma", size=16)

        # محاسبه نرخ پایه سیستم (موتور 4 درصد فلت)
        self.effective_monthly_rate = self.calculate_base_rate()

        # ساخت رابط کاربری
        self.setup_layout()

    def calculate_base_rate(self):
        """محاسبه نرخ موثر داخلی (IRR) برای وام 12 ماهه با 4 درصد سود فلت"""
        # پرداخت 100 واحد، دریافت 148 واحد در 12 قسط
        cash_flows = [-100] + [148/12] * 12
        return npf.irr(cash_flows)

    def setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === 1. سایدبار (منو سمت چپ) ===
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # لوگو و اطلاعات نرخ
        ctk.CTkLabel(self.sidebar, text="Compound\nMaster", font=ctk.CTkFont(size=28, weight="bold"), text_color="#3B8ED0").pack(pady=(30,10))
        
        rate_txt = fix_text(f"نرخ رشد موثر: {self.effective_monthly_rate*100:.1f}%")
        ctk.CTkLabel(self.sidebar, text=rate_txt, text_color="#2CC985", font=self.font_ui).pack(pady=5)
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=20)

        # انتخاب تاریخ
        ctk.CTkLabel(self.sidebar, text=fix_text("تاریخ محاسبه (هدف):"), font=self.font_ui, anchor="e").pack(fill="x", padx=20)
        
        date_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        date_box.pack(pady=10)
        
        now = jdatetime.datetime.now()
        self.ent_d = ctk.CTkEntry(date_box, width=50, justify="center", font=ctk.CTkFont(size=16)); self.ent_d.insert(0, now.day); self.ent_d.pack(side="right", padx=2)
        ctk.CTkLabel(date_box, text="/").pack(side="right")
        self.ent_m = ctk.CTkEntry(date_box, width=50, justify="center", font=ctk.CTkFont(size=16)); self.ent_m.insert(0, now.month); self.ent_m.pack(side="right", padx=2)
        ctk.CTkLabel(date_box, text="/").pack(side="right")
        self.ent_y = ctk.CTkEntry(date_box, width=70, justify="center", font=ctk.CTkFont(size=16)); self.ent_y.insert(0, now.year); self.ent_y.pack(side="right", padx=2)

        ctk.CTkButton(self.sidebar, text=fix_text("تنظیم به امروز"), command=self.set_today, fg_color="transparent", border_width=1, font=self.font_ui).pack(pady=5)

        # دکمه محاسبه بزرگ
        self.btn_calc = ctk.CTkButton(self.sidebar, text=fix_text("شروع محاسبه"), command=self.run_process, height=60, font=ctk.CTkFont(family="Tahoma", size=18, weight="bold"), fg_color="#106EBE")
        self.btn_calc.pack(side="bottom", fill="x", padx=20, pady=30)

        # === 2. پنل اصلی (سمت راست) ===
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # ردیف کارت‌های اطلاعات (Dashboard)
        self.dashboard_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.dashboard_frame.pack(fill="x", pady=(0, 20))
        self.dashboard_frame.grid_columnconfigure((0,1,2), weight=1)

        self.card_invest = self.create_kpi_card(self.dashboard_frame, "سرمایه اولیه کل", "0", 0, "#2B2B2B")
        self.card_value = self.create_kpi_card(self.dashboard_frame, "ارزش تئوری فعلی", "0", 1, "#1c4b82") # آبی تیره
        self.card_profit = self.create_kpi_card(self.dashboard_frame, "سود خالص سیستم", "0", 2, "#18593b") # سبز تیره

        # جدول داده‌ها
        # سرستون‌ها
        header_frame = ctk.CTkFrame(self.main_panel, height=40, fg_color="#202020", corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)
        
        headers = ["تاریخ واریز", "مبلغ واریزی (تومان)", "مدت (ماه)", "ضریب رشد", "ارزش امروز (تومان)"]
        widths = [150, 200, 100, 100, 200]
        
        for i, (h, w) in enumerate(zip(headers, widths)):
            # ترتیب معکوس برای نمایش فارسی
            idx = 4 - i
            lbl = ctk.CTkLabel(header_frame, text=fix_text(h), font=self.font_table_header, width=w)
            lbl.pack(side="right", padx=10, fill="y")

        # بدنه جدول (اسکرول)
        self.scroll_table = ctk.CTkScrollableFrame(self.main_panel, label_text="")
        self.scroll_table.pack(fill="both", expand=True)

    def create_kpi_card(self, parent, title, value, col_idx, color):
        frame = ctk.CTkFrame(parent, fg_color=color, height=120, corner_radius=15)
        frame.grid(row=0, column=2-col_idx, sticky="ew", padx=10) # 2-col برای چینش راست به چپ
        frame.pack_propagate(False)
        
        ctk.CTkLabel(frame, text=fix_text(title), font=self.font_card_title, text_color="#aaaaaa").pack(pady=(15,5))
        val_lbl = ctk.CTkLabel(frame, text=value, font=self.font_big_number, text_color="white")
        val_lbl.pack()
        return val_lbl

    def set_today(self):
        now = jdatetime.datetime.now()
        self.ent_y.delete(0,"end"); self.ent_y.insert(0, now.year)
        self.ent_m.delete(0,"end"); self.ent_m.insert(0, now.month)
        self.ent_d.delete(0,"end"); self.ent_d.insert(0, now.day)

    def get_data(self):
        try:
            conn_str = (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER={DB_CONFIG['server']};"
                f"DATABASE={DB_CONFIG['database']};"
                f"UID={DB_CONFIG['username']};"
                f"PWD={DB_CONFIG['password']};"
                "TrustServerCertificate=yes;"
            )
            conn = pyodbc.connect(conn_str)
            query = "SELECT amount, paymentdate FROM payments WHERE paymentType = 'capital_injection' ORDER BY paymentdate"
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        except Exception as e:
            messagebox.showerror(fix_text("خطا در دیتابیس"), str(e))
            return None

    def run_process(self):
        # 1. خواندن تاریخ
        try:
            td = jdatetime.date(int(self.ent_y.get()), int(self.ent_m.get()), int(self.ent_d.get())).togregorian()
        except:
            messagebox.showerror("Error", "تاریخ اشتباه است")
            return

        # 2. خواندن دیتا
        df = self.get_data()
        if df is None: return

        # 3. پاکسازی جدول قدیم
        for widget in self.scroll_table.winfo_children():
            widget.destroy()

        # 4. محاسبات
        total_inv = 0
        total_val = 0
        
        row_idx = 0
        
        for _, row in df.iterrows():
            try:
                # تبدیل تاریخ
                p_date_str = row['paymentdate'] # فرمت 1404/08/12...
                y, m, d = map(int, p_date_str.split(' ')[0].split('/'))
                rec_date = jdatetime.date(y, m, d).togregorian()
                
                amount = float(row['amount'])
                
                # فاصله زمانی
                months_passed = (td - rec_date).days / 30.4375
                
                # اگر واریزی برای آینده است (نسبت به تاریخ هدف) نشان نده یا صفر نشان بده
                if months_passed < 0:
                    continue

                # فرمول جادویی
                growth = (1 + self.effective_monthly_rate) ** months_passed
                future_val = amount * growth
                
                total_inv += amount
                total_val += future_val

                # رسم ردیف در جدول
                self.draw_row(row_idx, p_date_str, amount, months_passed, growth, future_val)
                row_idx += 1
                
            except Exception as e:
                print(f"Error skipping row: {e}")

        # 5. آپدیت کارت‌ها
        self.card_invest.configure(text=format_money(total_inv))
        self.card_value.configure(text=format_money(total_val))
        
        profit = total_val - total_inv
        sign = "+" if profit >= 0 else "-"
        self.card_profit.configure(text=f"{sign} {format_money(abs(profit))}", text_color="#00ff88" if profit>=0 else "red")

    def draw_row(self, idx, date_str, amount, months, growth, f_val):
        # رنگ پس‌زمینه یکی در میان (Zebra Striping)
        bg_color = "#2b2b2b" if idx % 2 == 0 else "#333333"
        
        row_frame = ctk.CTkFrame(self.scroll_table, fg_color=bg_color, corner_radius=5)
        row_frame.pack(fill="x", pady=2)
        
        # ستون‌ها (دقت کنید به ترتیب راست به چپ اضافه نمیکنیم، پک میکنیم به راست)
        # 1. تاریخ (راست)
        ctk.CTkLabel(row_frame, text=date_str, width=150, font=self.font_table_row, anchor="center").pack(side="right", padx=10)
        
        # 2. مبلغ (راست)
        ctk.CTkLabel(row_frame, text=format_money(amount), width=200, font=self.font_table_row, text_color="#aaaaaa", anchor="e").pack(side="right", padx=10)
        
        # 3. مدت (وسط)
        ctk.CTkLabel(row_frame, text=f"{months:.1f}", width=100, font=self.font_table_row, anchor="center").pack(side="right", padx=10)
        
        # 4. ضریب (وسط)
        growth_lbl = f"x {growth:.2f}"
        ctk.CTkLabel(row_frame, text=growth_lbl, width=100, font=self.font_table_row, text_color="#ffcc00", anchor="center").pack(side="right", padx=10)
        
        # 5. ارزش نهایی (چپ)
        ctk.CTkLabel(row_frame, text=format_money(f_val), width=200, font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color="#4ea8de", anchor="w").pack(side="right", padx=10)

if __name__ == "__main__":
    app = ModernFinanceApp()
    app.mainloop()