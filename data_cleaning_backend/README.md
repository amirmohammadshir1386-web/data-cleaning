# راهنمای اجرای وب‌سرویس بک‌اند پالایش داده‌های متنی فارسی (Backend API)

این بک‌اند بر پایه فریم‌ورک سریع و مدرن **FastAPI** و با استفاده از معماری و منطق پردازشی پروژه **amirmohammadshir1386-web/data-cleaning** پیاده‌سازی شده است.

---

## 🚀 نحوه نصب و اجرا

### ۱. نصب وابستگی‌ها
ابتدا یک محیط مجازی (Virtual Environment) ایجاد کرده و پکیج‌ها را نصب کنید:

```bash
# ساخت و فعال‌سازی محیط مجازی
python -m venv venv
source venv/bin/activate  # در ویندوز: venv\Scripts\activate

# نصب پکیج‌ها
pip install -r requirements.txt
```

### ۲. اجرای سرور
برای اجرای سرور به صورت زنده (Live Reload):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
یا به سادگی اجرای مستقیم فایل پایتون:
```bash
python main.py
```

پس از اجرا، سرور روی آدرس `http://localhost:8000` در دسترس خواهد بود.

---

## 📖 مستندات تعاملی API (Swagger / OpenAPI)

FastAPI به صورت خودکار مستندات کامل و امکان تست زنده تمام روت‌ها را فراهم می‌کند:
* **مستندات Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **مستندات ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 روت‌ها و اندپوینت‌های اصلی

| روش | مسیر (Endpoint) | توضیحات |
| :--- | :--- | :--- |
| `GET` | `/` | بررسی وضعیت سلامت سرور و متادیتا |
| `POST` | `/api/v1/clean` | دریافت متن خام و تنظیمات، و بازگرداندن متن پالایش‌شده |
| `POST` | `/api/v1/upload` | آپلود مستقیم فایل (`.txt`, `.csv`, `.json`) و پاک‌سازی آن |
| `POST` | `/api/v1/analyze` | تحلیل آماری جامع پیکره (معادل `analyzer.py`) |
| `POST` | `/api/v1/export/csv` | دانلود خروجی به صورت فایل `final.csv` (با UTF-8 BOM) |
| `POST` | `/api/v1/export/report` | دانلود گزارش تحلیلی در قالب `analyzer.txt` |

---

## 🔌 نحوه اتصال به فرانت‌اند (index.html)

فرانت‌اند ساخته شده می‌تواند درخواست‌های پاک‌سازی را به صورت زنده به این آدرس ارسال کند:

```javascript
// نمونه کد فراخوانی در جاوااسکریپت:
const response = await fetch("http://localhost:8000/api/v1/clean", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "متن خام شما...",
    options: {
      normalize_chars: true,
      semi_space: true,
      deduplicate: true,
      filter_short: true
    }
  })
});
const result = await response.json();
console.log(result.cleaned_text);
```
