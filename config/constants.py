import os
from dotenv import load_dotenv
from enum import Enum

# --- ENV management ---
class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

load_dotenv()

CURRENT_ENV = Environment(os.getenv('APP_ENV', 'development'))

def require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise EnvironmentError(f"[CONFIG] Variabile '{var_name}' non trovata nel file .env")
    return value

# --- DBF Paths ---
PATHS_DBF = {
    'appuntamenti': (
        './windent/user/APPUNTA.DBF' if CURRENT_ENV == Environment.DEVELOPMENT
        else require_env('PATH_APPUNTAMENTI_DBF')
    ),
    'anagrafica': (
        './windent/dati/PAZIENTI.DBF' if CURRENT_ENV == Environment.DEVELOPMENT
        else require_env('PATH_ANAGRAFICA_DBF')
    )
}

# --- Colonne DBF ---
COLONNE = {
    'appuntamenti': {
        'data': 'DB_APDATA',
        'data_inserimento': 'DB_APDATAI',
        'ora_inizio': 'DB_APOREIN',
        'ora_fine': 'DB_APOREOU',
        'id_paziente': 'DB_APPACOD',
        'tipo': 'DB_GUARDIA',
        'medico': 'DB_APMEDIC',
        'studio': 'DB_APSTUDI',
        'note': 'DB_NOTE',
        'descrizione': 'DB_APDESCR',
    },
    'pazienti': {
        'id': 'DB_CODE',
        'nome': 'DB_PANOME',
        'cognome': 'DB_PACOGNOME',
        'cellulare': 'DB_PACELLU',
        'telefono': 'DB_PATELEF'
    },
    'richiami': {
        'id_paziente': 'DB_CODE',
        'da_richiamare': 'DB_PARICHI',
        'mesi': 'DB_PARITAR',
        'tipo': 'DB_PARIMOT',
        'data1': 'DB_PAMODA1',
        'data2': 'DB_PAMODA2',
        'ultima_visita': 'DB_PAULTVI'
    }
}

# --- Mapping logico ---
TIPI_APPUNTAMENTO = {
    'V': 'Prima visita', 'I': 'Igiene', 'C': 'Conservativa', 'E': 'Endodonzia',
    'H': 'Chirurgia', 'P': 'Protesi', 'O': 'Ortodonzia', 'L': 'Implantologia',
    'R': 'Parodontologia', 'S': 'Controllo', 'U': 'Gnatologia',
    'F': 'Ferie/Assenza', 'A': 'Attività/Manuten', 'M': 'privato'
}

TIPO_RICHIAMI = {
    '1': 'Generico',
    '2': 'Igiene',
    '3': 'Rx Impianto',
    '4': 'Controllo',
    '5': 'Impianto',
    '6': 'Ortodonzia'
}

COLORI_APPUNTAMENTO = {
    'V': '#FFA500', 'I': '#800080', 'C': '#00BFFF', 'E': '#808080',
    'H': '#FF0000', 'P': '#008000', 'O': '#FFC0CB', 'L': '#FF00FF',
    'R': '#FFFF00', 'S': '#ADD8E6', 'U': '#C8A2C8', 'F': '#A9A9A9',
    'A': '#808080', 'M': '#00FF00'
}

GOOGLE_COLOR_MAP = {
    'V': '6', 'U': '1', 'I': '3', 'C': '9', 'H': '11', 'P': '10', 'M': '2',
    'O': '4', 'E': '7', 'F': '8', 'A': '8', 'L': '3', 'R': '5', 'S': '8'
}

# --- Medici ---
MEDICI = {
    1: 'Dr. Nicola', 2: 'Dr.ssa Lara', 3: 'Dr. Giacomo',
    4: 'Dr. Roberto', 5: 'Dr.ssa Anet', 6: 'Dr.ssa Rossella'
}

# --- Twilio ---
TWILIO = {
    'account_sid': require_env('TWILIO_ACCOUNT_SID'),
    'auth_token': require_env('TWILIO_AUTH_TOKEN'),
    'whatsapp_number': require_env('TWILIO_WHATSAPP_NUMBER')
}

# --- Google Calendar ---
GOOGLE = {
    'credentials_path': 'credentials.json',
    'timezone': 'Europe/Rome',
    'default_calendar': require_env('GOOGLE_CALENDAR_EMAIL'),
    'calendars_by_studio': {
        1: os.getenv('CALENDAR_ID_STUDIO_1', require_env('GOOGLE_CALENDAR_EMAIL')),
        2: os.getenv('CALENDAR_ID_STUDIO_2', require_env('GOOGLE_CALENDAR_EMAIL'))
    }
}

PATH_APPUNTAMENTI_DBF = PATHS_DBF['appuntamenti']
PATH_ANAGRAFICA_DBF = PATHS_DBF['anagrafica']

TWILIO_ACCOUNT_SID = TWILIO['account_sid']
TWILIO_AUTH_TOKEN = TWILIO['auth_token']
TWILIO_WHATSAPP_NUMBER = TWILIO['whatsapp_number']