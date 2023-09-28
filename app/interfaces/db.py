import mysql.connector

from app.config import config

db = mysql.connector.connect(
    host=config['database']['host'],
    port=config['database']['port'],
    user=config['database']['user'],
    password=config['database']['password'],
)


def execute_query(query, values=None):
    db.ping(reconnect=True)

    cursor = db.cursor()

    try:
        if values is not None:
            cursor.execute(query, values)
        else:
            cursor.execute(query)
    except mysql.connector.Error as e:
        print("Error", e)
        raise e

    results = list(cursor)

    db.commit()

    return results


def update_token_count(user_id, token_count):
    query = f"""
    INSERT INTO chatbot.token_usage(user_id, token_count)
    VALUES ({user_id}, {token_count})
    ON DUPLICATE KEY UPDATE token_count = token_count + {token_count};
    """

    execute_query(query)
