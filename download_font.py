# download_fonts.py
import urllib.request
import os

def download_file(url, filename):
    print(f"در حال دانلود {filename}...")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"✅ {filename} با موفقیت دانلود شد.")
    except Exception as e:
        print(f"❌ خطا در دانلود {filename}: {e}")

# لینک‌های مستقیم فونت وزیر
fonts = {
    "Vazir.ttf": "https://github.com/rastikerdar/vazir-font/raw/master/dist/Vazir.ttf",
    "Vazir-Bold.ttf": "https://github.com/rastikerdar/vazir-font/raw/master/dist/Vazir-Bold.ttf"
}

if __name__ == "__main__":
    print("--- شروع دانلود فونت‌های فارسی ---")
    for name, link in fonts.items():
        if not os.path.exists(name):
            download_file(link, name)
        else:
            print(f"ℹ️ فایل {name} از قبل وجود دارد.")
    print("\n--- پایان. حالا می‌توانید گزارش بگیرید. ---")
