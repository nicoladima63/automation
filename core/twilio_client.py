import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

class TwilioWhatsAppClient:
    """
    Gestisce l'invio di messaggi WhatsApp tramite l'API Twilio.
    """
    def __init__(self, modalita_test=False, test_numero=None, simula_invio=False):
        self.modalita_test = modalita_test
        self.test_numero = test_numero
        self.simula_invio = simula_invio

        self.client = None
        if not self.modalita_test and not self.simula_invio:
            if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                try:
                    self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    logging.info("Client Twilio inizializzato.")
                except Exception as e:
                    logging.error(f"Errore durante l'inizializzazione del client Twilio: {e}")
                    self.client = None
            else:
                logging.warning("Credenziali Twilio (ACCOUNT_SID o AUTH_TOKEN) mancanti. Impossibile inviare messaggi reali.")
        elif self.modalita_test:
            logging.info(f"Modalità TEST ATTIVA. Nessun messaggio reale verrà inviato. Test numero: {self.test_numero}")
        elif self.simula_invio:
            logging.info("Modalità SIMULAZIONE INVIO ATTIVA. I messaggi non verranno inviati realmente.")

    def invia_messaggio(self, numero, messaggio, id_riferimento="N/A"):
        """
        Invia un messaggio WhatsApp al numero specificato utilizzando Twilio.

        Args:
            numero (str): Numero di telefono del destinatario (formato E.164, es. '+391234567890').
            messaggio (str): Contenuto del messaggio da inviare.
            id_riferimento (str): ID di riferimento (es. ID appuntamento/paziente) per il logging.

        Returns:
            bool: True se il messaggio è stato inviato con successo, False altrimenti.
        """

        if not numero:
            logging.error(f"Errore: Numero di telefono non valido per riferimento '{id_riferimento}'. Impossibile inviare messaggio.")
            return False

        # Precedenza alla modalità di test con numero specifico
        destinatario_reale = numero
        if self.test_numero:
            numero_destinazione = self.test_numero
            logging.info(f"Modalità TEST: Messaggio per {destinatario_reale} reindirizzato a {numero_destinazione} (Riferimento: {id_riferimento}).")
        else:
            numero_destinazione = destinatario_reale

        if self.simula_invio:
            logging.info(f"SIMULAZIONE INVIO - Messaggio per {destinatario_reale} (Riferimento: {id_riferimento}): '{messaggio}'")
            return True

        if not self.client:
            logging.error(f"Client Twilio non inizializzato. Impossibile inviare messaggio a {numero_destinazione} (Riferimento: {id_riferimento}).")
            return False

        try:
            message = self.client.messages.create(
                from_=f'whatsapp:{TWILIO_WHATSAPP_NUMBER}',
                body=messaggio,
                to=f'whatsapp:{numero_destinazione}'
            )
            logging.info(f"Messaggio inviato con successo a {numero_destinazione} (Riferimento: {id_riferimento}). SID: {message.sid}")
            return True
        except TwilioRestException as e:
            logging.error(f"Errore Twilio durante l'invio del messaggio a {numero_destinazione} (Riferimento: {id_riferimento}): {e}")
            logging.error(f"Codice errore Twilio: {e.code}, Messaggio: {e.msg}")
            return False
        except Exception as e:
            logging.error(f"Errore generico durante l'invio del messaggio a {numero_destinazione} (Riferimento: {id_riferimento}): {e}")
            return False

    # --- FUNZIONI DI TEST E DEBUG SPOSTATE DA twilio_client.py ---
    # Vedi test_tools.py per test_twilio_config

    def test_config(self):
        """
        Verifica se le credenziali Twilio sono caricate correttamente.
        """
        logging.info("--- Test Configurazione Twilio ---")
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER:
            logging.info("Credenziali Twilio (ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_NUMBER) caricate correttamente.")
            if not self.modalita_test and self.client:
                logging.info("Client Twilio inizializzato e pronto per l'invio.")
            elif self.modalita_test:
                logging.info("Client Twilio non inizializzato in modalità test. L'invio verrà simulato/reindirizzato.")
            else:
                logging.warning("Client Twilio non inizializzato. Controllare credenziali o connessione.")
        else:
            logging.error("Credenziali Twilio (ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_NUMBER) mancanti o incomplete. Impossibile inviare messaggi.")
        logging.info("--- Fine Test Configurazione Twilio ---")