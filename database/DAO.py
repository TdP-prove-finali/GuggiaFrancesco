from database.DBConnect import DBConnect
from model.entita import Arena, Partita, Squadra, Stagione


class DAO:

    @staticmethod
    def getAllSquadre():
        conn = DBConnect.get_connection()
        results = []
        cursor = conn.cursor(dictionary=True)
        query = """SELECT team_id, nome, citta, stato, conference, divisione
                   FROM team
                   ORDER BY nome"""
        cursor.execute(query)
        for row in cursor:
            results.append(Squadra(**row))
        cursor.close()
        conn.close()
        return results

    @staticmethod
    def getAllStagioni():
        conn = DBConnect.get_connection()
        results = []
        cursor = conn.cursor(dictionary=True)
        query = """SELECT stagione_id, anno_inizio, data_avvio, data_chiusura
                   FROM stagione
                   ORDER BY anno_inizio DESC"""
        cursor.execute(query)
        for row in cursor:
            results.append(Stagione(**row))
        cursor.close()
        conn.close()
        return results

    @staticmethod
    def getAllArene():
        conn = DBConnect.get_connection()
        results = []
        cursor = conn.cursor(dictionary=True)
        query = """SELECT a.team_id, t.citta
                   FROM arena a, team t
                   WHERE a.team_id = t.team_id
                   ORDER BY a.team_id"""
        cursor.execute(query)
        for row in cursor:
            results.append(Arena(**row))
        cursor.close()
        conn.close()
        return results

    @staticmethod
    def getEdges(idMap):
        conn = DBConnect.get_connection()
        results = []
        cursor = conn.cursor(dictionary=True)

        query = """SELECT team_a, team_b, km
                   FROM distanza
                   WHERE team_a < team_b"""
        cursor.execute(query)
        for row in cursor:
            results.append((idMap[row["team_a"]], idMap[row["team_b"]], float(row["km"])))
        cursor.close()
        conn.close()
        return results

    @staticmethod
    def getPartiteSquadra(stagione_id, team_id):
        conn = DBConnect.get_connection()
        results = []
        cursor = conn.cursor(dictionary=True)

        query = """SELECT data, team_casa, team_ospite, sede_neutra
                   FROM partita
                   WHERE stagione_id = %s AND (team_casa = %s OR team_ospite = %s)
                   ORDER BY data"""
        cursor.execute(query, (stagione_id, team_id, team_id))
        for row in cursor:
            results.append(Partita(row["data"], row["team_casa"],
                                   row["team_ospite"], bool(row["sede_neutra"])))
        cursor.close()
        conn.close()
        return results
