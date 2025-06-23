import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import TWILIO

class TwilioWhatsAppClient:
    """
    Gestisce l'invio di messaggi WhatsApp tramite l'API Twilio.
    """

    def __init__(self, modalita_test=False, test_numero=None, simula_invio=False):
        self.modalita_test = modalita_test
        self.test_numero = test_numero
        self.simula_invio = simula_invio
        self.client = None

        if self.modalita_test:
            logging.info(f"[Twilio] Modalità TEST ATTIVA. I messaggi verranno reindirizzati a {self.test_numero or 'nessun numero'}")
        elif self.simula_invio:
            logging.info("[Twilio] SIMULAZIONE INVIO ATTIVA. Nessun messaggio verrà realmente inviato.")
        else:
            sid = TWILIO.get('account_sid')
            token = TWILIO.get('auth_token')

            if sid and token:
                try:
                    self.client = Client(sid, token)
                    logging.info("Client Twilio inizializzato correttamente.")
                except Exception as e:
                    logging.error(f"Errore inizializzazione Twilio Client: {e}")
            else:
                logging.warning("Credenziali Twilio mancanti. Nessun messaggio verrà inviato.")

    def invia_messaggio(self, numero, messaggio, id_riferimento="N/A"):
        """
        Invia un messaggio WhatsApp tramite Twilio o simula l'invio.

        Args:
            numero (str): Numero destinatario in formato E.164 (+39...).
            messaggio (str): Testo del messaggio.
            id_riferimento (str): ID riferimento per log (es. ID paziente/app).

        Returns:
            bool: True se l'invio (o simulazione) è avvenuto con successo, False altrimenti.
        """
        if not numero:
            logging.error(f"[Twilio] Numero non valido (riferimento {id_riferimento})")
            return False

        numero_destinazione = self.test_numero if self.test_numero else numero
        log_dest = f"{numero_destinazione} (riferimento: {id_riferimento})"

        if self.simula_invio:
            logging.info(f"[SIMULATO] Messaggio per {log_dest}: {messaggio}")
            return True

        if not self.client:
            logging.warning(f"[Twilio] Client non disponibile. Messaggio non inviato a {log_dest}")
            return False

        try:
            message = self.client.messages.create(
                from_=f"whatsapp:{TWILIO['whatsapp_number']}",
                to=f"whatsapp:{numero_destinazione}",
                body=messaggio
            )
            logging.info(f"[Twilio] Messaggio inviato a {log_dest}. SID: {message.sid}")
            return True
        except TwilioRestException as e:
            logging.error(f"[Twilio] Errore Twilio: {e} | codice: {e.code}, msg: {e.msg}")
        except Exception as e:
            logging.error(f"[Twilio] Errore generico durante invio a {log_dest}: {e}")
        return False

    def test_config(self):
        """
        Verifica e logga la configurazione Twilio attiva.
        """
        logging.info("=== Test configurazione Twilio ===")
        if all(TWILIO.get(k) for k in ('account_sid', 'auth_token', 'whatsapp_number')):
            logging.info("Credenziali Twilio caricate correttamente.")
            if self.client:
                logging.info("Client Twilio pronto per invio.")
            elif self.modalita_test:
                logging.info("Modalità test: client non inizializzato (previsto).")
            else:
                logging.warning("Client Twilio non inizializzato.")
        else:
            logging.error("Credenziali Twilio mancanti o incomplete.")
        logging.info("=== Fine test configurazione Twilio ===")
