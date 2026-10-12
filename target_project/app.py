import sqlite3

PASSWORD = "admin123"


def get_user(name):
    conn = sqlite3.connect("db.sqlite")
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    return conn.execute(query).fetchall()


def run(expr):
    return eval(expr)
