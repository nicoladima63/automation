import argparse
import logging
from datetime import date, timedelta

from config import GOOGLE
from core.db_handler import DBHandler
from scripts.appointment_manager import AppointmentManager
from core.calendar_sync import GoogleCalendarSync
from core.twilio_client import TwilioWhatsAppClient
from core.recall_manager import RecallManager

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(test_mode=False, debug_sync=False):
    logging.info(f"Avvio automation.py | Modalità TEST: {test_mode} | DEBUG_SYNC: {debug_sync}")
    
    try:
        # Inizializza componenti principali
        db_handler = DBHandler()
        twilio_client = TwilioWhatsAppClient(
            modalita_test=test_mode,
            simula_invio=test_mode,
            test_numero=None
        )
        appointment_manager = AppointmentManager(db_handler, twilio_client)
        recall_manager = RecallManager(db_handler, twilio_client)
        calendar_sync = GoogleCalendarSync(db_handler=db_handler)

        # --- 1. PROMEMORIA APPUNTAMENTI ---
        try:
            if test_mode:
                domani = date.today() + timedelta(days=1)
                appuntamenti_domani = db_handler.estrai_appuntamenti_domani(domani)
                with open('test_promemoria_domani.txt', 'w', encoding='utf-8') as f:
                    if not appuntamenti_domani.empty:
                        for _, row in appuntamenti_domani.iterrows():
                            f.write(f"{row.to_dict()}\n")
                    else:
                        f.write("Nessun appuntamento per domani\n")
                logging.info("[TEST] File test_promemoria_domani.txt generato.")
            else:
                appointment_manager.elabora_promemoria_giornalieri()
        except Exception as e:
            logging.error(f"Errore elaborazione promemoria: {e}", exc_info=True)

        # --- 2. RICHIAMI (place holder per azione reale) ---
        try:
            if test_mode:
                recalls = recall_manager.get_due_recalls(days_threshold=30)
                with open('test_richiami_30gg.txt', 'w', encoding='utf-8') as f:
                    for recall in recalls:
                        f.write(f"{recall}\n")
                logging.info("[TEST] File test_richiami_30gg.txt generato.")
            else:
                # TODO: implementa invio richiami automatici
                logging.info("Funzione richiami non implementata in modalità reale.")
        except Exception as e:
            logging.error(f"Errore gestione richiami: {e}", exc_info=True)

        # --- 3. SYNC CALENDAR ---
        try:
            if test_mode:
                result = calendar_sync.sync_appointments_for_month(
                    studio_calendar_ids=GOOGLE['calendars_by_studio'],
                    debug_export_first_50=debug_sync
                )
                with open('test_eventi_sincronizzati.txt', 'w', encoding='utf-8') as f:
                    f.write(str(result))
                logging.info("[TEST] File test_eventi_sincronizzati.txt generato.")
            else:
                calendar_sync.sync_appointments_for_month(
                    studio_calendar_ids=GOOGLE['calendars_by_studio']
                )
        except Exception as e:
            logging.error(f"Errore sincronizzazione calendario: {e}", exc_info=True)

    except Exception as e:
        logging.critical(f"Errore fatale inizializzazione componenti: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automation Studio Dentistico")
    parser.add_argument('--test', action='store_true', help='Esegui in modalità test (file di output, nessun invio reale)')
    parser.add_argument('--debug-sync', action='store_true', help='Esporta primi 50 eventi per debug della sincronizzazione calendar')
    args = parser.parse_args()

    main(test_mode=args.test, debug_sync=args.debug_sync)
