import unittest

from app.password_policy import get_password_policy_error


class PasswordPolicyTests(unittest.TestCase):
    def test_accepts_password_with_letters_and_digits_in_range(self):
        self.assertIsNone(get_password_policy_error("abc123"))
        self.assertIsNone(get_password_policy_error("Abc12345"))

    def test_rejects_password_that_is_too_short(self):
        self.assertEqual(get_password_policy_error("a1b2"), "密码长度必须为6到16位")

    def test_rejects_password_that_is_too_long(self):
        self.assertEqual(get_password_policy_error("a1" * 9), "密码长度必须为6到16位")

    def test_rejects_password_without_letters(self):
        self.assertEqual(get_password_policy_error("123456"), "密码必须同时包含字母和数字")

    def test_rejects_password_without_digits(self):
        self.assertEqual(get_password_policy_error("abcdef"), "密码必须同时包含字母和数字")

    def test_rejects_password_with_symbols(self):
        self.assertEqual(get_password_policy_error("abc123!"), "密码只能包含字母和数字")


if __name__ == "__main__":
    unittest.main()
