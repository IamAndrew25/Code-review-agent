def fetch(connection, query):
    return connection.execute(query).fetchall()
