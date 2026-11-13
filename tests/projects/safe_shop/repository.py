def fetch(connection, query, parameters):
    return connection.execute(query, parameters).fetchall()
