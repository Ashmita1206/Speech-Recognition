"""
Unit & Integration Tests for Translation Feature
=================================================
Validates:
  1. GET /languages endpoint.
  2. POST /translate endpoint with various languages.
  3. POST /translate error handling (unsupported language, empty inputs).
  4. Natural voice translation command detection.
  5. UI template contains all necessary translation components.
"""

import unittest
from app import app
from utils.translator import (
    translate_text,
    detect_translation_command,
    resolve_language,
    get_supported_languages,
)

class TranslationFeatureTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_get_languages(self):
        """Verify /languages endpoint returns all required languages."""
        response = self.client.get('/languages')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        langs = data['languages']
        required = [
            'English', 'Hindi', 'Spanish', 'French', 'German',
            'Japanese', 'Korean', 'Chinese', 'Arabic', 'Punjabi',
            'Bengali', 'Marathi', 'Gujarati', 'Tamil', 'Telugu',
            'Kannada', 'Malayalam'
        ]
        for req in required:
            self.assertIn(req, langs, f"Missing required language: {req}")

    def test_voice_command_detection(self):
        """Test natural language voice command detection."""
        test_cases = [
            ("Translate this into English.", "English"),
            ("Translate this to Hindi.", "Hindi"),
            ("Translate my last transcription into Hindi.", "Hindi"),
            ("Convert this to Spanish.", "Spanish"),
            ("Give me the Hindi translation.", "Hindi"),
            ("Give me the translation in French", "French"),
            ("Translate to German", "German"),
            ("Translate into Japanese!", "Japanese"),
            ("How do you say this in Arabic?", "Arabic"),
        ]
        for text, expected_lang in test_cases:
            cmd = detect_translation_command(text)
            self.assertIsNotNone(cmd, f"Failed to detect voice command for: {text}")
            self.assertEqual(cmd['target_language'], expected_lang)

        # Normal speech must NOT trigger voice command
        regular_speech = [
            "Good morning everyone, welcome to my presentation.",
            "I have an exam tomorrow.",
            "Hello world.",
            "Please turn on the light.",
        ]
        for text in regular_speech:
            cmd = detect_translation_command(text)
            self.assertIsNone(cmd, f"False positive command detection for: {text}")

    def test_translate_endpoint_success(self):
        """Test POST /translate endpoint with Hindi and Spanish."""
        # 1. English to Hindi
        res = self.client.post('/translate', json={
            'text': 'Good morning everyone',
            'target_language': 'Hindi'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['source_text'], 'Good morning everyone')
        self.assertTrue(len(data['translated_text']) > 0)
        self.assertEqual(data['target_language'], 'Hindi')

        # 2. English to Spanish
        res = self.client.post('/translate', json={
            'text': 'I have an exam tomorrow.',
            'target_language': 'Spanish'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('examen', data['translated_text'].lower())

    def test_translate_endpoint_errors(self):
        """Test POST /translate validation and friendly error handling."""
        # Empty text
        res = self.client.post('/translate', json={'text': '', 'target_language': 'Hindi'})
        self.assertEqual(res.status_code, 400)

        # Missing target_language
        res = self.client.post('/translate', json={'text': 'Hello', 'target_language': ''})
        self.assertEqual(res.status_code, 400)

        # Unsupported language
        res = self.client.post('/translate', json={'text': 'Hello', 'target_language': 'Atlantian123'})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], "That language isn't currently supported.")

    def test_frontend_contains_translation_elements(self):
        """Verify that index.html serves the translation prompt, selector, and display."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('translation-offer-box', html)
        self.assertIn('Would you like me to translate this?', html)
        self.assertIn('btn-offer-translate', html)
        self.assertIn('btn-offer-skip', html)
        self.assertIn('translation-selector-box', html)
        self.assertIn('target-language-select', html)
        self.assertIn('translation-display-card', html)
        self.assertIn('btn-copy-translation', html)
        self.assertIn('btn-download-translation', html)
        self.assertIn('btn-listen-translation', html)
        self.assertIn('trans-original-content', html)
        self.assertIn('trans-target-content', html)

if __name__ == '__main__':
    unittest.main()
