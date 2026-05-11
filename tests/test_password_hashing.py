import os
import unittest

os.environ.setdefault("ALIBABA_API_KEY", "test-key")
os.environ["MONGO_URI"] = ""

from app.password_utils import truncate_bcrypt_password


class PasswordHashingTests(unittest.TestCase):
    def test_truncates_password_to_72_utf8_bytes(self):
        password = "测" * 25

        truncated = truncate_bcrypt_password(password)

        self.assertLessEqual(len(truncated.encode("utf-8")), 72)
        self.assertEqual(truncated, "测" * 24)

    def test_leaves_short_password_unchanged(self):
        password = "abcdef123456"

        self.assertEqual(truncate_bcrypt_password(password), password)


if __name__ == "__main__":
    unittest.main()
