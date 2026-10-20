import flet as ft

altezza_output = 320

# colori utilizzati per rendere la view piacevole all'occhio e suddividere le varie metriche
sfondo = "#0E1525"
pannello = "#162036"
fondo_output = "#0A101C"
bordo = "#26324D"
testo_tenue = "#93A1BC"
accento = "#F58426"
colore_percorso = "#F58426"
colore_viaggi = "#E4572E"
colore_denaro = "#2EC4B6"
colore_storico = "#8D99AE"
colore_risparmio = "#57CC99"


class View:

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Piano di trasferta NBA - ottimizzazione su grafo pesato"
        self.page.padding = 0
        self.page.bgcolor = sfondo
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.dark_theme = ft.Theme(color_scheme_seed=accento)
        self._controller = None
        self._schede = []
        self._contenuto = None

        self.dd_squadra = None
        self.dd_stagione = None
        self.testo_stato = None
        self.txt_max_partite = None
        self.riquadri_piano = {}
        self.lista_piano = None
        self.riquadri_confronto = {}
        self.testo_confronto = None
        self.lista_confronto = None
        self.riga_parametri = None
        self.txt_parametri = {}
        self.lista_gestionale = None
        self.lista_centralita = None

    def set_controller(self, controller):
        self._controller = controller

    def load_interface(self):
        self.dd_squadra = ft.Dropdown(label="Squadra", width=280, dense=True, filled=True,
            bgcolor=pannello, border_color=bordo, border_radius=10,
            prefix_icon=ft.icons.GROUPS, on_change=self._controller.handleCambioSelezione)
        self.dd_stagione = ft.Dropdown(label="Stagione", width=160, dense=True, filled=True,
            bgcolor=pannello, border_color=bordo, border_radius=10,
            prefix_icon=ft.icons.CALENDAR_MONTH, on_change=self._controller.handleCambioSelezione)
        self.testo_stato = ft.Text("", italic=True, size=10, color=testo_tenue)

        self._schede = [self._scheda_pianificazione(), self._scheda_confronto(),
                        self._scheda_gestionale()]
        self._contenuto = ft.Container(self._schede[0], expand=True,
                                       padding=ft.padding.symmetric(horizontal=25, vertical=15))

        menu = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=95,
            bgcolor=pannello, indicator_color=ft.colors.with_opacity(0.25, accento),
            leading=ft.Container(ft.Icon(ft.icons.SPORTS_BASKETBALL, color=accento, size=40),
                                 padding=ft.padding.only(top=20, bottom=15)),
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.ROUTE_OUTLINED,
                                             selected_icon=ft.icons.ROUTE, label="Piano"),
                ft.NavigationRailDestination(icon=ft.icons.COMPARE_ARROWS_OUTLINED,
                                             selected_icon=ft.icons.COMPARE_ARROWS, label="Confronto"),
                ft.NavigationRailDestination(icon=ft.icons.INSIGHTS_OUTLINED,
                                             selected_icon=ft.icons.INSIGHTS, label="Analisi"),
            ],
            on_change=self._cambio_scheda)

        self.page.add(ft.Row([
            menu,
            ft.VerticalDivider(width=1, color=bordo),
            ft.Column([self._testata(),
                       ft.Container(self.testo_stato, padding=ft.padding.only(left=25, top=10)),
                       self._contenuto], expand=True, spacing=0),
        ], expand=True, spacing=0))
        self._controller.fillDDs()
        self.update_page()

    def _cambio_scheda(self, e):
        self._contenuto.content = self._schede[e.control.selected_index]
        self.page.update()

    def _testata(self):
        return ft.Container(
            ft.Row([
                ft.Column([
                    ft.Text("PIANO DI TRASFERTA NBA", size=20, weight=ft.FontWeight.BOLD,
                            style=ft.TextStyle(letter_spacing=1.5)),
                    ft.Text("Raggruppamento e sequenziamento dei viaggi su grafo pesato",
                            size=10, color=testo_tenue),
                ], spacing=0, tight=True, expand=True),
                self.dd_squadra, self.dd_stagione,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=25, vertical=15),
            border=ft.border.only(bottom=ft.border.BorderSide(1, bordo)))

    def _scheda_pianificazione(self):
        self.txt_max_partite = ft.Slider(min=1, max=7, divisions=6, value=5, label="{value} gare",
            width=320, active_color=accento, on_change_end=self._controller.handleSlider)
        self.riga_parametri = ft.Row(controls=[], wrap=True, spacing=10, run_spacing=10)
        self.lista_piano = ft.ListView(spacing=0, padding=10)
        riquadri = self._crea_riquadri(self.riquadri_piano, [
            ("viaggi", ft.icons.LUGGAGE, colore_viaggi, "viaggi",
             "gruppi di trasferte consecutive, al massimo N gare ciascuno"),
            ("km", ft.icons.FLIGHT_TAKEOFF, colore_percorso, "chilometri",
             "somma dei giri ottimi sede -> tappe -> sede"),
            ("costo", ft.icons.EURO, colore_denaro, "costo stimato, EUR",
             "voli (quota fissa + km) + hotel + diarie, con gli assunti economici"),
            ("risparmio", ft.icons.TRENDING_DOWN, colore_risparmio, "km in meno vs reale",
             "(km reali - km piano) / km reali"),
        ])
        return ft.Column([
            self._didascalia("Raggruppa le trasferte in viaggi e ne ordina le tappe. Il piano "
                             "non assegna date: e' il limite inferiore non vincolato."),
            self._pannello([
                self._titolo_gruppo("Assunti economici"),
                self.riga_parametri,
                ft.Row([ft.Text("Max gare per viaggio", weight=ft.FontWeight.BOLD),
                        self.txt_max_partite], wrap=True, spacing=10,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.ElevatedButton("Calcola piano ottimizzato", icon=ft.icons.PLAY_ARROW,
                                      bgcolor=accento, color="#1A1A1A",
                                      on_click=self._controller.handleCalcolaPiano),
                    ft.OutlinedButton("Salva parametri", icon=ft.icons.SAVE,
                                      on_click=self._controller.handleSalvaParametri),
                ], wrap=True, spacing=10, run_spacing=10),
            ]),
            riquadri,
            self._cornice(self.lista_piano),
        ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    def _scheda_confronto(self):
        self.testo_confronto = ft.Text("", weight=ft.FontWeight.BOLD, size=15)
        self.lista_confronto = ft.ListView(spacing=0, padding=10)
        riquadri = self._crea_riquadri(self.riquadri_confronto, [
            ("km_reali", ft.icons.HISTORY, colore_storico, "km, calendario reale",
             "viaggi ricostruiti dalle gare esterne consecutive"),
            ("km_ottimi", ft.icons.FLIGHT_TAKEOFF, colore_percorso, "km, piano ottimizzato",
             "km del piano calcolato nella sezione Piano"),
            ("risparmio_km", ft.icons.TRENDING_DOWN, colore_risparmio, "km risparmiati",
             "km reali - km piano"),
            ("risparmio_eur", ft.icons.SAVINGS, colore_denaro, "EUR risparmiati",
             "costo reale - costo piano"),
        ])
        return ft.Column([
            self._didascalia("Confronta il calendario realmente disputato con il piano costruito "
                             "nella sezione Piano."),
            ft.Row([
                ft.OutlinedButton("Analizza calendario reale", icon=ft.icons.CALENDAR_MONTH,
                                  on_click=self._controller.handleAnalizzaReale),
                ft.ElevatedButton("Tabella comparativa completa", icon=ft.icons.TABLE_CHART,
                                  bgcolor=accento, color="#1A1A1A",
                                  on_click=self._controller.handleConfrontoCompleto),
            ], wrap=True, spacing=10, run_spacing=10),
            riquadri,
            self.testo_confronto,
            self._cornice(self.lista_confronto),
        ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    def _scheda_gestionale(self):
        self.lista_gestionale = ft.ListView(spacing=0, padding=10)
        self.lista_centralita = ft.ListView(spacing=0, padding=10)
        return ft.Column([
            self._didascalia("Quali franchigie hanno il margine di miglioramento maggiore e quanto "
                             "pesa la posizione geografica della sede."),
            self._titolo_gruppo("Confronto trasversale"),
            ft.Row([
                ft.ElevatedButton("Classifica per costo ottimizzato", icon=ft.icons.LEADERBOARD,
                                  bgcolor=accento, color="#1A1A1A",
                                  on_click=self._controller.handleConfrontoFranchigie),
                ft.OutlinedButton("Classifica per costo reale", icon=ft.icons.HISTORY,
                                  on_click=self._controller.handleConfrontoFranchigieReale),
            ], wrap=True, spacing=10, run_spacing=10),
            self._cornice(self.lista_gestionale),
            self._titolo_gruppo("Centralita' geografica delle sedi"),
            ft.OutlinedButton("Classifica delle sedi", icon=ft.icons.PLACE,
                              on_click=self._controller.handleCentralita),
            self._cornice(self.lista_centralita),
        ], spacing=15, expand=True, scroll=ft.ScrollMode.AUTO)

    @staticmethod
    def _didascalia(testo):
        return ft.Text(testo, italic=True, size=10, color=testo_tenue)

    @staticmethod
    def _titolo_gruppo(testo):
        return ft.Text(testo.upper(), size=10, weight=ft.FontWeight.BOLD, color=accento,
                       style=ft.TextStyle(letter_spacing=1.5))

    @staticmethod
    def _pannello(controlli):
        return ft.Container(ft.Column(controlli, spacing=10), padding=20, border_radius=10,
                            bgcolor=pannello, border=ft.border.all(1, bordo))

    @staticmethod
    def _cornice(contenuto):
        return ft.Container(contenuto, height=altezza_output, border_radius=10,
                            bgcolor=fondo_output, border=ft.border.all(1, bordo))

    def _crea_riquadri(self, deposito, definizioni):
        riga = ft.Row(spacing=10, run_spacing=10, wrap=True)
        for chiave, icona, colore, iniziale, spiegazione in definizioni:
            valore = ft.Text("—", size=20, weight=ft.FontWeight.BOLD, color=colore)
            etichetta = ft.Text(iniziale, size=10, color=testo_tenue)
            deposito[chiave] = (valore, etichetta, iniziale)
            riga.controls.append(ft.Container(
                ft.Row([ft.Container(width=5, height=45, bgcolor=colore, border_radius=0),
                        ft.Icon(icona, color=colore, size=25),
                        ft.Column([valore, etichetta], spacing=0, tight=True)],
                       spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(left=10, right=15, top=10, bottom=10), width=215,
                border_radius=10, bgcolor=pannello, border=ft.border.all(1, bordo),
                tooltip=spiegazione))
        return riga


    def update_page(self):
        self.page.update()

    def create_alert(self, testo):
        self.page.snack_bar = ft.SnackBar(ft.Text(testo))
        self.page.snack_bar.open = True
        self.page.update()
