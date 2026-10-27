import flet as ft

altezza_output = 320


sfondo = "#0B1724"
pannello = "#122337"
bordo = "#2A3B52"
turchese = "#2BA8A6"
oro = "#D9BE8C"
testo = "#E8E2D4"
testo_tenue = "#8FA3B8"
colore_metriche = oro


class View:

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Piano di trasferta NBA - ottimizzazione su grafo pesato"
        self.page.padding = 0
        self.page.bgcolor = sfondo
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.dark_theme = ft.Theme(color_scheme=ft.ColorScheme(primary=turchese, on_primary=sfondo, surface=sfondo, on_surface=testo))
        self._controller = None
        self._schede = []
        self._contenuto = None
        self._pulsanti_schede = []

        self.dd_squadra = None
        self.dd_stagione = None
        self.txt_max_partite = None
        self.riquadri_piano = {}
        self.lista_piano = None
        self.riquadri_confronto = {}
        self.testo_confronto = None
        self.lista_confronto = None
        self.riga_parametri = None
        self.txt_parametri = {}
        self.dd_criterio = None
        self.lista_gestionale = None
        self.lista_centralita = None
        self.btn_calcola = None
        self.stato_piano = None
        self.btn_reale = None
        self.btn_comparativa = None
        self.stato_confronto = None
        self.btn_franchigie = None
        self.stato_franchigie = None
        self.btn_centralita = None
        self.stato_centralita = None

    def set_controller(self, controller):
        self._controller = controller

    def load_interface(self):
        self.dd_squadra = ft.Dropdown(label="Squadra", width=280, dense=True, filled=True,
            bgcolor=pannello, border_color=bordo, border_radius=0,
            on_change=self._controller.handleCambioSelezione)
        self.dd_stagione = ft.Dropdown(label="Stagione", width=160, dense=True, filled=True,
            bgcolor=pannello, border_color=bordo, border_radius=0,
            on_change=self._controller.handleCambioSelezione)

        self._schede = [self._scheda_pianificazione(), self._scheda_confronto(), self._scheda_gestionale()]
        self._contenuto = ft.Container(self._schede[0], expand=True, padding=ft.padding.symmetric(horizontal=25, vertical=15))

        # navigazione nella testata, sotto il titolo: un pulsante per scheda, quello della scheda aperta e' evidenziato
        self._pulsanti_schede = [
            ft.ElevatedButton("Piano", data=0, width=130, style=ft.ButtonStyle(bgcolor=turchese, color=sfondo), on_click=self._cambio_scheda),
            ft.ElevatedButton("Confronto", data=1, width=130, style=ft.ButtonStyle(bgcolor=pannello, color=testo), on_click=self._cambio_scheda),
            ft.ElevatedButton("Analisi", data=2, width=130, style=ft.ButtonStyle(bgcolor=pannello, color=testo), on_click=self._cambio_scheda),
        ]
        self.page.add(ft.Column([self._testata(), self._contenuto], expand=True, spacing=0))
        self._controller.fillDDs()
        self.update_page()

    def _cambio_scheda(self, e):
        indice = e.control.data
        self._contenuto.content = self._schede[indice]
        for pulsante in self._pulsanti_schede:
            
            if pulsante.data == indice:
                pulsante.style = ft.ButtonStyle(bgcolor=turchese, color=sfondo)
            else:
                pulsante.style = ft.ButtonStyle(bgcolor=pannello, color=testo)
        self.page.update()

    def _testata(self):
        return ft.Container(ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("PIANO DI TRASFERTA NBA", size=20, weight=ft.FontWeight.BOLD, color=oro,
                            style=ft.TextStyle(letter_spacing=1.5)),
                    ft.Text("Raggruppamento e sequenziamento dei viaggi su grafo pesato",
                            size=10, color=testo_tenue),
                ], spacing=0, tight=True, expand=True),
                self.dd_squadra, self.dd_stagione,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(self._pulsanti_schede, spacing=10),
        ], spacing=15),
            padding=ft.padding.symmetric(horizontal=25, vertical=15),
            border=ft.border.only(bottom=ft.border.BorderSide(1, oro)))

    def _scheda_pianificazione(self):
        # menu a tendina con il numero massimo di gare per viaggio, da 1 a 7
        self.txt_max_partite = ft.Dropdown(width=100, dense=True, filled=True, value="5",
            bgcolor=pannello, border_color=bordo, border_radius=0,
            on_change=self._controller.handleCambioMaxPartite)
        for n in range(1, 8):
            self.txt_max_partite.options.append(ft.dropdown.Option(key=str(n), text=str(n)))
        self.riga_parametri = ft.Row(controls=[], wrap=True, spacing=10, run_spacing=10)
        self.lista_piano = ft.ListView(spacing=0, padding=10)
        riquadri = self._crea_riquadri(self.riquadri_piano, [
            ("viaggi", "viaggi"),
            ("km", "chilometri percorsi"),
            ("costo", "costo stimato, EUR"),
        ])
        self.btn_calcola = ft.ElevatedButton("Calcola piano ottimizzato", bgcolor=turchese, color=sfondo,
                                             on_click=self._controller.handleCalcolaPiano)
        self.stato_piano = ft.Text("", size=15, italic=True, color=testo_tenue)
        return ft.Column([
            self._didascalia("Raggruppa le trasferte in viaggi e ne ordina le tappe. Il piano "
                             "non assegna date."),
            self._pannello([
                self._titolo_gruppo("Assunti economici"),
                self.riga_parametri,
                ft.Row([ft.Text("Max gare per viaggio", weight=ft.FontWeight.BOLD),
                        self.txt_max_partite], wrap=True, spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    self.btn_calcola,
                    ft.OutlinedButton("Salva parametri", on_click=self._controller.handleSalvaParametri),
                    self.stato_piano,
                ], wrap=True, spacing=10, run_spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
            riquadri,
            self._cornice(self.lista_piano),
        ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    def _scheda_confronto(self):
        self.testo_confronto = ft.Text("", weight=ft.FontWeight.BOLD, size=15)
        self.lista_confronto = ft.ListView(spacing=0, padding=10)
        riquadri = self._crea_riquadri(self.riquadri_confronto, [
            ("km_reali", "calendario reale"),
            ("km_ottimi", "piano ottimizzato"),
            ("risparmio_km", "variazione km vs reale"),
            ("risparmio_eur", "EUR risparmiati"),
        ])
        self.btn_reale = ft.OutlinedButton("Analizza calendario reale", on_click=self._controller.handleAnalizzaReale)
        self.btn_comparativa = ft.ElevatedButton("Tabella comparativa completa",
                                                 bgcolor=turchese, color=sfondo,
                                                 on_click=self._controller.handleConfrontoCompleto)
        self.stato_confronto = ft.Text("", size=15, italic=True, color=testo_tenue)
        return ft.Column([
            self._didascalia("Confronta il calendario realmente disputato con il piano costruito nella sezione Piano."),
            ft.Row([
                self.btn_reale,
                self.btn_comparativa,
                self.stato_confronto,], wrap=True, spacing=10, run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
                riquadri,
                self.testo_confronto,
                self._cornice(self.lista_confronto),
                ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    def _scheda_gestionale(self):
        self.dd_criterio = ft.Dropdown(label="Ordina per", width=230, dense=True, filled=True,
            bgcolor=pannello, border_color=bordo, border_radius=0,
            value="costo_ottimo", options=[
                ft.dropdown.Option(key="costo_ottimo", text="Costo ottimizzato"),
                ft.dropdown.Option(key="costo_reale", text="Costo reale"),
                ft.dropdown.Option(key="risparmio_eur", text="Risparmio"),
            ])
        self.lista_gestionale = ft.ListView(spacing=0, padding=10)
        self.lista_centralita = ft.ListView(spacing=0, padding=10)
        self.btn_franchigie = ft.ElevatedButton("Classifica franchigie", bgcolor=turchese, color=sfondo,on_click=self._controller.handleConfrontoFranchigie)
        self.stato_franchigie = ft.Text("", size=15, italic=True, color=testo_tenue)
        self.btn_centralita = ft.OutlinedButton("Classifica delle sedi", on_click=self._controller.handleCentralita)
        self.stato_centralita = ft.Text("", size=15, italic=True, color=testo_tenue)
        return ft.Column([
            self._didascalia("Quali franchigie hanno il margine di miglioramento maggiore e quanto "
                             "pesa la posizione geografica della sede."),
            self._titolo_gruppo("Confronto trasversale"),
            ft.Row([
                self.btn_franchigie,
                self.dd_criterio,
                self.stato_franchigie,
            ], wrap=True, spacing=10, run_spacing=10,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self._cornice(self.lista_gestionale),
            self._titolo_gruppo("Centralita' geografica delle sedi"),
            ft.Row([
                self.btn_centralita,
                self.stato_centralita,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self._cornice(self.lista_centralita),
        ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    @staticmethod
    def _didascalia(testo):
        return ft.Text(testo, italic=True, size=15, color=testo_tenue)

    @staticmethod
    def _titolo_gruppo(testo):
        return ft.Text(testo.upper(), size=10, weight=ft.FontWeight.BOLD, color=turchese, style=ft.TextStyle(letter_spacing=1.5))

    @staticmethod
    def _pannello(controlli):
        return ft.Container(ft.Column(controlli, spacing=10), padding=20, bgcolor=pannello, border=ft.border.all(1, bordo))

    @staticmethod
    def _cornice(contenuto):
        return ft.Container(contenuto, height=altezza_output)

    def _crea_riquadri(self, deposito, definizioni):
        # un unico riquadro con tutti i dati affiancati, separati da linee verticali
        riga = ft.Row(spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        for chiave, iniziale in definizioni:
            valore = ft.Text("—", size=25, weight=ft.FontWeight.BOLD, color=colore_metriche)
            etichetta = ft.Text(iniziale, size=10, color=testo_tenue)
            deposito[chiave] = (valore, etichetta, iniziale)
            if len(riga.controls) > 0:
                riga.controls.append(ft.Container(ft.VerticalDivider(width=40, color=bordo), height=50))
            riga.controls.append(ft.Container(ft.Column([valore, etichetta], spacing=0, tight=True),
                                              expand=True))
        return ft.Container(riga, padding=20, bgcolor=pannello, border=ft.border.all(1, bordo))


    def update_page(self):
        self.page.update()

    def create_alert(self, testo):
        self.page.snack_bar = ft.SnackBar(ft.Text(testo))
        self.page.snack_bar.open = True
        self.page.update()
