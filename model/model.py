import copy

import networkx as nx

from database.DAO import DAO
from model.entita import Costo, Metriche, Piano, Viaggio

# definisco un numero massimo di gare per rendere il risultato più simile alla realtà e diminuire il costo computazionale
MAX_GARE_PER_VIAGGIO = 7
PARAMETRI_COSTO = {
    "volo_quota_fissa":       {"valore": 25000.0, "unita": "EUR per tratta"},
    "volo_costo_km":          {"valore": 30.0,    "unita": "EUR per km"},
    "hotel_camera_notte":     {"valore": 250.0,   "unita": "EUR per notte"},
    "diaria_persona":         {"valore": 150.0,   "unita": "EUR per giorno"},
    "dimensione_delegazione": {"valore": 25.0,    "unita": "persone"},
}


class Model:

    def __init__(self):
        self._graph = nx.Graph()
        self._idMap = {}
        self._squadre = {}
        self._parametri = copy.deepcopy(PARAMETRI_COSTO)
        self._cacheSequenza = {}
        self._bestOrdine = None
        self._bestScore = 0.0
        for squadra in DAO.getAllSquadre():
            self._squadre[squadra.team_id] = squadra

    def buildGraph(self):
        self._graph.clear()
        self._idMap.clear()
        nodes = DAO.getAllArene()
        for n in nodes:
            self._idMap[n.team_id] = n
        self._graph.add_nodes_from(nodes)
        allEdges = DAO.getEdges(self._idMap)
        for e in allEdges:
            self._graph.add_edge(e[0], e[1], weight=e[2])

    def getGraphDetails(self):
        return self._graph.number_of_nodes(), self._graph.number_of_edges()

    def pesoTratta(self, a, b) -> float:
        if a == b:
            return 0.0
        return self._graph[self._idMap[a]][self._idMap[b]]["weight"]

    def kmPercorso(self, sede, tappe) -> float:
        percorso = [sede] + list(tappe) + [sede]
        totale = 0.0
        for i in range(len(percorso) - 1):
            totale += self.pesoTratta(percorso[i], percorso[i + 1])
        return totale

    # sequenziamento di un viaggio:
    # provo tutti gli ordini delle tappe con partenza e ritorno in sede
    # e tengo quello con meno km.
    def sequenzaOttima(self, sede, tappe):
        tappe = list(tappe)
        if len(tappe) <= 1:
            return tuple(tappe), self.kmPercorso(sede, tappe)
        chiave = (sede, tuple(sorted(tappe)))
        if chiave in self._cacheSequenza:
            return self._cacheSequenza[chiave]
        self._bestOrdine = None
        self._bestScore = 10 ** 12        # numero grande: ogni percorso reale e' minore
        self._ricorsione(sede, tappe, [], 0.0, sede)
        risultato = (tuple(self._bestOrdine), self._bestScore)
        self._cacheSequenza[chiave] = risultato
        return risultato

    def _ricorsione(self, sede, tappe, parziale, km_parziale, corrente):
        # parziale = tappe gia' ordinate, km_parziale = km fin qui, corrente = ultima citta'
        # potatura: i km possono solo crescere, se ho gia' raggiunto il migliore il ramo e' inutile
        if km_parziale >= self._bestScore:
            return
        # tutte le tappe ordinate, si chiude il giro tornando in sede
        if len(parziale) == len(tappe):
            km = km_parziale + self.pesoTratta(corrente, sede)
            if km < self._bestScore:
                self._bestScore = km
                self._bestOrdine = copy.deepcopy(parziale)   # il backtracking svuota parziale
            return
        # ogni tappa non ancora visitata puo' essere la prossima.
        # "not in parziale" richiede tappe distinte
        for prossima in tappe:
            if prossima not in parziale:
                parziale.append(prossima)
                self._ricorsione(sede, tappe, parziale,
                                 km_parziale + self.pesoTratta(corrente, prossima),
                                 prossima)
                parziale.pop()

    def _costruisciViaggio(self, sede, tappe, data_inizio=None, data_fine=None):
        ordine, km = self.sequenzaOttima(sede, tappe)
        return Viaggio(ordine, km, data_inizio, data_fine)

    # partizionamento delle trasferte in viaggi da max_partite gare:
    def partizionaViaggi(self, sede, destinazioni, max_partite):
        gruppi = self._partizionaEuristico(sede, destinazioni, max_partite)
        return self._ricercaLocale(sede, gruppi, max_partite)

    def _partizionaEuristico(self, sede, destinazioni, max_partite):
        rimaste = list(destinazioni)
        gruppi = []
        # ogni viaggio nasce dalla tappa libera piu' lontana dalla sede e cresce
        # aggiungendo, una alla volta, la tappa piu' vicina al gruppo
        while rimaste:
            seme = rimaste[0]
            for d in rimaste:
                if self.pesoTratta(sede, d) > self.pesoTratta(sede, seme):
                    seme = d
            rimaste.remove(seme)
            gruppo = [seme]
            while len(gruppo) < max_partite:
                candidati = []
                for d in rimaste:
                    if d not in gruppo:   # niente doppioni: la ricorsione vuole tappe distinte
                        candidati.append(d)
                if not candidati:
                    break
                prossima = candidati[0]
                migliore = self._distGruppo(prossima, gruppo)
                for d in candidati:
                    dist = self._distGruppo(d, gruppo)
                    if dist < migliore:
                        migliore = dist
                        prossima = d
                gruppo.append(prossima)
                rimaste.remove(prossima)
            gruppi.append(gruppo)
        return gruppi

    def _distGruppo(self, d, gruppo):
        minimo = 10 ** 12
        for t in gruppo:
            peso = self.pesoTratta(d, t)
            if peso < minimo:
                minimo = peso
        return minimo

    def _ricercaLocale(self, sede, gruppi, max_partite):
        gruppi = copy.deepcopy(gruppi)
        valore = self._valutaGruppi(sede, gruppi)
        # first improvement: accetto la prima mossa che abbassa il costo e si riparte;
        # ci si ferma in un ottimo locale
        migliorato = True
        while migliorato:
            migliorato = False
            for cand in self._mosseVicine(gruppi, max_partite):
                nuovo = self._valutaGruppi(sede, cand)
                if nuovo < valore:
                    gruppi = cand
                    valore = nuovo
                    migliorato = True
                    break
        return gruppi

    @staticmethod
    def _mosseVicine(gruppi, max_partite):
        # vicinato "relocate": sposta una tappa in un altro viaggio non pieno che non la
        # contiene gia'; un viaggio rimasto vuoto viene eliminato
        mosse = []
        for i in range(len(gruppi)):
            for tappa in gruppi[i]:
                for j in range(len(gruppi)):
                    if i == j or len(gruppi[j]) >= max_partite or tappa in gruppi[j]:
                        continue
                    cand = copy.deepcopy(gruppi)
                    cand[i].remove(tappa)
                    cand[j].append(tappa)
                    puliti = []
                    for g in cand:
                        if g:
                            puliti.append(g)
                    mosse.append(puliti)
        return mosse

    def _valutaGruppi(self, sede, gruppi):
        # ogni gruppo e' valutato nel suo ordine ottimo (quindi passa dalla ricorsione)
        viaggi = []
        for g in gruppi:
            if g:
                viaggi.append(self._costruisciViaggio(sede, g))
        return self.calcolaCosto(self.calcolaMetriche(viaggi)).totale

    def calcolaMetriche(self, viaggi) -> Metriche:
        km = 0.0
        trasferimenti = 0
        tratte = 0
        partite = 0
        for v in viaggi:
            km += v.km
            trasferimenti += v.partite - 1
            tratte += v.tratte
            partite += v.partite
        # senza date: un giorno (e una notte) fuori per ogni gara, piu' uno per viaggio
        return Metriche(
            km=km,
            trasferimenti=trasferimenti,
            giorni_fuori=partite + len(viaggi),
            notti=partite + len(viaggi),
            viaggi=len(viaggi),
            tratte=tratte,
            partite=partite,
        )

    def calcolaCosto(self, metriche) -> Costo:
        v = {}
        for n, d in self._parametri.items():
            v[n] = d["valore"]
        delegazione = v["dimensione_delegazione"]
        return Costo(
            volo_fisso=metriche.tratte * v["volo_quota_fissa"],
            volo_km=metriche.km * v["volo_costo_km"],
            hotel=metriche.notti * v["hotel_camera_notte"] * delegazione,
            diaria=metriche.giorni_fuori * v["diaria_persona"] * delegazione,
        )

    def analizzaBaseline(self, stagione_id, team_id) -> Piano:
        partite = DAO.getPartiteSquadra(stagione_id, team_id)
        # le gare esterne consecutive, fino alla gara in casa successiva,
        # formano un viaggio
        viaggi, corrente = [], []
        for partita in partite:
            if partita.team_casa == team_id:
                if corrente:
                    viaggi.append(self._viaggioReale(team_id, corrente))
                    corrente = []
            else:
                corrente.append(partita)
        if corrente:
            viaggi.append(self._viaggioReale(team_id, corrente))
        metriche = self.calcolaMetriche(viaggi)
        return Piano(team_id, stagione_id,
                     viaggi, metriche, self.calcolaCosto(metriche))

    def _viaggioReale(self, sede, partite):
        tappe = []
        for p in partite:
            tappe.append(p.team_casa)
        return Viaggio(tuple(tappe), self.kmPercorso(sede, tappe),
                       partite[0].data, partite[-1].data)

    def ottimizzaPiano(self, stagione_id, team_id, max_partite, baseline=None) -> Piano:
        if baseline is None:
            baseline = self.analizzaBaseline(stagione_id, team_id)
        # stesse trasferte del calendario reale cambia solo come sono raggruppate e ordinate
        destinazioni = []
        for viaggio in baseline.viaggi:
            for tappa in viaggio.tappe:
                destinazioni.append(tappa)
        gruppi = self.partizionaViaggi(team_id, destinazioni, max_partite)
        viaggi = []
        for g in gruppi:
            viaggi.append(self._costruisciViaggio(team_id, g))
        viaggi.sort(key=lambda v: v.km, reverse=True)
        metriche = self.calcolaMetriche(viaggi)
        return Piano(team_id, stagione_id,
                     viaggi, metriche, self.calcolaCosto(metriche))

    def confrontoFranchigie(self, stagione_id, max_partite, criterio="costo_ottimo"):
        risultati = []
        for team_id in sorted(self._squadre):
            baseline = self.analizzaBaseline(stagione_id, team_id)
            if not baseline.viaggi:
                continue
            piano = self.ottimizzaPiano(stagione_id, team_id, max_partite, baseline)
            risparmio_km = baseline.metriche.km - piano.metriche.km
            risultati.append({
                "team_id": team_id, "nome": self._squadre[team_id].nome,
                "km_reali": baseline.metriche.km, "km_ottimi": piano.metriche.km,
                "costo_reale": baseline.costo.totale, "costo_ottimo": piano.costo.totale,
                "risparmio_km": risparmio_km,
                "risparmio_pct": risparmio_km / baseline.metriche.km * 100,
                "risparmio_eur": baseline.costo.totale - piano.costo.totale,
            })
        # criterio = "costo_ottimo": onere da sostenere, che resta anche pianificando al meglio
        # e dipende solo dalla posizione della sede
        # criterio = "costo_reale":  quanto e' costato davvero il calendario disputato
        # criterio = "risparmio_eur": quanto renderebbe pianificare meglio
        # costi in ordine crescente (in cima chi spende meno), risparmio in ordine decrescente
        risultati.sort(key=lambda r: r[criterio], reverse=(criterio == "risparmio_eur"))
        return risultati

    def getCentralita(self):
        # somma dei km verso tutte le altre arene.
        # Piu' e' basso, piu' la sede e' centrale rispetto al resto della lega
        classifica = []
        for n in self._graph.nodes():
            classifica.append((n, self._graph.degree(n, weight="weight")))
        classifica.sort(key=lambda x: x[1])
        return classifica

    def citta(self, team_id) -> str:
        return self._idMap[team_id].citta

    def getSquadre(self):
        return list(self._squadre.values())

    def getStagioni(self):
        return DAO.getAllStagioni()

    def getParametri(self):
        return self._parametri

    def updateParametro(self, nome, valore):
        self._parametri[nome]["valore"] = valore
