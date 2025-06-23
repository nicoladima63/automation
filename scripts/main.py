import argparse
import logging
import schedule
import time
from datetime import datetime
import os

# Imposta il livello di logging prima di importare altri moduli che usano logging
# Questa configurazione deve essere fatta all'inizio.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('promemoria_appuntamenti.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

from scripts.appointment_manager import AppointmentManager

def main():
    parser = argparse.ArgumentParser(description="Script per l'invio di promemoria appuntamenti via WhatsApp.")
    parser.add_argument('--test', action='store_true',
                        help="Attiva la modalità test. I messaggi non vengono inviati realmente.")
    parser.add_argument('--simula-invio', action='store_true',
                        help="Simula l'invio dei messaggi (utile per testare la logica senza Twilio).")
    parser.add_argument('--test-db', action='store_true',
                        help="Esegue un test della connessione ai file DBF.")
    parser.add_argument('--test-twilio', action='store_true',
                        help="Esegue un test della configurazione delle credenziali Twilio.")
    parser.add_argument('--test-numero', type=str,
                        help="Numero di telefono specifico a cui reindirizzare i messaggi in modalità test (es. +39123456789).")
    parser.add_argument('--test-data', type=str,
                        help="Data specifica per testare l'estrazione degli appuntamenti (formato YYYY-MM-DD).")
    parser.add_argument('--esegui-ora', action='store_true',
                        help="Esegue l'elaborazione dei promemoria immediatamente, senza scheduling.")
    parser.add_argument('--solo-primo', action='store_true',
                        help="Invia il promemoria solo per il primo appuntamento trovato (utile per il debug).")
    args = parser.parse_args()

    data_test = None
    if args.test_data:
        try:
            data_test = datetime.strptime(args.test_data, '%Y-%m-%d').date()
        except ValueError:
            logging.error("Formato data non valido per --test-data. Usa YYYY-MM-DD")
            return

    # Inizializza il gestore degli appuntamenti, passando i parametri di test
    manager = AppointmentManager(
        modalita_test=args.test,
        test_numero=args.test_numero,
        simula_invio=args.simula_invio
    )

    if args.test_db:
        manager.test_database_connection()
        return

    if args.test_twilio:
        manager.test_twilio_configuration()
        return

    if args.esegui_ora:
        manager.elabora_promemoria_giornalieri(data_test, args.solo_primo)
        return

    logging.info("Script avviato in modalità scheduling. I promemoria verranno inviati ogni giorno alle 18:30.")
    schedule.every().day.at("18:30").do(
        manager.elabora_promemoria_giornalieri,
        data_test=data_test,
        solo_primo=args.solo_primo
    )

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()