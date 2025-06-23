import re
import pandas as pd
from datetime import datetime, date, timedelta, time
import logging

from config.constants import TIPI_APPUNTAMENTO, MEDICI, COLONNE

def decodifica_tipo_appuntamento(codice_guardia):
    if pd.isna(codice_guardia):
        return "Sconosciuto"
    return TIPI_APPUNTAMENTO.get(str(codice_guardia).upper(), 'Sconosciuto')

def decodifica_medico(numero_medico):
    try:
        return MEDICI.get(int(numero_medico), 'Sconosciuto')
    except (ValueError, TypeError):
        return 'Sconosciuto'

def calcola_giorni_prenotazione(data_inserimento):
    if pd.isna(data_inserimento):
        return 0
    try:
        data_inserimento_dt = datetime.combine(data_inserimento, datetime.min.time()).date()
        return (date.today() - data_inserimento_dt).days
    except TypeError:
        return 0

def normalizza_numero_telefono(numero_telefono):
    if pd.isna(numero_telefono):
        return None
    numero_pulito = re.sub(r'[^\d+]', '', str(numero_telefono)).lstrip('+')
    if numero_pulito.startswith('00'):
        numero_pulito = numero_pulito[2:]
    if not numero_pulito.startswith('39'):
        numero_pulito = '39' + numero_pulito
    if len(numero_pulito) < 11 or len(numero_pulito) > 13:
        logging.warning(f"Numero {numero_telefono} -> {numero_pulito} ha lunghezza anomala")
    return '+' + numero_pulito

def costruisci_messaggio_promemoria(appuntamento):
    col = COLONNE['appuntamenti']
    try:
        nome_paziente = appuntamento.get('nome_completo', "Gentile paziente")
        data_app = appuntamento.get(col['data'], datetime.now()).strftime('%d/%m/%Y')
        ora_app = appuntamento.get(col['ora_inizio'], "ora non specificata")
        tipo_app = decodifica_tipo_appuntamento(appuntamento.get(col['tipo']))
        medico = decodifica_medico(appuntamento.get(col['medico']))

        # Formattazione ora
        if isinstance(ora_app, (datetime, time)):
            ora_app = ora_app.strftime('%H:%M')
        elif isinstance(ora_app, (int, float)):
            ore = int(ora_app)
            minuti = int((ora_app % 1) * 60)
            ora_app = f"{ore:02d}:{minuti:02d}"
        elif not isinstance(ora_app, str):
            ora_app = "ora non specificata"

        return (
            f"Ciao {nome_paziente},\n"
            f"Ti ricordiamo l'appuntamento di domani {data_app} alle ore {ora_app}.\n"
            f"Tipo di appuntamento: {tipo_app}.\n"
            f"Con il {medico}.\n"
            f"Per qualsiasi necessità, contattaci. Grazie."
        )
    except Exception as e:
        logging.error(f"Errore costruzione messaggio: {str(e)}")
        return "Ciao! Ti ricordiamo un appuntamento programmato per domani. Contattaci per conferma. Grazie."

def costruisci_messaggio_richiamo(richiamo):
    col = COLONNE['richiami']
    try:
        nome = richiamo.get('NOME', 'Gentile paziente')
        tipo = richiamo.get(col['tipo'], 'controllo')
        data = richiamo.get(col['data1'])

        data_str = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else 'una prossima data'

        return (
            f"Ciao {nome},\n"
            f"Ti ricordiamo che è tempo per il tuo richiamo ({tipo}).\n"
            f"Ti proponiamo un appuntamento intorno al {data_str}.\n"
            f"Contattaci per fissarlo. Grazie!"
        )
    except Exception as e:
        logging.error(f"Errore costruzione messaggio richiamo: {str(e)}")
        return "Gentile paziente, è il momento di programmare un richiamo. Contattaci per fissare l'appuntamento."
