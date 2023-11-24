import mysql.connector

from db_cache_manager.db import DBCachingManagerBase

from app.config import config


################################################################
# CACHING MANAGER                                              #
################################################################

class ChatbotDBCachingManager(DBCachingManagerBase):
    # This class demonstrates how to extend the DBCachingManagerBase class for a concrete case
    # For most purposes, the default methods defined in the parent class should be appropriate for any and all tasks.
    # Feel free to overwrite any if you have special mechanisms (e.g. if some results expire after a certain amount
    # of time, you may have to overwrite `get_details`, `get_details_using_origin`, etc.)
    def __init__(self):
        """
        db_config: Parameters for the database connection
        cache_table: Name of the main cache table, where the actual results are stored
        most_similar_table: Name of the similarity table, where the similarity relationships between different rows
            of the cache table are stored
        schema: Name of the database schema
        """
        super().__init__(
            db_config={
              'host': config['database']['host'],
              'port': config['database']['port'],
              'user': config['database']['user'],
              'pass': config['database']['password'],
            },
            cache_table='exact_cache',
            most_similar_table='closest_match_cache',
            schema='chatbot',
        )

    def init_db(self):
        # This method implements an abstract method in the parent.
        # This example demonstrates the general layout of this method, and generally these are all the lines you need.
        # All you have to do is to add your own columns to the definition of the cache table. See more below.

        # Making sure the schema exists
        self.db.execute_query(
            f"""
            CREATE DATABASE IF NOT EXISTS `{self.schema}`
            DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
            DEFAULT ENCRYPTION='N';
            """
        )

        # Creating the cache table if it does not exist
        # The columns "id_token" and "date_added" should not have their names changed, since the
        # methods in the parent class rely on their names.
        # The types of "id_token" and "date_added" should not be changed, but "fingerprint" can be LONGTEXT if need be.
        # Aside from these three columns, add any columns you need. For this example, the task could be text
        # classification: there is an "input" and an "output" column, where "output" is the name of the class that
        # "input" has been classified as. "fingerprint" is the fingerprint of "input", and can be null.
        self.db.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.schema}`.`{self.cache_table}` (
              `id_token` VARCHAR(255),
              `fingerprint` VARCHAR(255) DEFAULT NULL,
              `input` LONGTEXT DEFAULT NULL,
              `output` VARCHAR(255) DEFAULT NULL,
              `date_added` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY id_token (id_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

        # # To speed up fingerprint lookups, it is advisable to create a fingerprint index
        # try:
        #     self.db.execute_query(
        #         f"""
        #         CREATE INDEX `example_main_fp_index` ON `{self.schema}`.`{self.cache_table}` (`fingerprint`(64));
        #         """
        #     )
        # except Exception:
        #     pass

        # Creating the closest match table. This table represents a DAG of most-similar relationships (although it
        # can also have self-loops), where the row with "id_token" as its id is found to be (almost or exactly)
        # identical to the row with "most_similar_token" as its id.
        self.db.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.schema}`.`{self.most_similar_table}` (
              `id_token` VARCHAR(255),
              `most_similar_token` VARCHAR(255) DEFAULT NULL,
              PRIMARY KEY id_token (id_token),
              KEY most_similar_token (most_similar_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

    def get(self, key):
        match = self.get_details(key, ['output'])[0]

        if match is None:
            return None

        return match['output']

    def set(self, key, value):
        self.insert_or_update_details(key, values_to_insert={'output': value})

    def delete(self, key):
        self.delete_cache_rows([key])


db_manager = ChatbotDBCachingManager()

################################################################


db = mysql.connector.connect(
    host=config['database']['host'],
    port=config['database']['port'],
    user=config['database']['user'],
    password=config['database']['password'],
)
