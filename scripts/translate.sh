#!/bin/bash
# Skills Test Center - Translation Helper Script
# Creates and manages translation files for all supported languages

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Translation Helper Script                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Create translations directory structure
LANGUAGES=("en" "de" "es" "fr" "ar")

for lang in "${LANGUAGES[@]}"; do
    mkdir -p "translations/${lang}/LC_MESSAGES"
done

# Extract translatable strings
pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .

# Initialize translation files
for lang in "${LANGUAGES[@]}"; do
    if [ -f "translations/${lang}/LC_MESSAGES/messages.po" ]; then
        pybabel update -i messages.pot -d translations -l $lang
    else
        pybabel init -i messages.pot -d translations -l $lang
    fi
done

echo "1. Edit translation files in translations/<lang>/LC_MESSAGES/messages.po"
echo "2. Compile: pybabel compile -d translations"
