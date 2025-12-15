/**
 * Skills Test Center - Accessibility & Theme JavaScript
 * Handles dark mode, accessibility features, and user preferences
 */

(function () {
    'use strict';

    // ══════════════════════════════════════════════════════════════
    // THEME MANAGEMENT
    // ══════════════════════════════════════════════════════════════

    const ThemeManager = {
        STORAGE_KEY: 'theme',

        init() {
            // Check saved preference or system preference
            const savedTheme = localStorage.getItem(this.STORAGE_KEY);
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

            if (savedTheme) {
                this.setTheme(savedTheme);
            } else if (systemPrefersDark) {
                this.setTheme('dark');
            }

            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem(this.STORAGE_KEY)) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        },

        setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            document.body.classList.toggle('dark-mode', theme === 'dark');
            localStorage.setItem(this.STORAGE_KEY, theme);

            // Update toggle button icons
            const toggles = document.querySelectorAll('.theme-toggle');
            toggles.forEach(btn => {
                btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
            });
        },

        toggle() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            this.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        },

        getTheme() {
            return document.documentElement.getAttribute('data-theme') || 'light';
        }
    };

    // ══════════════════════════════════════════════════════════════
    // ACCESSIBILITY MANAGEMENT
    // ══════════════════════════════════════════════════════════════

    const AccessibilityManager = {
        STORAGE_KEY: 'accessibility',

        features: {
            highContrast: false,
            largeText: false,
            extraLargeText: false,
            dyslexiaFriendly: false,
            reducedMotion: false,
            colorblindMode: null // 'protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia'
        },

        init() {
            // Load saved preferences
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                this.features = { ...this.features, ...JSON.parse(saved) };
                this.applyFeatures();
            }

            // Check system preference for reduced motion
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                this.features.reducedMotion = true;
                this.applyFeatures();
            }

            // Check system preference for high contrast
            if (window.matchMedia('(prefers-contrast: high)').matches) {
                this.features.highContrast = true;
                this.applyFeatures();
            }
        },

        toggle(feature) {
            if (feature === 'largeText') {
                this.features.largeText = !this.features.largeText;
                this.features.extraLargeText = false;
            } else if (feature === 'extraLargeText') {
                this.features.extraLargeText = !this.features.extraLargeText;
                this.features.largeText = false;
            } else if (feature in this.features) {
                this.features[feature] = !this.features[feature];
            }

            this.applyFeatures();
            this.save();
            return this.features[feature];
        },

        setColorblindMode(mode) {
            this.features.colorblindMode = mode === this.features.colorblindMode ? null : mode;
            this.applyFeatures();
            this.save();
        },

        applyFeatures() {
            const html = document.documentElement;
            const body = document.body;

            // High Contrast
            html.classList.toggle('high-contrast', this.features.highContrast);

            // Large Text
            html.classList.toggle('large-text', this.features.largeText);
            html.classList.toggle('extra-large-text', this.features.extraLargeText);

            // Dyslexia Friendly
            html.classList.toggle('dyslexia-friendly', this.features.dyslexiaFriendly);

            // Reduced Motion
            html.classList.toggle('reduced-motion', this.features.reducedMotion);

            // Colorblind Modes
            ['protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia'].forEach(mode => {
                html.classList.toggle(`colorblind-${mode}`, this.features.colorblindMode === mode);
            });

            // Update toolbar buttons
            this.updateToolbarButtons();
        },

        updateToolbarButtons() {
            document.querySelectorAll('[data-accessibility-toggle]').forEach(btn => {
                const feature = btn.dataset.accessibilityToggle;
                const isActive = this.features[feature];
                btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
                btn.classList.toggle('active', isActive);
            });
        },

        save() {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.features));
        },

        reset() {
            this.features = {
                highContrast: false,
                largeText: false,
                extraLargeText: false,
                dyslexiaFriendly: false,
                reducedMotion: false,
                colorblindMode: null
            };
            this.applyFeatures();
            this.save();
        }
    };

    // ══════════════════════════════════════════════════════════════
    // KEYBOARD NAVIGATION
    // ══════════════════════════════════════════════════════════════

    const KeyboardNavigation = {
        init() {
            // Detect keyboard vs mouse user
            document.body.addEventListener('mousedown', () => {
                document.body.classList.add('using-mouse');
            });

            document.body.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    document.body.classList.remove('using-mouse');
                }
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Alt + A: Toggle accessibility toolbar
                if (e.altKey && e.key === 'a') {
                    e.preventDefault();
                    this.toggleAccessibilityToolbar();
                }

                // Alt + D: Toggle dark mode
                if (e.altKey && e.key === 'd') {
                    e.preventDefault();
                    ThemeManager.toggle();
                }

                // Alt + H: Toggle high contrast
                if (e.altKey && e.key === 'h') {
                    e.preventDefault();
                    AccessibilityManager.toggle('highContrast');
                }

                // Escape: Close modals/dropdowns
                if (e.key === 'Escape') {
                    this.closeOpenElements();
                }
            });
        },

        toggleAccessibilityToolbar() {
            const toolbar = document.getElementById('accessibility-toolbar');
            if (toolbar) {
                const isHidden = toolbar.style.display === 'none';
                toolbar.style.display = isHidden ? 'flex' : 'none';

                // Announce to screen readers
                this.announce(isHidden ? 'Accessibility toolbar opened' : 'Accessibility toolbar closed');
            }
        },

        closeOpenElements() {
            // Close Bootstrap dropdowns
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });

            // Close modals
            const modal = document.querySelector('.modal.show');
            if (modal && window.bootstrap) {
                bootstrap.Modal.getInstance(modal)?.hide();
            }
        },

        announce(message) {
            const announcer = document.getElementById('a11y-announcer') || this.createAnnouncer();
            announcer.textContent = message;
        },

        createAnnouncer() {
            const announcer = document.createElement('div');
            announcer.id = 'a11y-announcer';
            announcer.setAttribute('aria-live', 'polite');
            announcer.setAttribute('aria-atomic', 'true');
            announcer.className = 'sr-only';
            document.body.appendChild(announcer);
            return announcer;
        }
    };

    // ══════════════════════════════════════════════════════════════
    // GLOBAL FUNCTIONS
    // ══════════════════════════════════════════════════════════════

    window.toggleTheme = function () {
        ThemeManager.toggle();
    };

    window.toggleAccessibility = function (feature) {
        return AccessibilityManager.toggle(feature);
    };

    window.setColorblindMode = function (mode) {
        AccessibilityManager.setColorblindMode(mode);
    };

    window.resetAccessibility = function () {
        AccessibilityManager.reset();
    };

    // ══════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ══════════════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', function () {
        ThemeManager.init();
        AccessibilityManager.init();
        KeyboardNavigation.init();

        console.log('Accessibility features loaded');
    });

})();
