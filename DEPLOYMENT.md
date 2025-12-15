# Skills Test Center - Deployment Guide

Bu doküman, Skills Test Center uygulamasını production ortamına deploy etme adımlarını içerir.

## 📋 Gereksinimler

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Nginx (reverse proxy)
- Let's Encrypt (SSL)

---

## 1️⃣ Sunucu Hazırlığı

### 1.1 Sistem Paketleri

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 1.2 PostgreSQL Kurulumu

```bash
sudo -u postgres psql

CREATE USER skillstest WITH PASSWORD 'your-secure-password';
CREATE DATABASE skillstest_db OWNER skillstest;
GRANT ALL PRIVILEGES ON DATABASE skillstest_db TO skillstest;
\q
```

---

## 2️⃣ Uygulama Kurulumu

### 2.1 Proje Klonlama

```bash
cd /var/www
sudo git clone https://github.com/ayyildizemrah88/ingilizcetesti.git skillstestcenter
sudo chown -R www-data:www-data skillstestcenter
cd skillstestcenter
```

### 2.2 Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3️⃣ Environment Değişkenleri

### 3.1 .env Dosyası Oluşturma

```bash
nano .env
```

### 3.2 .env İçeriği

```env
# Flask Configuration
FLASK_ENV=production
FLASK_APP=run.py

# Security - MUTLAKA DEĞİŞTİRİN!
SECRET_KEY=your-64-character-random-string-here-generate-with-flask-command

# Database
DATABASE_URL=postgresql://skillstest:your-secure-password@localhost:5432/skillstest_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Email Service
SENDGRID_API_KEY=your-sendgrid-api-key

# Error Tracking
SENTRY_DSN=your-sentry-dsn
APP_VERSION=2.0.0

# Google Drive Backup (Opsiyonel)
ENABLE_GOOGLE_DRIVE_BACKUP=true
GOOGLE_APPLICATION_CREDENTIALS=/var/www/skillstestcenter/google-credentials.json
GOOGLE_DRIVE_BACKUP_FOLDER_ID=your-drive-folder-id

# Backup Settings
BACKUP_DIR=/var/www/skillstestcenter/backups
BACKUP_KEEP_DAYS=7
```

### 3.3 SECRET_KEY Üretimi

```bash
source venv/bin/activate
flask generate-secret-key
# Çıktıdaki key'i .env dosyasına yapıştırın
```

---

## 4️⃣ Veritabanı Kurulumu

```bash
source venv/bin/activate

# Tabloları oluştur
flask init-db

# İlk superadmin oluştur
flask create-superadmin
# Email: admin@yourcompany.com
# Password: (güçlü bir şifre)
# Full Name: System Admin
```

---

## 5️⃣ Gunicorn Servisi

### 5.1 Gunicorn Config

```bash
nano gunicorn.conf.py
```

```python
# gunicorn.conf.py
bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

### 5.2 Systemd Service

```bash
sudo nano /etc/systemd/system/skillstest.service
```

```ini
[Unit]
Description=Skills Test Center Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/skillstestcenter
Environment="PATH=/var/www/skillstestcenter/venv/bin"
EnvironmentFile=/var/www/skillstestcenter/.env
ExecStart=/var/www/skillstestcenter/venv/bin/gunicorn -c gunicorn.conf.py run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/log/gunicorn

sudo systemctl daemon-reload
sudo systemctl enable skillstest
sudo systemctl start skillstest
sudo systemctl status skillstest
```

---

## 6️⃣ Celery Worker & Beat

### 6.1 Celery Worker Service

```bash
sudo nano /etc/systemd/system/skillstest-celery.service
```

```ini
[Unit]
Description=Skills Test Center Celery Worker
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/skillstestcenter
Environment="PATH=/var/www/skillstestcenter/venv/bin"
EnvironmentFile=/var/www/skillstestcenter/.env
ExecStart=/var/www/skillstestcenter/venv/bin/celery -A app.celery_app:celery worker --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.2 Celery Beat Service

```bash
sudo nano /etc/systemd/system/skillstest-celerybeat.service
```

```ini
[Unit]
Description=Skills Test Center Celery Beat
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/skillstestcenter
Environment="PATH=/var/www/skillstestcenter/venv/bin"
EnvironmentFile=/var/www/skillstestcenter/.env
ExecStart=/var/www/skillstestcenter/venv/bin/celery -A app.celery_app:celery beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable skillstest-celery skillstest-celerybeat
sudo systemctl start skillstest-celery skillstest-celerybeat
```

---

## 7️⃣ Nginx Yapılandırması

```bash
sudo nano /etc/nginx/sites-available/skillstestcenter
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    location /static {
        alias /var/www/skillstestcenter/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /var/www/skillstestcenter/uploads;
        expires 7d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/skillstestcenter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7.1 SSL Sertifikası

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 8️⃣ Google Drive Backup Kurulumu (Opsiyonel)

### 8.1 Google Cloud Console

1. https://console.cloud.google.com adresine gidin
2. Yeni proje oluşturun
3. "APIs & Services" > "Enable APIs" > "Google Drive API" etkinleştirin
4. "Credentials" > "Create Credentials" > "Service Account"
5. JSON key indirin

### 8.2 Service Account Key Yükleme

```bash
# JSON dosyasını sunucuya yükleyin
scp google-credentials.json user@server:/var/www/skillstestcenter/

# İzinleri ayarlayın
sudo chown www-data:www-data /var/www/skillstestcenter/google-credentials.json
sudo chmod 600 /var/www/skillstestcenter/google-credentials.json
```

### 8.3 Google Drive Klasör Paylaşımı

- Google Drive'da bir klasör oluşturun
- Klasörü Service Account email'i ile paylaşın (Editor yetkisi)
- Klasör ID'sini .env'e ekleyin

---

## 9️⃣ Günlük Bakım Komutları

```bash
# Servis durumu kontrolü
sudo systemctl status skillstest skillstest-celery skillstest-celerybeat

# Logları izleme
sudo journalctl -u skillstest -f
sudo tail -f /var/log/gunicorn/error.log

# Manuel backup tetikleme
cd /var/www/skillstestcenter
source venv/bin/activate
flask run-backup

# Konfigürasyon kontrolü
flask show-config

# Yeni admin ekleme
flask create-admin
```

---

## 🔒 Güvenlik Kontrol Listesi

- [ ] SECRET_KEY 64+ karakter ve benzersiz
- [ ] PostgreSQL şifresi güçlü
- [ ] .env dosyası 600 izinli
- [ ] SSL sertifikası aktif
- [ ] Firewall sadece 80/443 açık
- [ ] Redis sadece localhost'tan erişilebilir
- [ ] Sentry kurulu ve aktif
- [ ] Günlük backup aktif

---

## ❓ Sorun Giderme

### Uygulama başlamıyor
```bash
sudo journalctl -u skillstest -n 50
source venv/bin/activate && flask show-config
```

### Celery task'ları çalışmıyor
```bash
redis-cli ping  # "PONG" dönmeli
sudo systemctl restart skillstest-celery
```

### 502 Bad Gateway
```bash
sudo systemctl restart skillstest
sudo nginx -t && sudo systemctl reload nginx
```
