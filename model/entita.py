from dataclasses import dataclass, field
from datetime import date


@dataclass
class Squadra:
    team_id: str
    nome: str
    citta: str
    stato: str
    conference: str
    divisione: str

    def __str__(self):
        return f"{self.nome} ({self.team_id})"


@dataclass
class Arena:

    team_id: str
    citta: str

    def __hash__(self):
        return hash(self.team_id)

    def __eq__(self, other):
        return isinstance(other, Arena) and self.team_id == other.team_id

    def __str__(self):
        return f"{self.citta} ({self.team_id})"


@dataclass
class Stagione:
    stagione_id: str
    anno_inizio: int
    data_avvio: date
    data_chiusura: date

    def __str__(self):
        return self.stagione_id


@dataclass
class Partita:
    data: date
    team_casa: str
    team_ospite: str
    sede_neutra: bool


@dataclass
class Viaggio:
    # tappe = sigle delle squadre ospitanti in ordine di visita (partenza e ritorno in sede).
    # Date solo per i viaggi reali: nel piano ottimizzato il raggruppamento e' la decisione.
    tappe: tuple
    km: float
    data_inizio: date = None
    data_fine: date = None

    @property
    def partite(self) -> int:
        return len(self.tappe)

    @property
    def tratte(self) -> int:
        # andata + trasferimenti interni + ritorno
        return len(self.tappe) + 1

    @property
    def giorni_effettivi(self):
        if self.data_inizio is None or self.data_fine is None:
            return None
        return (self.data_fine - self.data_inizio).days + 1

    def __str__(self):
        return " -> ".join(self.tappe)


@dataclass
class Metriche:
    # definite senza date, cosi' piano reale e ottimizzato sono confrontabili
    km: float = 0.0
    trasferimenti: int = 0
    giorni_fuori: int = 0
    notti: int = 0
    viaggi: int = 0
    tratte: int = 0
    partite: int = 0


@dataclass
class Costo:
    volo_fisso: float = 0.0
    volo_km: float = 0.0
    hotel: float = 0.0
    diaria: float = 0.0

    @property
    def totale(self) -> float:
        return self.volo_fisso + self.volo_km + self.hotel + self.diaria


@dataclass
class Piano:
    team_id: str
    stagione_id: str
    viaggi: list = field(default_factory=list)
    metriche: Metriche = field(default_factory=Metriche)
    costo: Costo = field(default_factory=Costo)

    def __str__(self):
        return f"{self.metriche.viaggi} viaggi, {self.metriche.km:,.0f} km"
