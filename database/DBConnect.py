import mysql.connector
from mysql.connector import errorcode
import pathlib


class DBConnect:
    _cnxpool = None

    def __init__(self):
        raise RuntimeError('Do not create an instance, use the class method get_connection()!')

    @classmethod
    def get_connection(cls, pool_name="my_pool", pool_size=3) -> mysql.connector.pooling.PooledMySQLConnection:
        if cls._cnxpool is None:
            try:
                cls._cnxpool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name=pool_name,
                    pool_size=pool_size,
                    option_files=f"{pathlib.Path(__file__).resolve().parent}/connector.cnf"
                )
                return cls._cnxpool.get_connection()
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    print("Something is wrong with your user name or password")
                    return None
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    print("Database does not exist")
                    return None
                else:
                    print(err)
                    return None
        else:
            return cls._cnxpool.get_connection()
