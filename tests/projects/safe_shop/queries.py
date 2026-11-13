def user_query(name):
    return 'SELECT id, name FROM users WHERE name = ?', (name,)
