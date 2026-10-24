import time

import flet as ft

colore_evidenziato = ft.colors.with_opacity(0.2, "#F58426")


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

        self._view.update_page()

    # Testata: menu Squadra e Stagione, comuni a tutte le schede

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
        self._view.update_page()

    # Scheda 1: pianificazione

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

        avvio = time.perf_counter()
        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        self._piano = self._model.ottimizzaPiano(
            stagione_id, team_id, max_partite, self._baseline)
        durata = time.perf_counter() - avvio

        m = self._piano.metriche
        elementi = [
            f"Piano ottimizzato (max {max_partite} gare per viaggio), calcolato in {durata:.2f} s",
            self._riepilogo(self._piano),
            "",
            "Dettaglio dei viaggi",
            self._dettaglioViaggi(self._piano),
        ]
        self._scrivi(self._view.lista_piano, elementi)
        r = self._baseline.metriche.km
        self._view.riquadri_piano["risparmio"][0].value = f"-{(r - m.km) / r * 100:.1f}%"
        self._view.riquadri_piano["viaggi"][0].value = str(m.viaggi)
        self._view.riquadri_piano["km"][0].value = f"{m.km:,.0f}"
        self._view.riquadri_piano["costo"][0].value = self._breve(self._piano.costo.totale)
        self._aggiornaRiquadriConfronto()
        self._view.update_page()

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
        self._view.update_page()

    # Scheda 2: confronto con il calendario reale

    def handleAnalizzaReale(self, e):
        selezione = self._selezione()
        if selezione is None:
            return
        stagione_id, team_id = selezione

        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        m = self._baseline.metriche
        elementi = [
            f"Calendario realmente disputato - {team_id}, stagione {stagione_id}",
            self._riepilogo(self._baseline),
            "",
            "Viaggi effettivamente compiuti",
            self._dettaglioViaggi(self._baseline),
        ]
        self._scrivi(self._view.lista_confronto, elementi)
        self._view.testo_confronto.value = (
            f"Baseline: {m.viaggi} viaggi, {m.km:,.0f} km, "
            f"{self._baseline.costo.totale:,.0f} EUR")
        self._aggiornaRiquadriConfronto()
        self._view.update_page()

    def handleConfrontoCompleto(self, e):
        if not self._pronti():
            return
        tabella = self._tabella(["voce", "reale", "ottimizzato", "delta"],
                                self._confrontaPiani(self._baseline, self._piano),
                                numeriche=[1, 2, 3])

        self._scrivi(self._view.lista_confronto, ["TABELLA COMPARATIVA", tabella])
        self._aggiornaRiquadriConfronto()
        self._view.update_page()

    # Scheda 3: analisi

    def handleConfrontoFranchigie(self, e):
        criterio = self._view.dd_criterio.value
        stagione_id = self._view.dd_stagione.value
        if not stagione_id:
            self._view.create_alert("Selezionare una stagione")
            return
        max_partite = int(self._view.txt_max_partite.value)

        avvio = time.perf_counter()
        risultati = self._model.confrontoFranchigie(stagione_id, max_partite, criterio)
        durata = time.perf_counter() - avvio

        # ordine delle colonne di costo: per prima quella del criterio scelto
        ordine_costi = {
            "costo_ottimo": ["costo_ottimo", "costo_reale", "risparmio_eur"],
            "costo_reale": ["costo_reale", "costo_ottimo", "risparmio_eur"],
            "risparmio_eur": ["risparmio_eur", "costo_reale", "costo_ottimo"],
        }
        titoli = {"costo_ottimo": "costo ottimo", "costo_reale": "costo reale",
                  "risparmio_eur": "risparmio EUR"}
        costi = ordine_costi[criterio]

        intestazioni = ["#", "squadra"]
        for chiave in costi:
            intestazioni.append(titoli[chiave])
        intestazioni += ["km reali", "km ottimi", "margine %"]

        righe = []
        for i in range(len(risultati)):
            r = risultati[i]
            riga = [i + 1, r["nome"]]
            for chiave in costi:
                riga.append(f"{r[chiave]:,.0f}")
            riga += [f"{r['km_reali']:,.0f}", f"{r['km_ottimi']:,.0f}",
                     f"{r['risparmio_pct']:.1f}%"]
            righe.append(riga)

        if criterio == "costo_ottimo":
            nota = ("Ordinamento per costo ottimizzato (crescente): l'onere sostenuto "
                    "pianificando al meglio le trasferte.")
        elif criterio == "costo_reale":
            nota = ("Ordinamento per costo reale (crescente): quanto e' costato davvero "
                    "il calendario disputato.")
        else:
            nota = ("Ordinamento per risparmio (decrescente): in cima le franchigie a cui una "
                    "pianificazione migliore farebbe risparmiare di piu'.")

        self._scrivi(self._view.lista_gestionale, [
            f"CONFRONTO FRA LE FRANCHIGIE - stagione {stagione_id}, "
            f"max {max_partite} gare per viaggio ({durata:.1f} s)",
            self._tabella(intestazioni, righe, numeriche=[0, 2, 3, 4, 5, 6, 7]),
            "",
            nota,
        ])
        self._view.update_page()

    def handleCentralita(self, e):
        classifica = self._model.getCentralita()
        altre = len(classifica) - 1
        minimo = classifica[0][1]

        righe = []
        for i in range(len(classifica)):
            arena = classifica[i][0]
            km = classifica[i][1]
            righe.append([i + 1, str(arena), f"{km:,.0f}", f"{km / altre:,.0f}",
                          f"{(km - minimo) / minimo * 100:+.0f}%"])
        tabella = self._tabella(["#", "sede", "km totali", "km medi", "vs prima"], righe,
                                numeriche=[0, 2, 3, 4])

        # la squadra selezionata nel menu viene evidenziata colorando la sua riga
        for i in range(len(classifica)):
            if classifica[i][0].team_id == self._view.dd_squadra.value:
                tabella.rows[i].color = colore_evidenziato

        self._scrivi(self._view.lista_centralita, [
            "CENTRALITA' GEOGRAFICA DELLE SEDI",
            f"somma delle distanze verso le altre {altre} arene (grado pesato del nodo)",
            tabella,
            "",
            "Le sedi in fondo partono svantaggiate: ogni trasferta costa piu' km "
            "a prescindere da come viene pianificata.",
        ])
        self._view.update_page()

    # Metodi di supporto

    def _riempiParametri(self):
        self._view.riga_parametri.controls.clear()
        self._view.txt_parametri.clear()
        for nome, dati in self._model.getParametri().items():
            campo = ft.TextField(label=nome.replace("_", " "), dense=True, width=190,
                                 value=f"{dati['valore']:g}", helper_text=dati["unita"])
            self._view.txt_parametri[nome] = campo
            self._view.riga_parametri.controls.append(campo)

    @staticmethod
    def _scrivi(lista, elementi):
        # elementi: stringhe (diventano testo) oppure tabelle gia' costruite
        lista.controls.clear()
        for elemento in elementi:
            if isinstance(elemento, str):
                lista.controls.append(ft.Text(elemento, size=12, selectable=True))
            else:
                # scroll orizzontale se la tabella e' piu' larga del riquadro
                lista.controls.append(ft.Row([elemento], scroll=ft.ScrollMode.AUTO))

    @staticmethod
    def _tabella(intestazioni, righe, numeriche=()):
        
        colonne = []
        for i in range(len(intestazioni)):
            colonne.append(ft.DataColumn(ft.Text(intestazioni[i], weight=ft.FontWeight.BOLD),
                                         numeric=i in numeriche))
        tabella = ft.DataTable(columns=colonne, column_spacing=25, heading_row_height=36,
                               data_row_min_height=30, data_row_max_height=30)
        for riga in righe:
            celle = []
            for valore in riga:
                celle.append(ft.DataCell(ft.Text(str(valore), size=12)))
            tabella.rows.append(ft.DataRow(cells=celle))
        return tabella

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

    def _riepilogo(self, piano):
        m = piano.metriche
        righe = [
            ("viaggi", m.viaggi),
            ("chilometri", f"{m.km:,.0f}"),
            ("tratte aeree", m.tratte),
            ("trasferimenti", m.trasferimenti),
            ("giorni fuori sede", m.giorni_fuori),
            ("costo stimato", f"{piano.costo.totale:,.0f} EUR"),
        ]
        return self._tabella(["metrica", "valore"], righe, numeriche=[1])

    def _dettaglioViaggi(self, piano):
        # stessa tabella per piano reale e ottimizzato: le date ci sono solo nel reale
        con_date = len(piano.viaggi) > 0 and piano.viaggi[0].data_inizio is not None
        intestazioni = ["#", "km", "costo EUR", "gare"]
        numeriche = [0, 1, 2, 3]
        if con_date:
            intestazioni += ["periodo", "giorni"]
            numeriche.append(5)
        intestazioni.append("percorso")

        sede = self._model.citta(piano.team_id)
        righe = []
        for i in range(len(piano.viaggi)):
            viaggio = piano.viaggi[i]
            costo = self._model.calcolaCosto(self._model.calcolaMetriche([viaggio])).totale
            nomi = [sede]
            for t in viaggio.tappe:
                nomi.append(self._model.citta(t))
            nomi.append(sede)

            riga = [i + 1, f"{viaggio.km:,.0f}", f"{costo:,.0f}", viaggio.partite]
            if con_date:
                riga += [f"{viaggio.data_inizio:%d/%m} - {viaggio.data_fine:%d/%m}",
                         viaggio.giorni_effettivi]
            riga.append(" -> ".join(nomi))
            righe.append(riga)
        return self._tabella(intestazioni, righe, numeriche)
