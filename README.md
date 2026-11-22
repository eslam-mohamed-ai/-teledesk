# TeleDesk Backend

## التشغيل (Windows / Mac / Linux)
```bash
# 1) الأساسيات (Postgres + Redis + MinIO)
docker compose up -d

# 2) المفاتيح
cp .env.example .env        # وبعدين املا GEMINI_API_KEY و ENCRYPTION_KEY

# 3) المكتبات
cd backend
python -m venv venv
venv\Scripts\activate       # Windows  |  source venv/bin/activate  (Mac/Linux)
pip install -r requirements.txt

# 4) الـ Backend (Terminal 1)
uvicorn app.main:app --reload

# 5) الـ Worker (Terminal 2)  -- على Windows لازم --pool=solo
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# 6) النفق لتليجرام (Terminal 3)
ngrok http 8000             # حط عنوان https في PUBLIC_BASE_URL وأعد تشغيل uvicorn
```
افتح http://localhost:8000/docs لتجربة الـ API.

## تجربة سريعة من /docs
1. `POST /api/auth/demo` ← خد الـ token ← Authorize (Bearer).
2. `POST /api/documents/text` ← ضيف سياسة أو أسعار، وانتظر حالة `ready` في `GET /api/documents`.
3. `POST /api/bots/test` {"question": "..."} ← جرّب الرد من غير تليجرام.
4. `POST /api/bots/connect` بتوكن من @BotFather ← ابعت رسالة للبوت.

## الاختبارات
```bash
pip install -r backend/requirements-dev.txt
make test
```

## قاعدة البيانات والترحيلات
- `make migrate` يطبق ترحيلات Alembic على قاعدة البيانات المحددة في `.env`.
- `docker compose up` يشغّل خدمة `migrate` قبل الـ API والـ worker.
- عند استخدام قاعدة موجودة من إصدار سابق، افحص الـ schema وخذ نسخة احتياطية
  قبل ختم baseline؛ الأمر لا ينشئ الجداول أو يتحقق منها:
  `make stamp-existing CONFIRM_EXISTING_SCHEMA=yes`

## ملاحظات قبل الإطلاق التجاري
- Gemini المجاني: Google ممكن تستخدم البيانات، فانقل للخطة المدفوعة.
- `POST /api/billing/plan` بيغيّر الخطة من غير دفع (للتطوير بس). اربط Stripe/Paymob.
- تغييرات الـ schema تُدار بترحيلات Alembic؛ التطبيق لا ينشئ الجداول عند التشغيل.
