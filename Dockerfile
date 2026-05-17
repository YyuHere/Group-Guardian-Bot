FROM python:3.11-slim

# تثبيت الـ ffmpeg وأدوات بناء السيرفر الأساسية
RUN apt-get update && apt-get install -y ffmpeg build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ وتثبيت المكتبات بالنسخ المستقرة
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# أمر تشغيل البوت الأساسي
CMD ["python", "main.py"]
