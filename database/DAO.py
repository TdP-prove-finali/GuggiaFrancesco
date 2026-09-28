"""
Livello di accesso ai dati.

Ogni metodo apre la connessione condivisa, legge e restituisce entita' del
dominio: sopra questo livello non circolano tuple o dizionari del driver.
"""

from database.DBConnect import DBConnect
from model.entita import Arena, Partita, Squadra, Stagione


class DAO:

    @staticmethod
    def getAllSquadre():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""SELECT team_id, nome, citta, stato, conference, divisione
                          FROM team ORDER BY nome""")
        risultato = []
        for row in cursor:
            risultato.append(Squadra(row["team_id"], row["nome"], row["citta"],
                                     row["stato"], row["conference"], row["divisione"]))
        cursor.close()
        return risultato

    @staticmethod
    def getAllStagioni():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""SELECT stagione_id, anno_inizio, data_avvio, data_chiusura
                          FROM stagione ORDER BY anno_inizio DESC""")
        risultato = []
        for row in cursor:
            risultato.append(Stagione(row["stagione_id"], row["anno_inizio"],
                                      row["data_avvio"], row["data_chiusura"]))
        cursor.close()
        return risultato

    @staticmethod
    def getAllArene():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""SELECT a.team_id, t.citta
                          FROM arena a JOIN team t ON t.team_id = a.team_id
                          ORDER BY a.team_id""")
        risultato = []
        for row in cursor:
            risultato.append(Arena(row["team_id"], row["citta"]))
        cursor.close()
        return risultato

    @staticmethod
    def getEdges():
        """Archi del grafo come tuple (nodo1, nodo2, peso), un verso solo."""
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""SELECT team_a, team_b, km FROM distanza
                          WHERE team_a < team_b""")
        risultato = []
        for row in cursor:
            risultato.append((row["team_a"], row["team_b"], float(row["km"])))
        cursor.close()
        return risultato

    @staticmethod
    def getPartiteSquadra(stagione_id, team_id):
        """Tutte le partite della squadra, interne ed esterne, in ordine di data."""
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""SELECT data, team_casa, team_ospite, sede_neutra
                          FROM partita
                          WHERE stagione_id = %s AND (team_casa = %s OR team_ospite = %s)
                          ORDER BY data""",
                       (stagione_id, team_id, team_id))
        risultato = []
        for row in cursor:
            risultato.append(Partita(row["data"], row["team_casa"],
                                     row["team_ospite"], bool(row["sede_neutra"])))
        cursor.close()
        return risultato
