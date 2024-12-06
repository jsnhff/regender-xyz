import unittest
from unittest.mock import patch, MagicMock
import regender_app

class TestRegenderApp(unittest.TestCase):

    @patch('regender_app.OpenAI')
    def test_check_openai_api_key_valid(self, MockOpenAI):
        mock_client = MockOpenAI.return_value
        mock_client.models.list.return_value = True
        with patch('builtins.print') as mocked_print:
            regender_app.check_openai_api_key()
            mocked_print.assert_called_with("OpenAI API key is valid.")

    @patch('regender_app.OpenAI')
    def test_check_openai_api_key_invalid(self, MockOpenAI):
        mock_client = MockOpenAI.return_value
        mock_client.models.list.side_effect = Exception("Invalid API key")
        with patch('builtins.print') as mocked_print:
            regender_app.check_openai_api_key()
            mocked_print.assert_any_call("Error: Invalid API key")
            mocked_print.assert_any_call("OpenAI API key is invalid or there is an issue with the connection.")

    @patch('regender_app.client.chat.completions.create')
    def test_get_gpt_response_success(self, mock_create):
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Test response"))]
        response = regender_app.get_gpt_response("Test prompt")
        self.assertEqual(response, "Test response")

    @patch('regender_app.client.chat.completions.create')
    def test_get_gpt_response_failure(self, mock_create):
        mock_create.side_effect = Exception("API error")
        response = regender_app.get_gpt_response("Test prompt", retries=1, delay=0)
        self.assertEqual(response, "Error: Unable to get response after multiple attempts")

    @patch('regender_app.get_gpt_response')
    def test_detect_roles_gpt(self, mock_get_gpt_response):
        mock_get_gpt_response.return_value = "Character - Role - Gender"
        response = regender_app.detect_roles_gpt("Test input text")
        self.assertEqual(response, "Character - Role - Gender")

    @patch('regender_app.get_gpt_response')
    def test_regender_text_gpt(self, mock_get_gpt_response):
        mock_get_gpt_response.return_value = "Regendered text"
        response = regender_app.regender_text_gpt("Test input text", "Character - Role - Gender")
        self.assertEqual(response, "Regendered text")

    def test_highlight_changes(self):
        original_text = "This is a test."
        regendered_text = "This is a test!"
        expected_diff = "--- \n+++ \n@@ -1 +1 @@\n-This is a test.\n+This is a test!\n"
        diff = regender_app.highlight_changes(original_text, regendered_text)
        self.assertEqual(diff, expected_diff)

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_log_output(self, mock_open):
        regender_app.log_output("log.txt", "Test log")
        mock_open.assert_called_with("log.txt", 'w')
        mock_open().write.assert_called_with("Test log\n")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="Test input text")
    def test_load_input_text(self, mock_open):
        input_text = regender_app.load_input_text("input.txt")
        self.assertEqual(input_text, "Test input text")

    @patch('builtins.input', side_effect=["male", ""])
    def test_confirm_roles(self, mock_input):
        roles_info = "Character1 - Role1 - female\nCharacter2 - Role2 - male"
        expected_confirmed_roles = "Character1 - Role1 - male\nCharacter2 - Role2 - male"
        confirmed_roles = regender_app.confirm_roles(roles_info)
        self.assertEqual(confirmed_roles, expected_confirmed_roles)

if __name__ == '__main__':
    unittest.main()