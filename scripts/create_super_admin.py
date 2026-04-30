"""
One-time script to seed the first super_admin user.

Usage:
    python -m scripts.create_super_admin
"""
import sys
import getpass

sys.path.insert(0, ".")

import auth as auth_module
from database import get_db


def main() -> None:
    print("Create super_admin user")
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    confirm  = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    db = get_db()
    existing = db.table("users").select("id").eq("username", username).execute().data
    if existing:
        print(f"User '{username}' already exists.")
        sys.exit(1)

    db.table("users").insert({
        "username": username,
        "password_hash": auth_module.hash_password(password),
        "role": "super_admin",
        "is_admin": True,
    }).execute()
    print(f"super_admin '{username}' created.")


if __name__ == "__main__":
    main()
