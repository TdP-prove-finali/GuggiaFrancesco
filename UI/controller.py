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

        
        self._view.riga_parametri.controls.clear()
        self._view.txt_parametri.clear()
        for nome, dati in self._model.getParametri().items():
            campo = ft.TextField(label=nome.replace("_", " "), dense=True, width=190,
                                 value=f"{dati['valore']:g}", helper_text=dati["unita"])
            self._view.txt_parametri[nome] = campo
            self._view.riga_parametri.controls.append(campo)

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
        stagione_id = self._view.dd_stagione.value
        team_id = self._view.dd_squadra.value
        if not stagione_id or not team_id:
            self._view.create_alert("Selezionare squadra e stagione")
            return
        max_partite = int(self._view.txt_max_partite.value)

        avvio = time.perf_counter()
        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        self._piano = self._model.ottimizzaPiano(
            stagione_id, team_id, max_partite, self._baseline)
        durata = time.perf_counter() - avvio
        m = self._piano.metriche


        voci = [
            ("viaggi", m.viaggi),
            ("chilometri", f"{m.km:,.0f}"),
            ("tratte aeree", m.tratte),
            ("trasferimenti", m.trasferimenti),
            ("giorni fuori sede", m.giorni_fuori),
            ("costo stimato", f"{self._piano.costo.totale:,.0f} EUR"),
        ]
        riepilogo = self._tabella(["metrica", "valore"], voci, numeriche=[1])


        sede = self._model.citta(self._piano.team_id)
        righe = []
        for i in range(len(self._piano.viaggi)):
            viaggio = self._piano.viaggi[i]
            costo = self._model.calcolaCosto(self._model.calcolaMetriche([viaggio])).totale
            nomi = [sede]
            for t in viaggio.tappe:
                nomi.append(self._model.citta(t))
            nomi.append(sede)
            righe.append([i + 1, f"{viaggio.km:,.0f}", f"{costo:,.0f}", viaggio.partite,
                          " -> ".join(nomi)])
        dettaglio = self._tabella(["#", "km", "costo EUR", "gare", "percorso"], righe,
                                  numeriche=[0, 1, 2, 3])

        lista = self._view.lista_piano
        lista.controls.clear()
        lista.controls.append(ft.Text(
            f"Piano ottimizzato (max {max_partite} gare per viaggio), calcolato in {durata:.2f} s",
            size=12))
        lista.controls.append(ft.Row([riepilogo], scroll=ft.ScrollMode.AUTO))
        lista.controls.append(ft.Text("", size=12))
        lista.controls.append(ft.Text("Dettaglio dei viaggi", size=12))
        lista.controls.append(ft.Row([dettaglio], scroll=ft.ScrollMode.AUTO))


        r = self._baseline.metriche.km
        costo_totale = self._piano.costo.totale
        if costo_totale >= 1_000_000:
            costo_breve = f"{costo_totale / 1_000_000:.2f} M"
        elif costo_totale >= 1_000:
            costo_breve = f"{costo_totale / 1_000:,.0f} k"
        else:
            costo_breve = f"{costo_totale:,.0f}"
        self._view.riquadri_piano["risparmio"][0].value = f"-{(r - m.km) / r * 100:.1f}%"
        self._view.riquadri_piano["viaggi"][0].value = str(m.viaggi)
        self._view.riquadri_piano["km"][0].value = f"{m.km:,.0f}"
        self._view.riquadri_piano["costo"][0].value = costo_breve


        o = self._piano.metriche
        rb = self._baseline.metriche
        risparmio = rb.km - o.km
        euro = self._baseline.costo.totale - self._piano.costo.totale
        if abs(euro) >= 1_000_000:
            euro_breve = f"{euro / 1_000_000:.2f} M"
        elif abs(euro) >= 1_000:
            euro_breve = f"{euro / 1_000:,.0f} k"
        else:
            euro_breve = f"{euro:,.0f}"
        rc = self._view.riquadri_confronto
        rc["km_reali"][0].value = f"{rb.km:,.0f}"
        rc["km_reali"][1].value = "km, calendario reale"
        rc["km_ottimi"][0].value = f"{o.km:,.0f}"
        rc["km_ottimi"][1].value = "km, piano ottimizzato"
        rc["risparmio_km"][0].value = f"{risparmio:,.0f}"
        rc["risparmio_km"][1].value = f"km risparmiati ({risparmio / rb.km * 100:.1f} %)"
        rc["risparmio_eur"][0].value = euro_breve
        rc["risparmio_eur"][1].value = "EUR risparmiati"
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


        self._view.riga_parametri.controls.clear()
        self._view.txt_parametri.clear()
        for nome, dati in self._model.getParametri().items():
            campo = ft.TextField(label=nome.replace("_", " "), dense=True, width=190,
                                 value=f"{dati['valore']:g}", helper_text=dati["unita"])
            self._view.txt_parametri[nome] = campo
            self._view.riga_parametri.controls.append(campo)

        self._view.create_alert("Parametri salvati, ricalcolare i piani")
        self._view.update_page()

    # Scheda 2: confronto con il calendario reale

    def handleAnalizzaReale(self, e):
        stagione_id = self._view.dd_stagione.value
        team_id = self._view.dd_squadra.value
        if not stagione_id or not team_id:
            self._view.create_alert("Selezionare squadra e stagione")
            return

        self._baseline = self._model.analizzaBaseline(stagione_id, team_id)
        m = self._baseline.metriche


        voci = [
            ("viaggi", m.viaggi),
            ("chilometri", f"{m.km:,.0f}"),
            ("tratte aeree", m.tratte),
            ("trasferimenti", m.trasferimenti),
            ("giorni fuori sede", m.giorni_fuori),
            ("costo stimato", f"{self._baseline.costo.totale:,.0f} EUR"),
        ]
        riepilogo = self._tabella(["metrica", "valore"], voci, numeriche=[1])

        # tabella dettaglio viaggi, con le date del calendario reale
        sede = self._model.citta(self._baseline.team_id)
        righe = []
        for i in range(len(self._baseline.viaggi)):
            viaggio = self._baseline.viaggi[i]
            costo = self._model.calcolaCosto(self._model.calcolaMetriche([viaggio])).totale
            nomi = [sede]
            for t in viaggio.tappe:
                nomi.append(self._model.citta(t))
            nomi.append(sede)
            righe.append([i + 1, f"{viaggio.km:,.0f}", f"{costo:,.0f}", viaggio.partite,
                          f"{viaggio.data_inizio:%d/%m} - {viaggio.data_fine:%d/%m}",
                          viaggio.giorni_effettivi, " -> ".join(nomi)])
        dettaglio = self._tabella(["#", "km", "costo EUR", "gare", "periodo", "giorni",
                                   "percorso"], righe, numeriche=[0, 1, 2, 3, 5])

        lista = self._view.lista_confronto
        lista.controls.clear()
        lista.controls.append(ft.Text(
            f"Calendario realmente disputato - {team_id}, stagione {stagione_id}", size=12))
        lista.controls.append(ft.Row([riepilogo], scroll=ft.ScrollMode.AUTO))
        lista.controls.append(ft.Text("", size=12))
        lista.controls.append(ft.Text("Viaggi effettivamente compiuti", size=12))
        lista.controls.append(ft.Row([dettaglio], scroll=ft.ScrollMode.AUTO))

        self._view.testo_confronto.value = (
            f"Baseline: {m.viaggi} viaggi, {m.km:,.0f} km, "
            f"{self._baseline.costo.totale:,.0f} EUR")


        rc = self._view.riquadri_confronto
        rc["km_reali"][0].value = f"{m.km:,.0f}"
        rc["km_reali"][1].value = "km, calendario reale"
        if self._piano is not None:
            o = self._piano.metriche
            risparmio = m.km - o.km
            euro = self._baseline.costo.totale - self._piano.costo.totale
            if abs(euro) >= 1_000_000:
                euro_breve = f"{euro / 1_000_000:.2f} M"
            elif abs(euro) >= 1_000:
                euro_breve = f"{euro / 1_000:,.0f} k"
            else:
                euro_breve = f"{euro:,.0f}"
            rc["km_ottimi"][0].value = f"{o.km:,.0f}"
            rc["km_ottimi"][1].value = "km, piano ottimizzato"
            rc["risparmio_km"][0].value = f"{risparmio:,.0f}"
            rc["risparmio_km"][1].value = f"km risparmiati ({risparmio / m.km * 100:.1f} %)"
            rc["risparmio_eur"][0].value = euro_breve
            rc["risparmio_eur"][1].value = "EUR risparmiati"
        self._view.update_page()

    def handleConfrontoCompleto(self, e):
        if self._baseline is None or self._piano is None:
            self._view.create_alert("Calcolare prima il piano ottimizzato nella sezione 1")
            return

        r, o = self._baseline.metriche, self._piano.metriche
        cr, co = self._baseline.costo, self._piano.costo

        voci = [
            ("Chilometri percorsi", r.km, o.km, f"{r.km:,.0f}", f"{o.km:,.0f}"),
            ("Numero di viaggi", r.viaggi, o.viaggi, str(r.viaggi), str(o.viaggi)),
            ("Tratte aeree", r.tratte, o.tratte, str(r.tratte), str(o.tratte)),
            ("Trasferimenti fra gare", r.trasferimenti, o.trasferimenti,
             str(r.trasferimenti), str(o.trasferimenti)),
            ("Giorni fuori sede", r.giorni_fuori, o.giorni_fuori,
             str(r.giorni_fuori), str(o.giorni_fuori)),
            ("Costo voli", cr.volo_fisso + cr.volo_km, co.volo_fisso + co.volo_km,
             f"{cr.volo_fisso + cr.volo_km:,.0f} EUR", f"{co.volo_fisso + co.volo_km:,.0f} EUR"),
            ("Costo alberghi", cr.hotel, co.hotel,
             f"{cr.hotel:,.0f} EUR", f"{co.hotel:,.0f} EUR"),
            ("Diarie", cr.diaria, co.diaria,
             f"{cr.diaria:,.0f} EUR", f"{co.diaria:,.0f} EUR"),
            ("Costo totale", cr.totale, co.totale,
             f"{cr.totale:,.0f} EUR", f"{co.totale:,.0f} EUR"),
        ]

        righe = []
        for voce, reale, ottimo, testo_reale, testo_ottimo in voci:
            # variazione percentuale del piano rispetto al reale
            delta = "" if not reale else f"{(ottimo - reale) / reale * 100:+.1f}%"
            righe.append([voce, testo_reale, testo_ottimo, delta])
        tabella = self._tabella(["voce", "reale", "ottimizzato", "delta"], righe,
                                numeriche=[1, 2, 3])

        lista = self._view.lista_confronto
        lista.controls.clear()
        lista.controls.append(ft.Text("TABELLA COMPARATIVA", size=12))
        lista.controls.append(ft.Row([tabella], scroll=ft.ScrollMode.AUTO))

        # riquadri della scheda Confronto
        risparmio = r.km - o.km
        euro = cr.totale - co.totale
        if abs(euro) >= 1_000_000:
            euro_breve = f"{euro / 1_000_000:.2f} M"
        elif abs(euro) >= 1_000:
            euro_breve = f"{euro / 1_000:,.0f} k"
        else:
            euro_breve = f"{euro:,.0f}"
        rc = self._view.riquadri_confronto
        rc["km_reali"][0].value = f"{r.km:,.0f}"
        rc["km_reali"][1].value = "km, calendario reale"
        rc["km_ottimi"][0].value = f"{o.km:,.0f}"
        rc["km_ottimi"][1].value = "km, piano ottimizzato"
        rc["risparmio_km"][0].value = f"{risparmio:,.0f}"
        rc["risparmio_km"][1].value = f"km risparmiati ({risparmio / r.km * 100:.1f} %)"
        rc["risparmio_eur"][0].value = euro_breve
        rc["risparmio_eur"][1].value = "EUR risparmiati"
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
        tabella = self._tabella(intestazioni, righe, numeriche=[0, 2, 3, 4, 5, 6, 7])

        if criterio == "costo_ottimo":
            nota = ("Ordinamento per costo ottimizzato (crescente): l'onere sostenuto "
                    "pianificando al meglio le trasferte.")
        elif criterio == "costo_reale":
            nota = ("Ordinamento per costo reale (crescente): quanto e' costato davvero "
                    "il calendario disputato.")
        else:
            nota = ("Ordinamento per risparmio (decrescente): in cima le franchigie a cui una "
                    "pianificazione migliore farebbe risparmiare di piu'.")

        lista = self._view.lista_gestionale
        lista.controls.clear()
        lista.controls.append(ft.Text(
            f"CONFRONTO FRA LE FRANCHIGIE - stagione {stagione_id}, "
            f"max {max_partite} gare per viaggio ({durata:.1f} s)", size=12))
        lista.controls.append(ft.Row([tabella], scroll=ft.ScrollMode.AUTO))
        lista.controls.append(ft.Text("", size=12))
        lista.controls.append(ft.Text(nota, size=12))
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

        lista = self._view.lista_centralita
        lista.controls.clear()
        lista.controls.append(ft.Text("CENTRALITA' GEOGRAFICA DELLE SEDI", size=12))
        lista.controls.append(ft.Text(
            f"somma delle distanze verso le altre {altre} arene (grado pesato del nodo)",
            size=12))
        lista.controls.append(ft.Row([tabella], scroll=ft.ScrollMode.AUTO))
        lista.controls.append(ft.Text("", size=12))
        lista.controls.append(ft.Text(
            "Le sedi in fondo partono svantaggiate: ogni trasferta costa piu' km "
            "a prescindere da come viene pianificata.", size=12))
        self._view.update_page()

    # metodo di supporto che costruisce una DataTable a partire da titoli e righe

    @staticmethod
    def _tabella(intestazioni, righe, numeriche=()):
        # numeriche: indici delle colonne con numeri, che Flet allinea a destra da solo
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
