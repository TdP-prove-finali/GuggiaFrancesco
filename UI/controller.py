import time

import flet as ft

monospazio = "Consolas"
larghezza_voce = 32
larghezza_colonna = 18


class Controller:

    def __init__(self, view, model):
        self._view = view
        self._model = model
        self._baseline = None
        self._piano = None

    def fillDDs(self):
        self._model.buildGraph()
        nodi, archi = self._model.getGraphDetails()

        for squadra in self._model.getSquadre():
            self._view.dd_squadra.options.append(
                ft.dropdown.Option(key=squadra.team_id, text=f"{squadra.nome} ({squadra.team_id})"))

        stagioni = self._model.getStagioni()
        for stagione in stagioni:
            self._view.dd_stagione.options.append(
                ft.dropdown.Option(key=stagione.stagione_id, text=stagione.stagione_id))
        if stagioni:
            self._view.dd_stagione.value = stagioni[0].stagione_id

        self._riempiParametri()

        self._view.testo_stato.value = f"grafo pronto: {nodi} arene, {archi} archi"
        self._view.update_page()

    # Scheda 1: pianificazione

    def handleCambioSelezione(self, e):
        self._baseline = None
        self._piano = None
        self._view.lista_piano.controls.clear()
        self._view.lista_confronto.controls.clear()
        self._view.testo_confronto.value = ""
        for riquadri in (self._view.riquadri_piano, self._view.riquadri_confronto):
            for chiave in riquadri:
                riquadri[chiave][0].value = "—"
                riquadri[chiave][1].value = riquadri[chiave][2]

        if e is not None and e.control is self._view.dd_stagione:
            self._view.lista_gestionale.controls.clear()
        self._view.testo_stato.value = "selezione cambiata, premere Calcola piano"
        self._view.update_page()

    def handleSlider(self, e):
        # ricalcola solo se c'e' gia' un piano per la selezione corrente
        if self._piano is not None:
            self.handleCalcolaPiano(e)

    def handleCalcolaPiano(self, e):
        selezione = self._selezione()
        if selezione is None:
            return
        stagione_id, team_id = selezione
        max_partite = int(self._view.txt_max_partite.value)

        self._view.testo_stato.value = "ottimizzazione in corso..."
        self._view.update_page()
        avvio = time.perf_counter()
        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        self._piano = self._model.ottimizzaPiano(
            stagione_id, team_id, max_partite, self._baseline)
        durata = time.perf_counter() - avvio

        m = self._piano.metriche
        righe = [
            f"Piano ottimizzato (max {max_partite} gare per viaggio)",
            f"calcolato in {durata:.2f} s",
            "",
            f"  viaggi                 {m.viaggi}",
            f"  chilometri             {m.km:,.0f}",
            f"  tratte aeree           {m.tratte}",
            f"  trasferimenti          {m.trasferimenti}",
            f"  giorni fuori sede      {m.giorni_fuori}",
            f"  costo stimato          {self._piano.costo.totale:,.0f} EUR",
            "",
            "Dettaglio dei viaggi",
            "",
        ]
        righe.extend(self._dettaglioViaggi(self._piano))
        self._scrivi(self._view.lista_piano, righe)
        r = self._baseline.metriche.km
        self._view.riquadri_piano["risparmio"][0].value = f"-{(r - m.km) / r * 100:.1f}%"
        self._view.riquadri_piano["viaggi"][0].value = str(m.viaggi)
        self._view.riquadri_piano["km"][0].value = f"{m.km:,.0f}"
        self._view.riquadri_piano["costo"][0].value = self._breve(self._piano.costo.totale)
        self._aggiornaRiquadriConfronto()
        self._view.testo_stato.value = f"piano pronto ({m.viaggi} viaggi, {m.km:,.0f} km)"
        self._view.update_page()

    # Scheda 2: confronto con il calendario reale

    def handleAnalizzaReale(self, e):
        selezione = self._selezione()
        if selezione is None:
            return
        stagione_id, team_id = selezione

        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        m = self._baseline.metriche
        righe = [
            f"Calendario realmente disputato - {team_id}, stagione {stagione_id}",
            "",
            f"  viaggi                 {m.viaggi}",
            f"  trasferte              {m.partite}",
            f"  chilometri             {m.km:,.0f}",
            f"  tratte aeree           {m.tratte}",
            f"  trasferimenti          {m.trasferimenti}",
            f"  giorni fuori sede      {m.giorni_fuori}",
            f"  gare ravvicinate       {m.back_to_back}  (giorni consecutivi, sede diversa)",
            f"  costo stimato          {self._baseline.costo.totale:,.0f} EUR",
            "",
            "Viaggi effettivamente compiuti",
            "",
        ]
        righe.extend(self._dettaglioViaggi(self._baseline))
        self._scrivi(self._view.lista_confronto, righe)
        self._view.testo_confronto.value = (
            f"Baseline: {m.viaggi} viaggi, {m.km:,.0f} km, "
            f"{self._baseline.costo.totale:,.0f} EUR")
        self._aggiornaRiquadriConfronto()
        self._view.testo_stato.value = "calendario reale analizzato"
        self._view.update_page()

    def handleConfrontoCompleto(self, e):
        if not self._pronti():
            return
        righe = ["TABELLA COMPARATIVA", "", self._intestazione()]
        for r in self._confrontaPiani(self._baseline, self._piano):
            righe.append(self._riga(r[0], r[1], r[2], r[3]))

        self._scrivi(self._view.lista_confronto, righe)
        self._aggiornaRiquadriConfronto()
        self._view.testo_stato.value = "tabella comparativa pronta"
        self._view.update_page()

    # Scheda 3: analisi e confornto

    def handleSalvaParametri(self, e):
        try:
            for nome, campo in self._view.txt_parametri.items():
                self._model.updateParametro(nome, float(campo.value.replace(",", ".")))
        except ValueError:
            self._view.create_alert("I parametri devono essere numerici")
            return

        self._baseline = None
        self._piano = None

        self._riempiParametri()

        self._view.create_alert("Parametri salvati, ricalcolare i piani")
        self._view.testo_stato.value = "parametri di costo aggiornati"
        self._view.update_page()

    def handleConfrontoFranchigie(self, e):
        self._confrontoFranchigie("costo_ottimo")

    def handleConfrontoFranchigieReale(self, e):
        self._confrontoFranchigie("costo_reale")

    def _confrontoFranchigie(self, criterio):
        stagione_id = self._view.dd_stagione.value
        if not stagione_id:
            self._view.create_alert("Selezionare una stagione")
            return
        max_partite = int(self._view.txt_max_partite.value)

        self._view.testo_stato.value = "confronto sulle 30 franchigie, richiede qualche secondo..."
        self._view.update_page()
        avvio = time.perf_counter()
        risultati = self._model.confrontoFranchigie(stagione_id, max_partite, criterio)
        durata = time.perf_counter() - avvio

        righe = [
            f"CONFRONTO FRA LE FRANCHIGIE - stagione {stagione_id}",
            f"max {max_partite} gare per viaggio ({durata:.1f} s)",
            "",
            f"{'#':>3}  {'squadra':<26}{'km reali':>11}{'km ottimi':>11}{'margine %':>11}"
            f"{'costo reale':>14}{'costo ottimo':>14}{'risparmio EUR':>15}",
            "-" * 107,
        ]
        for i in range(len(risultati)):
            posizione = i + 1
            r = risultati[i]
            righe.append(f"{posizione:>3}  {r['nome'][:26]:<26}{r['km_reali']:>11,.0f}"
                         f"{r['km_ottimi']:>11,.0f}{r['risparmio_pct']:>10.1f}%"
                         f"{r['costo_reale']:>14,.0f}{r['costo_ottimo']:>14,.0f}"
                         f"{r['risparmio_eur']:>15,.0f}")
        righe += [
            "-" * 107,
            "",
        ]
        if criterio == "costo_ottimo":
            righe += ["Ordinamento per costo ottimizzato: l'onere che resta anche pianificando al",
                      "meglio, quindi dipende solo dalla posizione della sede."]
        else:
            righe += ["Ordinamento per costo reale: quanto e' costato davvero il calendario disputato,",
                      "somma dello svantaggio geografico e della qualita' del calendario."]
        righe.append("La colonna 'risparmio EUR' indica dove la pianificazione renderebbe di piu'.")

        self._scrivi(self._view.lista_gestionale, righe)
        self._view.testo_stato.value = "confronto fra franchigie completato"
        self._view.update_page()

    def handleCentralita(self, e):
        classifica = self._model.getCentralita()
        altre = len(classifica) - 1
        minimo = classifica[0][1]
        righe = [
            "CENTRALITA' GEOGRAFICA DELLE SEDI",
            f"somma delle distanze verso le altre {altre} arene (grado pesato del nodo)",
            "",
            f"{'#':>3}  {'sede':<30}{'km totali':>12}{'km medi':>10}{'vs prima':>11}",
            "-" * 66,
        ]
        for i in range(len(classifica)):
            arena = classifica[i][0]
            km = classifica[i][1]
            # la squadra selezionata nel menu viene evidenziata con una freccia
            segno = ">" if arena.team_id == self._view.dd_squadra.value else " "
            righe.append(f"{segno}{i + 1:>2}  {str(arena):<30}{km:>12,.0f}"
                         f"{km / altre:>10,.0f}{(km - minimo) / minimo * 100:>+10.0f}%")
        righe += [
            "-" * 66,
            "",
            "Le sedi in fondo partono svantaggiate: ogni trasferta costa piu' km",
            "a prescindere da come viene pianificata.",
        ]
        self._scrivi(self._view.lista_centralita, righe)
        self._view.testo_stato.value = "classifica di centralita' pronta"
        self._view.update_page()

    def _riempiParametri(self):
        self._view.riga_parametri.controls.clear()
        self._view.txt_parametri.clear()
        for nome, dati in self._model.getParametri().items():
            campo = ft.TextField(label=nome.replace("_", " "), dense=True, width=190,
                                 value=f"{dati['valore']:g}", helper_text=dati["unita"])
            self._view.txt_parametri[nome] = campo
            self._view.riga_parametri.controls.append(campo)

    @staticmethod
    def _scrivi(lista, righe):
        lista.controls.clear()
        for riga in righe:
            lista.controls.append(ft.Text(riga, font_family=monospazio, size=12, selectable=True))

    def _selezione(self):
        stagione_id = self._view.dd_stagione.value
        team_id = self._view.dd_squadra.value
        if not stagione_id or not team_id:
            self._view.create_alert("Selezionare squadra e stagione")
            return None
        return stagione_id, team_id

    def _aggiornaRiquadriConfronto(self):
        valori = {}
        if self._baseline is not None:
            valori["km_reali"] = (f"{self._baseline.metriche.km:,.0f}",
                                  "km, calendario reale")
        if self._baseline is not None and self._piano is not None:
            r, o = self._baseline.metriche, self._piano.metriche
            risparmio = r.km - o.km
            euro = self._baseline.costo.totale - self._piano.costo.totale
            valori["km_ottimi"] = (f"{o.km:,.0f}", "km, piano ottimizzato")
            valori["risparmio_km"] = (f"{risparmio:,.0f}",
                                      f"km risparmiati ({risparmio / r.km * 100:.1f} %)")
            valori["risparmio_eur"] = (self._breve(euro), "EUR risparmiati")
        for chiave in valori:
            valore = valori[chiave][0]
            etichetta = valori[chiave][1]
            self._view.riquadri_confronto[chiave][0].value = valore
            self._view.riquadri_confronto[chiave][1].value = etichetta

    @staticmethod
    def _breve(valore):
        if abs(valore) >= 1_000_000:
            return f"{valore / 1_000_000:.2f} M"
        if abs(valore) >= 1_000:
            return f"{valore / 1_000:,.0f} k"
        return f"{valore:,.0f}"

    def _pronti(self):
        if self._baseline is None or self._piano is None:
            self._view.create_alert("Calcolare prima il piano ottimizzato nella sezione 1")
            return False
        return True

    @staticmethod
    def _intestazione():
        return (f"{'':<{larghezza_voce}}{'reale':>{larghezza_colonna}}"
                f"{'ottimizzato':>{larghezza_colonna}}{'delta':>12}\n"
                + "-" * (larghezza_voce + 2 * larghezza_colonna + 12))

    @staticmethod
    def _riga(voce, reale, ottimo, delta):
        return (f"{str(voce):<{larghezza_voce}}{str(reale):>{larghezza_colonna}}"
                f"{str(ottimo):>{larghezza_colonna}}{str(delta):>12}")

    @staticmethod
    def _delta(reale, ottimo):
        return "" if not reale else f"{(ottimo - reale) / reale * 100:+.1f}%"

    def _confrontaPiani(self, reale, ottimizzato):
        r, o = reale.metriche, ottimizzato.metriche
        cr, co = reale.costo, ottimizzato.costo
        return [
            ("Chilometri percorsi", f"{r.km:,.0f}", f"{o.km:,.0f}", self._delta(r.km, o.km)),
            ("Numero di viaggi", r.viaggi, o.viaggi, self._delta(r.viaggi, o.viaggi)),
            ("Tratte aeree", r.tratte, o.tratte, self._delta(r.tratte, o.tratte)),
            ("Trasferimenti fra gare", r.trasferimenti, o.trasferimenti,
             self._delta(r.trasferimenti, o.trasferimenti)),
            ("Giorni fuori sede", r.giorni_fuori, o.giorni_fuori,
             self._delta(r.giorni_fuori, o.giorni_fuori)),
            ("Costo voli", f"{cr.volo_fisso + cr.volo_km:,.0f} EUR",
             f"{co.volo_fisso + co.volo_km:,.0f} EUR",
             self._delta(cr.volo_fisso + cr.volo_km, co.volo_fisso + co.volo_km)),
            ("Costo alberghi", f"{cr.hotel:,.0f} EUR", f"{co.hotel:,.0f} EUR",
             self._delta(cr.hotel, co.hotel)),
            ("Diarie", f"{cr.diaria:,.0f} EUR", f"{co.diaria:,.0f} EUR",
             self._delta(cr.diaria, co.diaria)),
            ("Costo totale", f"{cr.totale:,.0f} EUR", f"{co.totale:,.0f} EUR",
             self._delta(cr.totale, co.totale)),
        ]

    def _dettaglioViaggi(self, piano):
        righe = []
        sede = self._model.citta(piano.team_id)
        for i in range(len(piano.viaggi)):
            numero = i + 1
            viaggio = piano.viaggi[i]

            costo = self._model.calcolaCosto(self._model.calcolaMetriche([viaggio])).totale
            nomi = []
            for t in viaggio.tappe:
                nomi.append(self._model.citta(t))
            citta = " -> ".join(nomi)
            periodo = ""
            if viaggio.data_inizio:
                periodo = (f"  [{viaggio.data_inizio:%d/%m} - {viaggio.data_fine:%d/%m}, "
                           f"{viaggio.giorni_effettivi} giorni]")
            righe.append(f"{numero:2}. {viaggio.km:7,.0f} km  {costo:>11,.0f} EUR  "
                         f"{viaggio.partite} gare{periodo}")
            righe.append(f"    {sede} -> {citta} -> {sede}")
            righe.append("")
        return righe
