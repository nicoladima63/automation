import pandas as pd
import logging
from datetime import date, timedelta

from core.recall_manager import RecallManager
from core.utils import normalizza_numero_telefono, costruisci_messaggio_promemoria
from config import COLONNE

class AppointmentManager:
    """
    Gestisce il flusso dei promemoria appuntamenti.
    """
    def __init__(self, db_handler, twilio_client):
        self.db_handler = db_handler
        self.twilio_client = twilio_client
        self.recall_manager = RecallManager(self.db_handler, self.twilio_client)

    def elabora_promemoria_giornalieri(self, data_test=None, solo_primo=False):
        giorno_target = data_test if data_test else (date.today() + timedelta(days=1))
        logging.info(f"--- Inizio elaborazione promemoria per il {giorno_target.strftime('%Y-%m-%d')} ---")

        appuntamenti_domani = self.db_handler.estrai_appuntamenti_domani(giorno_target)
        if appuntamenti_domani.empty:
            logging.info("Nessun appuntamento trovato. Fine elaborazione.")
            return

        col_id_paziente = COLONNE['appuntamenti']['id_paziente']
        col_id_paz = COLONNE['pazienti']['id']

        if col_id_paziente not in appuntamenti_domani.columns:
            logging.error(f"Colonna '{col_id_paziente}' non trovata. Interruzione.")
            return

        lista_id_pazienti = appuntamenti_domani[col_id_paziente].unique().tolist()
        df_pazienti = self.db_handler.recupera_dati_pazienti(lista_id_pazienti)

        if df_pazienti.empty:
            logging.warning("Nessun dato paziente recuperato.")
            return

        # Conversioni per merge
        df_pazienti[col_id_paz] = df_pazienti[col_id_paz].astype(str)
        appuntamenti_domani[col_id_paziente] = appuntamenti_domani[col_id_paziente].astype(str)

        df_merged = pd.merge(
            appuntamenti_domani,
            df_pazienti,
            left_on=col_id_paziente,
            right_on=col_id_paz,
            how='left'
        )

        messaggi_inviati = messaggi_falliti = appuntamenti_senza_numero = 0

        for _, appuntamento in df_merged.iterrows():
            id_app = appuntamento.get(col_id_paziente, 'N/A')
            nome = appuntamento.get('nome_completo', 'Sconosciuto')
            logging.info(f"→ Elaboro appuntamento per {nome} (ID: {id_app})")

            numero_raw = appuntamento.get('numero_contatto')
            numero = normalizza_numero_telefono(numero_raw)

            if not numero:
                logging.warning(f"→ Numero non valido per {nome}. Skipping.")
                appuntamenti_senza_numero += 1
                continue

            messaggio = costruisci_messaggio_promemoria(appuntamento)

            if self.twilio_client.invia_messaggio(numero, messaggio, id_app):
                messaggi_inviati += 1
            else:
                messaggi_falliti += 1

            if solo_primo:
                logging.info("→ Solo primo attivo: interruzione.")
                break

        # Riepilogo finale
        logging.info(f"--- Fine promemoria --- Totali: {len(appuntamenti_domani)} | Inviati: {messaggi_inviati} | Falliti: {messaggi_falliti} | Senza numero: {appuntamenti_senza_numero}")

    def test_database_connection(self):
        """Test connessione DBF"""
        self.db_handler.test_connessione()

    def test_twilio_configuration(self):
        """Test configurazione Twilio"""
        self.twilio_client.test_config()
