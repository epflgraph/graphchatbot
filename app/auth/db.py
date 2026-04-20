import pymysql

from app.config import config


def _connect():
    db_config = config['database']
    return pymysql.connect(
        host=db_config['host'],
        port=int(db_config['port']),
        user=db_config['user'],
        password=db_config['password'],
        autocommit=True,
    )


def _execute(query, values=None):
    conn = _connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, values)
            return cursor.fetchall()
    finally:
        conn.close()


def init_auth_schema():
    _execute(
        """
        CREATE DATABASE IF NOT EXISTS `chatbot`
        DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
        """
    )

    _execute(
        """
        CREATE TABLE IF NOT EXISTS `chatbot`.`api_keys` (
          `api_key` VARCHAR(63) NOT NULL,
          `sciper` VARCHAR(15) DEFAULT NULL,
          `email` VARCHAR(255) DEFAULT NULL,
          `is_active` TINYINT(1) DEFAULT 1,
          `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          `updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY api_key (api_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """
    )


def get_api_key(sciper, email):
    init_auth_schema()

    result = _execute(
        """
        SELECT `api_key` FROM `chatbot`.`api_keys`
        WHERE `sciper` = %s AND `email` = %s
        LIMIT 1
        """,
        values=[sciper, email],
    )

    if result:
        api_key, = result[0]
    else:
        api_key = None

    return api_key


def get_user(api_key):
    init_auth_schema()

    result = _execute(
        """
        SELECT `sciper`, `email`, `is_active`
        FROM `chatbot`.`api_keys`
        WHERE `api_key` = %s
        LIMIT 1
        """,
        values=[api_key],
    )

    if not result:
        return None

    sciper, email, is_active = result[0]

    return {
        'sciper': sciper,
        'email': email,
        'is_active': is_active,
    }


def insert_api_keys(records):
    init_auth_schema()

    placeholders = []
    values = []
    for record in records:
        placeholders.append('(%s, %s, %s)')
        values.extend([record['api_key'], record['sciper'], record['email']])

    _execute(
        f"""
        INSERT INTO `chatbot`.`api_keys`(`api_key`, `sciper`, `email`)
        VALUES {', '.join(placeholders)}
        ON DUPLICATE KEY UPDATE `is_active` = 1
        """,
        values,
    )


def deactivate_api_keys(conditions):
    init_auth_schema()

    for field in conditions:
        values = conditions[field]
        if values:
            _execute(
                f"""
                UPDATE `chatbot`.`api_keys`
                SET `is_active`=0
                WHERE `{field}` IN ({', '.join(['%s'] * len(values))})
                """,
                values,
            )
