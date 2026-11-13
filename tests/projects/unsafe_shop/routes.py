from queries import user_query
from repository import fetch


def search_users(request, connection):
    name = request.args.get('name', '')
    query = user_query(name)
    return fetch(connection, query)
