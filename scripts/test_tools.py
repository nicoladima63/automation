# test_tools.py
# Tutte le funzioni di test e debug centralizzate qui.
# Puoi importare da qui per eseguire test manuali o automatizzati.

# Esempio di import da altri moduli:
# from db_handler import test_connessione, debug_campi_dbf, debug_richiami
# from gui_app import test_calendar_auth, test_appointments_read, test_recalls, test_single_event_gui, test_send_debug_json_events
# from twilio_client import test_config
# from script import test_connessione_database, test_twilio_config
# from recall_manager import test_due_recalls, debug_recall_data
# from appointment_manager import test_database_connection, test_twilio_configuration

# --- FUNZIONI DI TEST E DEBUG SPOSTATE DA db_handler.py ---
import logging
from config import (
    PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF,
    COL_RICHAMI_DARICHIAMARE, COL_RICHAMI_PAZIENTE_ID, COL_PAZIENTI_NOME, COL_PAZIENTI_CELLULARE, COL_PAZIENTI_TELEFONO_FISSO,
    COL_RICHAMI_MESI_RICHIAMO, COL_RICHAMI_TIPO_RICHIAMI, COL_RICHAMI_DATA1, COL_RICHAMI_DATA2, COL_RICHAMI_ULTIMA_VISITA
)
import dbf

# Funzione di test connessione DBF

def test_connessione(path_appuntamenti=PATH_APPUNTAMENTI_DBF, path_anagrafica=PATH_ANAGRAFICA_DBF):
    """
    Verifica la connessione e la leggibilità dei file DBF degli appuntamenti e dell'anagrafica.
    """
    logging.info("--- Test Connessione Database ---")
    try:
        appuntamenti_ok = False
        pazienti_ok = False
        try:
            dbf.Table(path_appuntamenti, codepage='cp1252').open().close()
            appuntamenti_ok = True
        except Exception:
            pass
        try:
            dbf.Table(path_anagrafica, codepage='cp1252').open().close()
            pazienti_ok = True
        except Exception:
            pass
        if appuntamenti_ok:
            logging.info(f"Connessione a '{path_appuntamenti}' riuscita.")
        else:
            logging.error(f"Connessione a '{path_appuntamenti}' fallita. Verificare percorso e permessi.")
        if pazienti_ok:
            logging.info(f"Connessione a '{path_anagrafica}' riuscita.")
        else:
            logging.error(f"Connessione a '{path_anagrafica}' fallita. Verificare percorso e permessi.")
    except Exception as e:
        logging.error(f"Errore test connessione: {e}")
    logging.info("--- Fine Test Connessione Database ---")

# Funzione di debug campi DBF

def debug_campi_dbf(percorso_file, file_type='appuntamenti'):
    """
    Esegue il debug dei campi del file DBF specificato,
    mostrando le colonne e i primi 3 record.
    """
    logging.info(f"--- DEBUG CAMPI DBF '{file_type.upper()}' ---")
    try:
        dbf_table = dbf.Table(percorso_file, codepage='cp1252')
        dbf_table.open()
        logging.info(f"Colonne disponibili in '{percorso_file}': {[field.name for field in dbf_table.fields]}")
        logging.info("Primi 3 record:")
        for i, record in enumerate(dbf_table):
            if i >= 3:
                break
            logging.info(f"Record {i+1}: {dict(record)}")
        dbf_table.close()
    except Exception as e:
        logging.error(f"Errore durante il debug del file DBF {file_type}: {e}")
    logging.info("----------------------------------")

# Funzione di debug richiami

def debug_richiami(db_handler):
    """
    Esegue il debug dei richiami mostrando i primi 3 record
    """
    logging.info("--- DEBUG RICHIAMI ---")
    try:
        recalls = db_handler.get_recalls_data()
        logging.info(f"Totale richiami trovati: {len(recalls)}")
        for i, recall in enumerate(recalls[:3]):
            logging.info(f"Richiamo {i+1}:")
            for key, value in recall.items():
                logging.info(f"  {key}: {value}")
            logging.info("-------------------")
    except Exception as e:
        logging.error(f"Errore durante il debug dei richiami: {e}")
    logging.info("----------------------------------")

# --- FUNZIONI DI TEST E DEBUG SPOSTATE DA gui_app.py ---
# Queste funzioni possono essere adattate per uso standalone o importate dalla GUI per test manuali.

def test_calendar_auth(calendar_sync, calendar_result):
    """Testa l'autenticazione con Google Calendar"""
    try:
        calendar_sync.authenticate()
        calendar_result.insert('end', "✓ Autenticazione Google Calendar riuscita!\n")
    except Exception as e:
        calendar_result.insert('end', f"✗ Errore autenticazione: {str(e)}\n")


def test_appointments_read(manager, calendar_result):
    """Testa la lettura degli appuntamenti dal DBF"""
    try:
        appointments = manager.db_handler.get_appointments()
        calendar_result.insert('end', f"Trovati {len(appointments)} appuntamenti futuri\n\n")
        for i, app in enumerate(appointments[:5], 1):
            calendar_result.insert('end', f"{i}. {app}\n")
    except Exception as e:
        calendar_result.insert('end', f"Errore lettura appuntamenti: {str(e)}\n")


def test_recalls(manager, recall_days_var, month_var, tipo_richiamo_var, recall_test_result):
    """Esegue il test dei richiami e mostra i risultati"""
    try:
        days = int(recall_days_var.get())
        selected_month = None
        selected_type = None
        month_str = month_var.get()
        if month_str != "Tutti":
            mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
            selected_month = mesi.index(month_str) + 1
        tipo_str = tipo_richiamo_var.get()
        if tipo_str != "Tutti":
            selected_type = tipo_str
        recalls = manager.db_handler.get_recalls(month=selected_month, tipo=selected_type)
        recall_test_result.insert('end', f"Trovati {len(recalls)} richiami\n")
        for i, recall in enumerate(recalls[:5], 1):
            recall_test_result.insert('end', f"{i}. {recall}\n")
    except Exception as e:
        recall_test_result.insert('end', f"Errore test richiami: {str(e)}\n")

# --- FUNZIONI DI TEST E DEBUG SPOSTATE DA twilio_client.py ---
# Puoi importare questa funzione in test_tools.py per testare la configurazione Twilio.

def test_twilio_config(client):
    """
    Verifica se le credenziali Twilio sono caricate correttamente.
    """
    import logging
    from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
    logging.info("--- Test Configurazione Twilio ---")
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER:
        logging.info("Credenziali Twilio (ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_NUMBER) caricate correttamente.")
        if hasattr(client, 'modalita_test') and client.modalita_test:
            logging.info("Client Twilio non inizializzato in modalità test. L'invio verrà simulato/reindirizzato.")
        elif hasattr(client, 'client') and client.client:
            logging.info("Client Twilio inizializzato e pronto per l'invio.")
        else:
            logging.warning("Client Twilio non inizializzato. Controllare credenziali o connessione.")
    else:
        logging.error("Credenziali Twilio (ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_NUMBER) mancanti o incomplete. Impossibile inviare messaggi.")
    logging.info("--- Fine Test Configurazione Twilio ---")

# --- FUNZIONI DI TEST E DEBUG SPOSTATE DA script.py ---
# Puoi importare queste funzioni in test_tools.py per testare la connessione ai database e la configurazione Twilio.

def test_connessione_database(leggi_tabella_dbf, path_appuntamenti, path_anagrafica):
    """Test per verificare la connessione ai database e mostrare i campi disponibili"""
    import logging
    logging.info("=== TEST CONNESSIONE DATABASE ===")
    logging.info("Test tabella appuntamenti:")
    df_app = leggi_tabella_dbf(path_appuntamenti)
    if not df_app.empty:
        logging.info(f"Campi trovati: {list(df_app.columns)}")
        if len(df_app) > 0:
            logging.info("Primo record di esempio:")
            for col in df_app.columns:
                logging.info(f"  {col}: {df_app.iloc[0][col]}")
    logging.info("\nTest tabella anagrafica:")
    df_ana = leggi_tabella_dbf(path_anagrafica)
    if not df_ana.empty:
        logging.info(f"Campi trovati: {list(df_ana.columns)}")
    logging.info("=== FINE TEST DATABASE ===")

# La funzione test_twilio_config è già stata spostata e adattata sopra.
