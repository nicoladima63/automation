import argparse
import logging
from datetime import date, timedelta

from scripts.appointment_manager import AppointmentManager
from core.recall_manager import RecallManager
from core.calendar_sync import GoogleCalendarSync
from core.db_handler import DBHandler

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(test_mode=False):
    logging.info(f"Avvio automation.py | Modalità TEST: {test_mode}")
    db_handler = DBHandler()
    appointment_manager = AppointmentManager(modalita_test=test_mode, simula_invio=test_mode)
    recall_manager = RecallManager(db_handler, appointment_manager.twilio_client)
    calendar_sync = GoogleCalendarSync()

    # 1. PROMEMORIA APPUNTAMENTI PER DOMANI
    if test_mode:
        # Estrai appuntamenti per domani e scrivi su file
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

    # 2. RICHIAMI IN SCADENZA (prossimi 30 giorni)
    if test_mode:
        recalls = recall_manager.get_due_recalls(days_threshold=30)
        with open('test_richiami_30gg.txt', 'w', encoding='utf-8') as f:
            for recall in recalls:
                f.write(f"{recall}\n")
        logging.info("[TEST] File test_richiami_30gg.txt generato.")
    else:
        # Qui puoi inserire la chiamata reale per invio richiami automatici
        pass  # Da implementare se vuoi invio automatico

    # 3. SINCRONIZZAZIONE CALENDAR
    if test_mode:
        # Esegui sync calendar in dry-run e scrivi su file
        # Qui si assume che calendar_sync abbia una funzione di dry-run o debug_export_first_50
        result = calendar_sync.sync_appointments_for_month(debug_export_first_50=True)
        with open('test_eventi_sincronizzati.txt', 'w', encoding='utf-8') as f:
            f.write(str(result))
        logging.info("[TEST] File test_eventi_sincronizzati.txt generato.")
    else:
        # Sincronizzazione reale (puoi parametrizzare mese/anno)
        calendar_sync.sync_appointments_for_month()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automation Studio Dentistico: promemoria, richiami, sync calendar")
    parser.add_argument('--test', action='store_true', help='Esegui in modalità test (nessun invio reale, solo file di output)')
    args = parser.parse_args()
    main(test_mode=args.test)
