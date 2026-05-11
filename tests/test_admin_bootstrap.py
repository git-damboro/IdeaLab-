import unittest
from datetime import datetime

from app.auth_bootstrap import bootstrap_default_admin, user_requires_password_change


class FakeUsers:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find_one(self, query):
        if query == {"role_codes": "admin"}:
            return next((d for d in self.docs if "admin" in d.get("role_codes", [])), None)
        if "username" in query:
            return next((d for d in self.docs if d.get("username") == query["username"]), None)
        return None

    def insert_one(self, doc):
        self.docs.append(doc)


class AdminBootstrapTests(unittest.TestCase):
    def test_creates_default_admin_when_no_admin_exists(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="secret123",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertTrue(created)
        self.assertEqual(users.docs[0]["username"], "admin")
        self.assertEqual(users.docs[0]["password_hash"], "hashed:secret123")
        self.assertEqual(users.docs[0]["role_codes"], ["admin"])
        self.assertTrue(users.docs[0]["must_change_password"])

    def test_does_not_create_default_admin_when_admin_exists(self):
        users = FakeUsers([{"username": "root", "role_codes": ["admin"]}])

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="secret123",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(len(users.docs), 1)

    def test_does_not_create_default_admin_without_config(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="",
            admin_password="",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(users.docs, [])

    def test_does_not_create_default_admin_with_short_password(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="123",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(users.docs, [])

    def test_does_not_create_default_admin_with_password_missing_letters(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="123456",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(users.docs, [])

    def test_does_not_create_default_admin_with_password_missing_digits(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="abcdef",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(users.docs, [])

    def test_does_not_create_default_admin_with_password_too_long(self):
        users = FakeUsers()

        created = bootstrap_default_admin(
            users,
            admin_username="admin",
            admin_password="a1b2c3d4e5f6g7h8i9",
            hash_password=lambda value: f"hashed:{value}",
            now=lambda: datetime(2026, 5, 10),
        )

        self.assertFalse(created)
        self.assertEqual(users.docs, [])

    def test_requires_password_change_only_for_flagged_users(self):
        self.assertTrue(user_requires_password_change({"must_change_password": True}))
        self.assertFalse(user_requires_password_change({"must_change_password": False}))
        self.assertFalse(user_requires_password_change({}))


if __name__ == "__main__":
    unittest.main()
