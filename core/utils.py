import re
import pandas as pd
from datetime import datetime, date, timedelta, time
import logging

from config import TIPI_APPUNTAMENTO, MEDICI

def decodifica_tipo_appuntamento(codice_guardia):
    """
    Decodifica un codice di tipo appuntamento in una descrizione leggibile.

    Args:
        codice_guardia (str): Codice del tipo di appuntamento (es. 'V', 'C').

    Returns:
        str: Descrizione completa del tipo di appuntamento, o 'Sconosciuto' se il codice non è valido.
    """
    if pd.isna(codice_guardia):
        return "Sconosciuto"
    return TIPI_APPUNTAMENTO.get(str(codice_guardia).upper(), 'Sconosciuto')

def decodifica_medico(numero_medico):
    """
    Decodifica un codice numerico del medico nel nome del medico.

    Args:
        numero_medico (int): Codice numerico del medico.

    Returns:
        str: Nome del medico, o 'Sconosciuto' se il codice non è valido.
    """
    try:
        return MEDICI.get(int(numero_medico), 'Sconosciuto')
    except (ValueError, TypeError):
        return 'Sconosciuto'

def calcola_giorni_prenotazione(data_inserimento):
    """
    Calcola i giorni trascorsi dalla data di inserimento dell'appuntamento.

    Args:
        data_inserimento (datetime.date): Data di inserimento dell'appuntamento.

    Returns:
        int: Numero di giorni dalla data di inserimento, o 0 se la data non è valida.
    """
    if pd.isna(data_inserimento):
        return 0
    try:
        data_inserimento_dt = datetime.combine(data_inserimento, datetime.min.time()).date()
        return (date.today() - data_inserimento_dt).days
    except TypeError:
        return 0

def normalizza_numero_telefono(numero_telefono):
    """
    Normalizza un numero di telefono per l'uso con WhatsApp.
    
    Args:
        numero_telefono (str): Numero di telefono da normalizzare.
    
    Returns:
        str: Numero di telefono normalizzato, o None se invalido.
    """
    if pd.isna(numero_telefono):
        return None
        
    # Usa regex per rimuovere tutto tranne i numeri
    numero_pulito = re.sub(r'[^\d+]', '', str(numero_telefono))
    
    if not numero_pulito:
        return None
        
    # Rimuovi eventuali + iniziali per standardizzare
    numero_pulito = numero_pulito.lstrip('+')
    
    # Gestisci prefisso internazionale
    if numero_pulito.startswith('00'):
        numero_pulito = numero_pulito[2:]
    
    # Aggiungi prefisso Italia se necessario
    if not numero_pulito.startswith('39'):
        numero_pulito = '39' + numero_pulito
    
    # Validazione lunghezza
    if len(numero_pulito) < 11 or len(numero_pulito) > 13:
        logging.warning(f"Numero {numero_telefono} -> {numero_pulito} ha lunghezza anomala")
        
    return '+' + numero_pulito

def costruisci_messaggio_promemoria(appuntamento):
    """
    Costruisce il testo del messaggio di promemoria.
    
    Args:
        appuntamento (pd.Series): Dati appuntamento e paziente.
    
    Returns:
        str: Messaggio formattato o messaggio di fallback in caso di errore.
    """
    try:
        from config import COL_APPUNTAMENTI_DATA, COL_APPUNTAMENTI_ORA, COL_APPUNTAMENTI_TIPO, COL_APPUNTAMENTI_MEDICO
        
        # Gestione valori nulli con valori di default
        nome_paziente = appuntamento.get('nome_completo', "Gentile paziente")
        data_app = appuntamento.get(COL_APPUNTAMENTI_DATA, datetime.now()).strftime('%d/%m/%Y')
        ora_app = appuntamento.get(COL_APPUNTAMENTI_ORA, "ora non specificata")
        tipo_app = decodifica_tipo_appuntamento(appuntamento.get(COL_APPUNTAMENTI_TIPO))
        medico = decodifica_medico(appuntamento.get(COL_APPUNTAMENTI_MEDICO))

        # Formattazione ora
        if isinstance(ora_app, (datetime, time)):
            ora_app = ora_app.strftime('%H:%M')
        elif isinstance(ora_app, (int, float)):
            # Converti numeri decimali in orario (es: 9.3 -> 09:30)
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
        return "Errore nella costruzione del messaggio di promemoria. Contattare lo studio."