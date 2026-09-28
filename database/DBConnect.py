"""
Gestione della connessione al database MySQL.

I parametri non sono nel codice ma in connector.cnf, letto tramite il
meccanismo degli option file di mysql-connector-python.
"""

from pathlib import Path

import mysql.connector
from mysql.connector import Error

FILE_CONFIGURAZIONE = Path(__file__).with_name("connector.cnf")


class DBConnect:
    _connessione = None

    @staticmethod
    def get_connection():
        """Restituisce la connessione condivisa, riaprendola se e' stata chiusa."""
        if DBConnect._connessione is not None and DBConnect._connessione.is_connected():
            return DBConnect._connessione

        try:
            DBConnect._connessione = mysql.connector.connect(
                option_files=str(FILE_CONFIGURAZIONE)
            )
        except Error as e:
            DBConnect._connessione = None
            # Meglio fermarsi qui con un messaggio chiaro che restituire None e
            # far fallire il primo cursore con un AttributeError incomprensibile.
            raise RuntimeError(
                f"Connessione al database non riuscita: {e}\n"
                f"Verificare che MySQL sia avviato e che i parametri in "
                f"{FILE_CONFIGURAZIONE} siano corretti."
            ) from e

        return DBConnect._connessione

    @staticmethod
    def close_connection():
        if DBConnect._connessione is not None and DBConnect._connessione.is_connected():
            DBConnect._connessione.close()
        DBConnect._connessione = None
