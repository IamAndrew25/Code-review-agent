import os
import sqlite3

PASSWORD = os.environ.get("APP_PASSWORD")

def find_user(user_id):
    connection = sqlite3.connect(":memory:")
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,))
