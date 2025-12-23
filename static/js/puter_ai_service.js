/**
 * Puter.js AI Service for Skills Test Center
 * Free Gemini AI access without API keys
 * 
 * Features:
 * - Speaking response evaluation (IELTS criteria)
 * - Writing assessment
 * - Grammar checking
 * - Vocabulary analysis
 */

const PuterAI = {
    /**
     * Check if Puter.js is available
     */
    isAvailable: function () {
        return typeof puter !== 'undefined' && puter.ai;
    },

    /**
     * Evaluate speaking response using IELTS criteria
     * @param {string} transcript - The transcribed speech text
     * @param {string} question - The original question
     * @returns {Promise<Object>} Scores and feedback
     */
    evaluateSpeaking: async function (transcript, question) {
        if (!this.isAvailable()) {
            console.warn('Puter.js not available, using fallback scoring');
            return this.getFallbackScores();
        }

        const prompt = `You are an expert IELTS speaking examiner. Evaluate the following speaking response.

Question: ${question}

Response transcript: ${transcript}

Provide a JSON response with these exact fields (scores 0-9 in 0.5 increments):
{
    "fluency": <number>,
    "pronunciation": <number>,
    "grammar": <number>,
    "vocabulary": <number>,
    "overall": <number>,
    "cefr_level": "<A1|A2|B1|B2|C1|C2>",
    "feedback": "<2-3 sentences of constructive feedback in Turkish>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "improvements": ["<area to improve 1>", "<area to improve 2>"]
}

Return ONLY the JSON, no other text.`;

        try {
            const response = await puter.ai.chat(prompt);

            // Parse the JSON response
            let result;
            try {
                // Extract JSON from response if wrapped in markdown
                const jsonMatch = response.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    result = JSON.parse(jsonMatch[0]);
                } else {
                    result = JSON.parse(response);
                }
            } catch (parseError) {
                console.error('JSON parse error:', parseError);
                return this.getFallbackScores();
            }

            // Validate and normalize scores
            return {
                fluency: this.normalizeScore(result.fluency),
                pronunciation: this.normalizeScore(result.pronunciation),
                grammar: this.normalizeScore(result.grammar),
                vocabulary: this.normalizeScore(result.vocabulary),
                overall: this.normalizeScore(result.overall),
                cefr_level: result.cefr_level || 'B1',
                feedback: result.feedback || 'Değerlendirme tamamlandı.',
                strengths: result.strengths || [],
                improvements: result.improvements || []
            };
        } catch (error) {
            console.error('Puter AI error:', error);
            return this.getFallbackScores();
        }
    },

    /**
     * Evaluate writing response
     * @param {string} text - The written text
     * @param {string} prompt - The writing prompt
     * @param {string} type - Essay type (task1, task2, etc.)
     * @returns {Promise<Object>} Scores and feedback
     */
    evaluateWriting: async function (text, prompt, type = 'task2') {
        if (!this.isAvailable()) {
            return this.getFallbackScores();
        }

        const evaluationPrompt = `You are an expert IELTS writing examiner. Evaluate the following ${type} writing response.

Task/Prompt: ${prompt}

Student's response:
${text}

Word count: ${text.split(/\s+/).length}

Provide a JSON response with these exact fields (scores 0-9 in 0.5 increments):
{
    "task_achievement": <number>,
    "coherence_cohesion": <number>,
    "lexical_resource": <number>,
    "grammatical_range": <number>,
    "overall": <number>,
    "cefr_level": "<A1|A2|B1|B2|C1|C2>",
    "feedback": "<2-3 sentences of constructive feedback in Turkish>",
    "grammar_errors": ["<error 1>", "<error 2>"],
    "vocabulary_suggestions": ["<suggestion 1>", "<suggestion 2>"]
}

Return ONLY the JSON, no other text.`;

        try {
            const response = await puter.ai.chat(evaluationPrompt);

            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                const result = JSON.parse(jsonMatch[0]);
                return {
                    task_achievement: this.normalizeScore(result.task_achievement),
                    coherence_cohesion: this.normalizeScore(result.coherence_cohesion),
                    lexical_resource: this.normalizeScore(result.lexical_resource),
                    grammatical_range: this.normalizeScore(result.grammatical_range),
                    overall: this.normalizeScore(result.overall),
                    cefr_level: result.cefr_level || 'B1',
                    feedback: result.feedback || 'Değerlendirme tamamlandı.',
                    grammar_errors: result.grammar_errors || [],
                    vocabulary_suggestions: result.vocabulary_suggestions || []
                };
            }
            return this.getFallbackWritingScores();
        } catch (error) {
            console.error('Puter AI writing error:', error);
            return this.getFallbackWritingScores();
        }
    },

    /**
     * Get CEFR level from ability score
     * @param {number} ability - Ability score (-3 to +3)
     * @returns {string} CEFR level
     */
    getCEFRLevel: function (ability) {
        if (ability <= -2) return 'A1';
        if (ability <= -1) return 'A2';
        if (ability <= 0) return 'B1';
        if (ability <= 1) return 'B2';
        if (ability <= 2) return 'C1';
        return 'C2';
    },

    /**
     * Normalize score to 0-9 range with 0.5 increments
     * @param {number} score - Raw score
     * @returns {number} Normalized score
     */
    normalizeScore: function (score) {
        if (typeof score !== 'number' || isNaN(score)) return 5;
        const normalized = Math.max(0, Math.min(9, score));
        return Math.round(normalized * 2) / 2; // Round to nearest 0.5
    },

    /**
     * Fallback scores when AI is unavailable
     * @returns {Object} Default scores
     */
    getFallbackScores: function () {
        return {
            fluency: 5,
            pronunciation: 5,
            grammar: 5,
            vocabulary: 5,
            overall: 5,
            cefr_level: 'B1',
            feedback: 'AI değerlendirmesi şu an kullanılamıyor. Skorlar tahminidir.',
            strengths: [],
            improvements: []
        };
    },

    /**
     * Fallback writing scores
     * @returns {Object} Default writing scores
     */
    getFallbackWritingScores: function () {
        return {
            task_achievement: 5,
            coherence_cohesion: 5,
            lexical_resource: 5,
            grammatical_range: 5,
            overall: 5,
            cefr_level: 'B1',
            feedback: 'AI değerlendirmesi şu an kullanılamıyor.',
            grammar_errors: [],
            vocabulary_suggestions: []
        };
    },

    /**
     * Quick grammar check
     * @param {string} text - Text to check
     * @returns {Promise<Object>} Grammar analysis
     */
    checkGrammar: async function (text) {
        if (!this.isAvailable()) {
            return { errors: [], suggestions: [] };
        }

        const prompt = `Check the following English text for grammar errors. Return a JSON with:
{
    "errors": [{"original": "...", "correction": "...", "explanation": "..."}],
    "suggestions": ["..."],
    "is_correct": true/false
}

Text: ${text}

Return ONLY JSON.`;

        try {
            const response = await puter.ai.chat(prompt);
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        } catch (error) {
            console.error('Grammar check error:', error);
        }
        return { errors: [], suggestions: [], is_correct: true };
    },

    /**
     * Transcribe audio using browser's Web Speech API
     * (Puter.js doesn't have audio transcription, so we use native API)
     * @returns {Promise<string>} Transcribed text
     */
    startTranscription: function () {
        return new Promise((resolve, reject) => {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                reject(new Error('Speech recognition not supported'));
                return;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();

            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            let finalTranscript = '';

            recognition.onresult = (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + ' ';
                    }
                }
            };

            recognition.onend = () => {
                resolve(finalTranscript.trim());
            };

            recognition.onerror = (event) => {
                reject(event.error);
            };

            recognition.start();

            // Store reference for stopping
            window.currentRecognition = recognition;
        });
    },

    /**
     * Stop ongoing transcription
     */
    stopTranscription: function () {
        if (window.currentRecognition) {
            window.currentRecognition.stop();
        }
    }
};

// Export for use in other scripts
window.PuterAI = PuterAI;

// Log availability on load
document.addEventListener('DOMContentLoaded', function () {
    if (PuterAI.isAvailable()) {
        console.log('✅ Puter.js AI is available for free Gemini access');
    } else {
        console.warn('⚠️ Puter.js not loaded - AI features may be limited');
    }
});
