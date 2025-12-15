# 🎓 Skills Test Center

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)

**Professional English Proficiency Assessment Platform with CEFR Scoring**

[Demo](#demo) • [Features](#features) • [Installation](#installation) • [Documentation](#documentation)

</div>

---

## 🌟 Features

### 📝 Comprehensive Testing
- **4 Skills Assessment**: Reading, Listening, Writing, Speaking
- **Adaptive Testing (CAT)**: AI-powered question selection
- **CEFR Scoring**: A1-C2 level determination
- **IELTS/TOEFL Equivalent Scores**: International score mapping

### 🔐 Security
- **Two-Factor Authentication (2FA)**: TOTP-based authenticator app support
- **Account Lockout**: Protection against brute-force attacks
- **Strong Password Policy**: Configurable password requirements
- **Webhook Signatures**: Secure external integrations

### 💳 Payment Integration
- **Iyzico**: Turkish market payment processing
- **Stripe**: International payment support
- **Credit System**: Prepaid exam credits for companies

### 🌍 Multi-Language Support
- 🇹🇷 Türkçe (Default)
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇪🇸 Español
- 🇫🇷 Français
- 🇸🇦 العربية (RTL Support)

### ♿ Accessibility
- **WCAG 2.1 Compliant**: Screen reader compatible
- **High Contrast Mode**: For visually impaired users
- **Large Text Mode**: Adjustable font sizes
- **Keyboard Navigation**: Full keyboard support
- **Dyslexia-Friendly Font**: OpenDyslexic option
- **Reduced Motion**: For motion-sensitive users

### 🎨 Themes
- **Light Mode**: Default bright theme
- **Dark Mode**: Eye-friendly dark theme
- **System Preference**: Auto-detect OS theme

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (optional, for assets)

### Installation

```bash
# Clone the repository
git clone https://github.com/ayyildizemrah88/ingilizcetesti.git
cd ingilizcetesti

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
flask init-db
flask create-superadmin
flask run --debug
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# Initialize database
docker-compose exec web flask init-db
docker-compose exec web flask create-superadmin

# View logs
docker-compose logs -f
```

---

## 📁 Project Structure

```
skillstestcenter/
├── app/                    # Main application
│   ├── models/            # Database models
│   ├── routes/            # API routes & views
│   ├── tasks/             # Celery async tasks
│   ├── utils/             # Utility modules
│   └── i18n.py            # Internationalization
├── templates/              # Jinja2 templates
├── static/                 # Static assets
├── translations/           # Language files
├── tests/                  # Unit tests
├── scripts/                # Utility scripts
├── Dockerfile              # Container config
├── docker-compose.yml      # Multi-container setup
└── DEPLOYMENT.md           # Deployment guide
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

---

## 🔧 Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key (64+ chars) | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `GEMINI_API_KEY` | Google AI for speaking/writing | ✅ |
| `SENDGRID_API_KEY` | Email service | ✅ |
| `IYZICO_API_KEY` | Turkish payment gateway | Optional |
| `STRIPE_SECRET_KEY` | International payments | Optional |

---

## 📖 Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](http://localhost:5000/apidocs) (Swagger UI)
- [Translation Guide](scripts/translate.sh)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 📞 Support

For support and inquiries:
- 📧 Email: support@skillstestcenter.com
- 🌐 Website: https://skillstestcenter.com

---

<div align="center">

**Made with ❤️ for better English assessment**

</div>
