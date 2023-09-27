import mysql.connector

from app.config import config

db = mysql.connector.connect(
    host=config['database']['host'],
    port=config['database']['port'],
    user=config['database']['user'],
    password=config['database']['password'],
)


def execute_query(query, values):
    db.ping(reconnect=True)

    cursor = db.cursor()

    try:
        cursor.execute(query, values)
    except mysql.connector.Error as e:
        print("Error", e)
        raise e

    results = list(cursor)

    db.commit()

    return results
