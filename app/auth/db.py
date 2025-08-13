from db_cache_manager.db import DB

from app.config import config


def init_auth_schema():
    db = DB(config['database'])

    # Make sure the schema exists
    db.execute_query(
        """
        CREATE DATABASE IF NOT EXISTS `chatbot`
        DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
        DEFAULT ENCRYPTION='N';
        """
    )

    # Make sure the tables exist
    db.execute_query(
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
    db = DB(config['database'])

    init_auth_schema()

    query = """
        SELECT `api_key` FROM `chatbot`.`api_keys`
        WHERE `sciper` = %s AND `email` = %s
        LIMIT 1
    """

    result = db.execute_query(query, values=[sciper, email])

    if result:
        api_key, = result[0]
    else:
        api_key = None

    return api_key


def get_user(api_key):
    db = DB(config['database'])

    init_auth_schema()

    query = """
        SELECT `sciper`, `email`, `is_active`
        FROM `chatbot`.`api_keys`
        WHERE `api_key` = %s
        LIMIT 1
    """
    result = db.execute_query(query, values=[api_key])

    if not result:
        return None

    sciper, email, is_active = result[0]

    user = {
        'sciper': sciper,
        'email': email,
        'is_active': is_active,
    }

    return user


def insert_api_keys(records):
    db = DB(config['database'])

    init_auth_schema()

    placeholders = []
    values = []
    for record in records:
        placeholders.append('(%s, %s, %s)')
        values.extend([record['api_key'], record['sciper'], record['email']])

    query = f"""
        INSERT INTO `chatbot`.`api_keys`(`api_key`, `sciper`, `email`)
        VALUES {', '.join(placeholders)}
        ON DUPLICATE KEY UPDATE `is_active` = 1
    """

    db.execute_query(query, values)


def deactivate_api_keys(conditions):
    db = DB(config['database'])

    init_auth_schema()

    for field in conditions:
        values = conditions[field]
        if values:
            query = f"""
                UPDATE `chatbot`.`api_keys`
                SET `is_active`=0
                WHERE `{field}` IN ({', '.join(['%s'] * len(values))})
            """

            db.execute_query(query, values)
