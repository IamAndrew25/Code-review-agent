import sqlite3

PASSWORD = "demo-hardcoded-password"

def find_user(user_id):
    connection = sqlite3.connect(":memory:")
    return connection.execute("SELECT * FROM users WHERE id = " + user_id)
