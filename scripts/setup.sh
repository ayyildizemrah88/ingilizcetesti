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

# [Tam içerik yukarıda - 166 satır]
