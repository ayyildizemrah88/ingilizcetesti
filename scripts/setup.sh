#!/bin/bash
# Skills Test Center - Automated Setup Script
# Usage: chmod +x scripts/setup.sh && ./scripts/setup.sh

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Skills Test Center - Automated Setup Script            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Not running as root. Some commands may fail.${NC}"
fi

# ══════════════════════════════════════════════════════════════
# 1. CHECK PREREQUISITES
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[1/7] Checking prerequisites...${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python: $PYTHON_VERSION"
else
    echo -e "${RED}❌ Python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 installed"
else
    echo -e "${RED}❌ pip3 not found${NC}"
    exit 1
fi

# Check Redis (optional but recommended)
if command -v redis-cli &> /dev/null; then
    echo "✅ Redis installed"
else
    echo -e "${YELLOW}⚠️  Redis not found. Celery tasks won't work without Redis.${NC}"
fi

# ══════════════════════════════════════════════════════════════
# 2. CREATE VIRTUAL ENVIRONMENT
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[2/7] Setting up virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"

# Upgrade pip
pip install --upgrade pip --quiet
echo "✅ pip upgraded"

# ══════════════════════════════════════════════════════════════
# 3. INSTALL DEPENDENCIES
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[3/7] Installing dependencies...${NC}"

pip install -r requirements.txt --quiet
echo "✅ All dependencies installed"

# ══════════════════════════════════════════════════════════════
# 4. CREATE .ENV FILE
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[4/7] Setting up environment...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Generate SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Replace placeholder in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-64-character-secret-key-change-this-in-production/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-64-character-secret-key-change-this-in-production/$SECRET_KEY/" .env
    fi
    
    echo "✅ .env file created with generated SECRET_KEY"
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys:${NC}"
    echo "   - DATABASE_URL"
    echo "   - GEMINI_API_KEY"
    echo "   - SENDGRID_API_KEY"
    echo "   - IYZICO_API_KEY / STRIPE_SECRET_KEY"
else
    echo "✅ .env file already exists"
fi

# ══════════════════════════════════════════════════════════════
# 5. INITIALIZE DATABASE
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[5/7] Initializing database...${NC}"

# Set Flask app
export FLASK_APP=run.py

# Try Flask-Migrate first, fallback to init-db
if flask db upgrade 2>/dev/null; then
    echo "✅ Database migrated with Flask-Migrate"
else
    flask init-db 2>/dev/null || echo -e "${YELLOW}⚠️  Database initialization skipped (configure DATABASE_URL first)${NC}"
fi

# ══════════════════════════════════════════════════════════════
# 6. CREATE SUPERADMIN
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[6/7] SuperAdmin setup...${NC}"

echo -e "${YELLOW}Would you like to create a SuperAdmin user now? (y/n)${NC}"
read -r CREATE_ADMIN

if [ "$CREATE_ADMIN" = "y" ] || [ "$CREATE_ADMIN" = "Y" ]; then
    flask create-superadmin
else
    echo "Skipped. Run 'flask create-superadmin' later to create admin."
fi

# ══════════════════════════════════════════════════════════════
# 7. FINAL CHECKS
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}[7/7] Running final checks...${NC}"

# Show config status
flask show-config 2>/dev/null || echo "Config check skipped"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE! 🎉                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: flask run --debug"
echo "  4. Open: http://localhost:5000"
echo ""
echo "For production deployment, see DEPLOYMENT.md"
