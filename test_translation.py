"""
Unit & Integration Tests for Speech Recognition & Translation Feature
======================================================================
Validates all requirements:
  - Test A: Hindi transcription (Devanagari script consistency, no Urdu/Roman mixing)
  - Test B: Hindi to English translation ("मुझे एक कप चाय पीनी है।" -> "I want to have a cup of tea.")
  - Test C: English to Hindi translation ("I need to drink a cup of tea." -> "मुझे एक कप चाय पीनी है।")
  - Test D: English to Spanish translation ("Good morning." -> "Buenos días.")
  - Test E: Changing language (fresh translation of original sentence)
  - Test F: Translation failure returns clear error without returning input unchanged
  - Test G: Regression verification of /transcribe and original transcript preservation
  - Endpoint security tests: OS command execution gate, 403 Forbidden, token expiration
  - Upload validation tests: Missing files, empty filenames, unsupported extensions
  - Model lifecycle verification: Real model name tracking
"""

import os
import unittest
from unittest.mock import patch
from app import app
from utils.translator import (
    translate_text,
    detect_translation_command,
    resolve_language,
    get_supported_languages,
)
from utils.script_normalizer import (
    normalize_hindi_script,
    normalize_transcript,
)
from utils.predict import transcribe_audio, get_loaded_model_name
from utils.commands import detect_command, execute_command, confirm_and_execute


class TranslationFeatureUnitTests(unittest.TestCase):
    """
    Fast automated unit and route tests.
    Zero model weights downloaded. Validates text translation,
    script normalization, route errors, UI templates, and security gates.
    """

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

    # =========================================================================
    # User Request Specified Test Cases A through G (Unit / Text / Route)
    # =========================================================================

    def test_test_a_hindi_script_normalization(self):
        """
        Test A — Hindi script normalization (Fast unit test)
        Input: Hindi speech transcribed in Roman Hinglish or Urdu.
        Expected: A readable Hindi transcript in Devanagari, without unintended Urdu/Roman mixing.
        """
        # Test script normalization directly on Hinglish and Urdu inputs
        norm_hinglish = normalize_transcript("Mujhe ek cup chai peeni hai.", detected_language="hi")
        self.assertIn("मुझे", norm_hinglish)
        self.assertIn("चाय", norm_hinglish)
        self.assertIn("पीनी", norm_hinglish)
        self.assertIn("है", norm_hinglish)

        # Test Urdu script conversion to Devanagari
        norm_urdu = normalize_transcript("مجھے ایک کپ چائے پینی ہے", detected_language="hi")
        self.assertIn("मुझे", norm_urdu)
        self.assertIn("चाय", norm_urdu)

        # Verify already-correct Devanagari text remains intact
        correct_dev = "मुझे एक कप चाय पीनी है।"
        norm_correct = normalize_transcript(correct_dev, detected_language="hi")
        self.assertEqual(norm_correct, correct_dev)

    def test_test_b_hindi_to_english(self):
        """
        Test B — Hindi to English
        Input: 'मुझे एक कप चाय पीनी है।'
        Target: English
        Expected: 'I want to have a cup of tea.'
        """
        res = translate_text("मुझे एक कप चाय पीनी है।", "English")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["source_text"], "मुझे एक कप चाय पीनी है।")
        self.assertEqual(res["target_language"], "English")
        self.assertEqual(res["translated_text"], "I want to have a cup of tea.")

        # Also via HTTP endpoint
        http_res = self.client.post("/translate", json={
            "text": "मुझे एक कप चाय पीनी है।",
            "target_language": "English",
        })
        self.assertEqual(http_res.status_code, 200)
        data = http_res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["translated_text"], "I want to have a cup of tea.")

    def test_test_c_english_to_hindi(self):
        """
        Test C — English to Hindi
        Input: 'I need to drink a cup of tea.'
        Target: Hindi
        Expected: 'मुझे एक कप चाय पीनी है।'
        """
        res = translate_text("I need to drink a cup of tea.", "Hindi")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["source_text"], "I need to drink a cup of tea.")
        self.assertEqual(res["target_language"], "Hindi")
        self.assertEqual(res["translated_text"], "मुझे एक कप चाय पीनी है।")

        # Also via HTTP endpoint
        http_res = self.client.post("/translate", json={
            "text": "I need to drink a cup of tea.",
            "target_language": "Hindi",
        })
        self.assertEqual(http_res.status_code, 200)
        data = http_res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["translated_text"], "मुझे एक कप चाय पीनी है।")

    def test_test_d_english_to_spanish(self):
        """
        Test D — English to Spanish
        Input: 'Good morning.'
        Target: Spanish
        Expected: 'Buenos días.'
        """
        res = translate_text("Good morning.", "Spanish")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["source_text"], "Good morning.")
        self.assertEqual(res["target_language"], "Spanish")
        self.assertEqual(res["translated_text"], "Buenos días.")

        # Also via HTTP endpoint
        http_res = self.client.post("/translate", json={
            "text": "Good morning.",
            "target_language": "Spanish",
        })
        self.assertEqual(http_res.status_code, 200)
        data = http_res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["translated_text"], "Buenos días.")

    def test_test_e_changing_language(self):
        """
        Test E — Changing language
        Translate the same original sentence into Hindi and then English.
        The results must reflect each selected target language.
        """
        original = "मुझे एक कप चाय पीनी है।"

        # 1. Translate original into Hindi (same-language normalization)
        res_hindi = translate_text(original, "Hindi")
        self.assertEqual(res_hindi["status"], "success")
        self.assertEqual(res_hindi["translated_text"], "मुझे एक कप चाय पीनी है।")
        self.assertEqual(res_hindi["target_language"], "Hindi")

        # 2. Translate same original into English
        res_english = translate_text(original, "English")
        self.assertEqual(res_english["status"], "success")
        self.assertEqual(res_english["translated_text"], "I want to have a cup of tea.")
        self.assertEqual(res_english["target_language"], "English")

        # Ensure results are distinctly different and reflect each target language
        self.assertNotEqual(res_hindi["translated_text"], res_english["translated_text"])

    def test_test_f_translation_failure(self):
        """
        Test F — Translation failure
        If the translation service is unavailable, return a clear error.
        Do not report the original sentence as a successful translation.
        """
        with patch('requests.get', side_effect=Exception("Service down")):
            with patch('requests.post', side_effect=Exception("Service down")):
                res = translate_text("Good morning everyone.", "Spanish")
                self.assertEqual(res["status"], "error")
                self.assertIn("unavailable", res.get("error", "").lower())
                # Must NOT return original sentence as translated_text
                self.assertNotIn("translated_text", res)

    def test_test_g_regression_transcript_preservation(self):
        """
        Test G — Regression / Transcript Preservation (Fast Unit Test)
        Verify that /translate preserves the exact source_text without mutation,
        and that translations reflect target language correctly.
        """
        sample_transcript = "मुझे एक कप चाय पीनी है।"
        tr_res = self.client.post("/translate", json={
            "text": sample_transcript,
            "target_language": "English",
        })
        self.assertEqual(tr_res.status_code, 200)
        tr_data = tr_res.get_json()
        self.assertEqual(tr_data["status"], "success")
        self.assertEqual(tr_data["source_text"], sample_transcript)
        self.assertEqual(tr_data["translated_text"], "I want to have a cup of tea.")
        self.assertNotEqual(tr_data["translated_text"], sample_transcript)

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

    # =========================================================================
    # Endpoint Security & Input Validation Tests
    # =========================================================================

    def test_security_system_commands_disabled_by_default(self):
        """Verify that system commands are blocked when ENABLE_SYSTEM_COMMANDS is false."""
        with patch.dict(os.environ, {"ENABLE_SYSTEM_COMMANDS": "false"}):
            # Safe built-in command executes without shell
            cmd_time = detect_command("what time is it")
            self.assertIsNotNone(cmd_time)
            res_time = execute_command(cmd_time)
            self.assertTrue(res_time["executed"])
            self.assertIn("Current date and time", res_time["output"])

            # OS shell command is safely blocked
            cmd_browser = detect_command("open browser")
            self.assertIsNotNone(cmd_browser)
            res_browser = execute_command(cmd_browser)
            self.assertFalse(res_browser["executed"])
            self.assertIn("disabled on this server for security", res_browser["output"])

            # POST /execute is rejected with 403 Forbidden
            res_exec = self.client.post('/execute', json={
                "confirmation_token": "fake-token",
                "confirmed": True,
            })
            self.assertEqual(res_exec.status_code, 403)
            data = res_exec.get_json()
            self.assertIn("disabled", data["error"].lower())

    def test_security_invalid_confirmation_tokens(self):
        """Verify that invalid or missing confirmation tokens are rejected."""
        with patch.dict(os.environ, {"ENABLE_SYSTEM_COMMANDS": "true"}):
            res = confirm_and_execute("nonexistent-token-12345")
            self.assertFalse(res["executed"])
            self.assertIn("Invalid or expired", res["output"])

    def test_transcribe_validation_errors(self):
        """Verify /transcribe returns 400 on missing or invalid audio payloads."""
        # No files provided
        res = self.client.post('/transcribe')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["status"], "error")

        # Unsupported extension
        import io
        fake_file = (io.BytesIO(b"fake data"), "malicious.exe")
        res_bad_ext = self.client.post('/transcribe', data={"audio": fake_file})
        self.assertEqual(res_bad_ext.status_code, 400)
        self.assertIn("Unsupported audio format", res_bad_ext.get_json()["error"])


class WhisperModelIntegrationTests(unittest.TestCase):
    """
    Real Whisper Model Integration Test Suite.
    Runs speech inference on actual audio fixtures.
    Separated from routine PR CI to prevent multi-gigabyte model downloads.
    """

    def setUp(self):
        self.client = app.test_client()
        self.audio_file = "test_hindi.wav"
        if not os.path.isfile(self.audio_file):
            self.skipTest(f"Audio fixture '{self.audio_file}' not found on disk.")

    def test_audio_file_transcription_and_model_reporting(self):
        """
        Verify real Whisper speech-to-text inference on Hindi audio.
        Validates Devanagari output and logs the exact model loaded.
        """
        result = transcribe_audio(self.audio_file)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["language"], "hi")
        self.assertIn("चाय", result["transcription"])
        self.assertIn("कप", result["transcription"])

        loaded_name = get_loaded_model_name()
        self.assertIsNotNone(loaded_name)
        self.assertEqual(result.get("model"), loaded_name)
        print(f"\n[INTEGRATION TEST] Audio transcription succeeded.")
        print(f"[INTEGRATION TEST] Actual model active in memory: '{loaded_name}'")
        safe_output = result['transcription'].encode('ascii', errors='backslashreplace').decode('ascii')
        print(f"[INTEGRATION TEST] Transcription output: '{safe_output}'")

    def test_transcribe_endpoint_audio_regression(self):
        """
        Verify POST /transcribe with audio fixture followed by translation.
        Ensures original transcription is preserved.
        """
        with open(self.audio_file, "rb") as f:
            tx_res = self.client.post("/transcribe", data={"audio": (f, "test_hindi.wav")})
        self.assertEqual(tx_res.status_code, 200)
        tx_data = tx_res.get_json()
        self.assertEqual(tx_data["status"], "success")
        original_tx = tx_data["transcription"]
        self.assertTrue(len(original_tx) > 0)

        tr_res = self.client.post("/translate", json={
            "text": original_tx,
            "target_language": "English",
        })
        self.assertEqual(tr_res.status_code, 200)
        tr_data = tr_res.get_json()
        self.assertEqual(tr_data["source_text"], original_tx)
        self.assertNotEqual(tr_data["translated_text"], original_tx)


# Backward compatibility alias
TranslationFeatureTests = TranslationFeatureUnitTests


if __name__ == '__main__':
    unittest.main()
