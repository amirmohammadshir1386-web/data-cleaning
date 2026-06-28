import pandas as pd
import extractor as ex
from cleaner import is_sen

ex.runer()
for chunk in pd.read_csv('extracted.csv', chunksize=10000, quoting=3, on_bad_lines='skip'):
    for line in chunk:
        if is_sen(line)[0]:
            line = is_sen(line)[1]
        else:
            line = ""

        # بار اول
        chunk.to_csv('clean.csv', index=False, mode='w', header=True)

        # بقیه chunk ها
        chunk.to_csv('clean.csv', index=False, mode='a', header=False)

def remove_duplicates_with_pandas(secondary_path, final_path):
    print("\n⏳ فاز ۲: در حال بارگذاری فایل ثانویه در پانداز برای حذف تکراری‌ها...")

    # حالا پانداز یک فایل بسیار سبکِ تک‌ستونه را بدون هیچ اروری می‌خواند
    df = pd.read_csv(secondary_path, names=['text'], header=None)

    # حذف توییت‌های دابلیکیت
    print("🧹 در حال پردازش و حذف دابلیکیت‌ها...")
    df_unique = df.drop_duplicates(subset=['text'])

    print(f"📊 آمار نهایی:")
    print(f"🔹 کل توییت‌های استخراج شده: {len(df)}")
    print(f"🔸 توییت‌های یکتا و غیرتکراری: {len(df_unique)}")

    # ذخیره فایل نهایی کاملاً تمیز برای ادامه پروژه (هاضم و فرآیندهای بعدی)
    df_unique.to_csv(final_path, index=False, header=['text'], encoding='utf-8')
    print(f"🎉 فایل نهایی و یکتا در '{final_path}' ذخیره شد.")
