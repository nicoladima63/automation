import os
from dotenv import load_dotenv
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

# Carica variabili d'ambiente dal file .env
load_dotenv()

# Determina l'ambiente corrente
CURRENT_ENV = Environment(os.getenv('APP_ENV', 'development'))

# --- Percorsi File DBF ---
# In development usa i file locali, in production usa i path dal .env
PATH_APPUNTAMENTI_DBF = (
    './windent/user/APPUNTA.DBF' if CURRENT_ENV == Environment.DEVELOPMENT 
    else os.getenv('PATH_APPUNTAMENTI_DBF')
)
PATH_ANAGRAFICA_DBF = (
    './windent/dati/PAZIENTI.DBF' if CURRENT_ENV == Environment.DEVELOPMENT 
    else os.getenv('PATH_ANAGRAFICA_DBF')
)

# --- Nomi Colonne DBF (Appuntamenti) ---
COL_APPUNTAMENTI_DATA = 'DB_APDATA'
COL_APPUNTAMENTI_DATA_INSERIMENTO = 'DB_APDATAI'
COL_APPUNTAMENTI_ORA = 'DB_APOREIN'
COL_APPUNTAMENTI_ORA_FINE = 'DB_APOREOU'
COL_APPUNTAMENTI_IDPAZIENTE = 'DB_APPACOD'
COL_APPUNTAMENTI_TIPO = 'DB_GUARDIA'
COL_APPUNTAMENTI_MEDICO = 'DB_APMEDIC'
COL_APPUNTAMENTI_STUDIO = 'DB_APSTUDI'
COL_APPUNTAMENTI_NOTE = 'DB_NOTE'
COL_APPUNTAMENTI_DESCRIZIONE = 'DB_APDESCR'

# --- Nomi Colonne DBF (Pazienti) ---
COL_PAZIENTI_ID = 'DB_CODE'
COL_PAZIENTI_NOME = 'DB_PANOME'
COL_PAZIENTI_COGNOME = 'DB_PACOGNOME'
COL_PAZIENTI_CELLULARE = 'DB_PACELLU'
COL_PAZIENTI_TELEFONO_FISSO = 'DB_PATELEF'

# --- Nomi Colonne DBF (Richiami) ---
COL_RICHAMI_PAZIENTE_ID = 'DB_CODE'
COL_RICHAMI_DARICHIAMARE = 'DB_PARICHI'
COL_RICHAMI_MESI_RICHIAMO = 'DB_PARITAR'
COL_RICHAMI_TIPO_RICHIAMI = 'DB_PARIMOT'
COL_RICHAMI_DATA1 = 'DB_PAMODA1' 
COL_RICHAMI_DATA2 = 'DB_PAMODA2' 
COL_RICHAMI_ULTIMA_VISITA = 'DB_PAULTVI'


# --- Mappe per decodifica (ORA CORRETTE CON I TUOI DATI) ---
TIPI_APPUNTAMENTO = {
    'V': 'Prima visita',
    'I': 'Igiene',
    'C': 'Conservativa',
    'E': 'Endodonzia',
    'H': 'Chirurgia',
    'P': 'Protesi',
    'O': 'Ortodonzia',
    'L': 'Implantologia',
    'R': 'Parodontologia',
    'S': 'Controllo',
    'U': 'Gnatologia', # Aggiunto da immagine
    'F': 'Ferie/Assenza', # Aggiunto da immagine
    'A': 'Attività/Manuten', # Aggiunto da immagine
    'M': 'privato' # Aggiunto da immagine
}

# --- Colori Appuntamenti (Hex codes) ---
COLORI_APPUNTAMENTO = {
    'V': '#FFA500',  # Arancione (Prima visita)
    'U': '#C8A2C8',  # Viola chiaro (Gnatologia)
    'I': '#800080',  # Viola (Igiene) - Ho usato viola più scuro per distinguerlo da Gnatologia
    'C': '#00BFFF',  # Azzurro (Conservativa)
    'H': '#FF0000',  # Rosso (Chirurgia)
    'P': '#008000',  # Verde (Protesi)
    'M': '#00FF00',  # Verde brillante (privato)
    'O': '#FFC0CB',  # Rosa chiaro (Ortodonzia)
    'E': '#808080',  # Grigio (Endodonzia) - Sembra un po' più chiaro dell'altro grigio
    'F': '#A9A9A9',  # Grigio scuro (Ferie/Assenza)
    'A': '#808080',  # Grigio (Attività/Manuten) - Sembra simile a Endodonzia
    'L': '#FF00FF',  # Magenta (Implantologia)
    'R': '#FFFF00',  # Giallo (Parodontologia)
    'S': '#ADD8E6'   # Azzurro chiaro (Controllo) - Ho usato un azzurro più chiaro per distinguerlo da Conservativa
}

GOOGLE_COLOR_MAP = {
    'V': '6',   # Prima visita (Arancione) -> Banana
    'U': '1',   # Gnatologia (Viola chiaro) -> lavanda
    'I': '3',   # Igiene (Viola) -> Vinaccia
    'C': '9',   # Conservativa (Azzurro) -> Mirtillo
    'H': '11',  # Chirurgia (Rosso) -> Tomato
    'P': '10',  # Protesi (Verde) -> Basil
    'M': '2',  # privato (Verde brillante) -> tangerine
    'O': '4',   # Ortodonzia (Rosa chiaro) -> flamingo
    'E': '7',   # Endodonzia (Grigio) -> peacock
    'F': '8',   # Ferie/Assenza (Grigio scuro) -> Graphite
    'A': '8',   # Attività/Manuten (Grigio) -> Graphite
    'L': '3',   # Implantologia (Magenta) -> Grape
    'R': '5',   # Parodontologia (Giallo) -> Banana
    'S': '8'    # Controllo (Azzurro chiaro) -> Blueberry
}


MEDICI = {
    1: 'Dr. Nicola',
    2: 'Dr.ssa Lara',
    3: 'Dr. Giacomo',
    4: 'Dr. Roberto',
    5: 'Dr.ssa Anet',
    6: 'Dr.ssa Rossella'
}

# --- Credenziali Twilio ---
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')

# Google Calendar settings
GOOGLE_CREDENTIALS_PATH = 'credentials.json'
CALENDAR_TIMEZONE = 'Europe/Rome'
STUDIO_CALENDAR_EMAIL = 'studiodrnicoladimartino@gmail.com'
DEFAULT_CALENDAR_ID = STUDIO_CALENDAR_EMAIL  # Usa l'email come ID calendario