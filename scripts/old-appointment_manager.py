import pandas as pd
import logging
from datetime import date, timedelta
from datetime import datetime, timedelta

from core.db_handler import DBHandler
from core.twilio_client import TwilioWhatsAppClient
from core.recall_manager import RecallManager
from core.utils import normalizza_numero_telefono, costruisci_messaggio_promemoria
from config import (
    COL_APPUNTAMENTI_IDPAZIENTE,
    COL_PAZIENTI_ID
)

class AppointmentManager:
    """
    Gestisce l'intero flusso di lavoro dei promemoria appuntamenti:
    dall'estrazione dei dati all'invio dei messaggi.
    """
    def __init__(self, modalita_test=False, test_numero=None, simula_invio=False):
        self.db_handler = DBHandler()
        self.twilio_client = TwilioWhatsAppClient(
            modalita_test=modalita_test,
            test_numero=test_numero,
            simula_invio=simula_invio
        )
        # Inizializza il recall_manager con il nome corretto del client
        self.recall_manager = RecallManager(self.db_handler, self.twilio_client)  # modifica qui

    def elabora_promemoria_giornalieri(self, data_test=None, solo_primo=False):
        """
        Orchestra il processo di invio dei promemoria giornalieri.
        Estrae appuntamenti, recupera dati pazienti, unisce i dati e invia i messaggi.

        Args:
            data_test (datetime.date, optional): Data specifica per testare l'estrazione appuntamenti.
            solo_primo (bool): Se True, elabora e invia il promemoria solo per il primo appuntamento trovato.
        """
        logging.info(f"--- Inizio elaborazione promemoria giornalieri per il {data_test if data_test else (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')} ---")

        appuntamenti_domani = self.db_handler.estrai_appuntamenti_domani(data_test)

        if appuntamenti_domani.empty:
            logging.info("Nessun appuntamento trovato per domani. Elaborazione terminata.")
            return

        # Assicurati che COL_APPUNTAMENTI_IDPAZIENTE sia presente
        if COL_APPUNTAMENTI_IDPAZIENTE not in appuntamenti_domani.columns:
            logging.error(f"Colonna '{COL_APPUNTAMENTI_IDPAZIENTE}' non trovata nel DataFrame degli appuntamenti. Impossibile recuperare dati pazienti.")
            return

        lista_id_pazienti = appuntamenti_domani[COL_APPUNTAMENTI_IDPAZIENTE].unique().tolist()
        df_pazienti = self.db_handler.recupera_dati_pazienti(lista_id_pazienti)

        if df_pazienti.empty:
            logging.warning("Nessun dato paziente recuperato per gli appuntamenti di domani.")
            return

        # Converti COL_PAZIENTI_ID in stringa per un merge corretto
        df_pazienti[COL_PAZIENTI_ID] = df_pazienti[COL_PAZIENTI_ID].astype(str)
        appuntamenti_domani[COL_APPUNTAMENTI_IDPAZIENTE] = appuntamenti_domani[COL_APPUNTAMENTI_IDPAZIENTE].astype(str)


        # Unione dei DataFrame
        df_merged = pd.merge(
            appuntamenti_domani,
            df_pazienti,
            left_on=COL_APPUNTAMENTI_IDPAZIENTE,
            right_on=COL_PAZIENTI_ID,
            how='left'
        )

        # Contatori per il riepilogo
        messaggi_inviati_count = 0
        messaggi_falliti_count = 0
        appuntamenti_senza_numero = 0

        # Iterazione e invio messaggi
        for index, appuntamento in df_merged.iterrows():
            id_appuntamento = appuntamento.get(COL_APPUNTAMENTI_IDPAZIENTE, 'N/A')
            nome_paziente = appuntamento.get('nome_completo', 'Sconosciuto')
            logging.info(f"Elaborazione appuntamento per {nome_paziente} (ID: {id_appuntamento}).")

            # Verifica e pulizia del numero di telefono
            numero_grezzo = appuntamento.get('numero_contatto')
            numero_normalizzato = normalizza_numero_telefono(numero_grezzo)

            if not numero_normalizzato:
                logging.warning(f"Numero di telefono non valido per {nome_paziente} (ID: {id_appuntamento}, Numero originale: '{numero_grezzo}'). Salto l'invio del messaggio.")
                appuntamenti_senza_numero += 1
                continue

            messaggio = costruisci_messaggio_promemoria(appuntamento)

            if self.twilio_client.invia_messaggio(numero_normalizzato, messaggio, id_appuntamento):
                messaggi_inviati_count += 1
            else:
                messaggi_falliti_count += 1

            if solo_primo:
                logging.info("Modalità 'solo_primo' attiva. Interruzione dopo il primo appuntamento.")
                break

        logging.info(f"--- Riepilogo elaborazione promemoria ---")
        logging.info(f"Appuntamenti totali trovati: {len(appuntamenti_domani)}")
        logging.info(f"Messaggi inviati con successo: {messaggi_inviati_count}")
        logging.info(f"Messaggi falliti: {messaggi_falliti_count}")
        logging.info(f"Appuntamenti saltati (numero non valido/mancante): {appuntamenti_senza_numero}")
        logging.info("--- Fine elaborazione promemoria ---")

    def test_database_connection(self):
        """Esegue un test della connessione ai file DBF."""
        self.db_handler.test_connessione()

    def test_twilio_configuration(self):
        """Esegue un test della configurazione delle credenziali Twilio."""
        self.twilio_client.test_config()