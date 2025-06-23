import logging
from datetime import date, timedelta

from config.constants import COLONNE
from core.utils import normalizza_numero_telefono, costruisci_messaggio_richiamo

class RecallManager:
    """
    Gestisce i richiami dei pazienti in base ai dati salvati nell'anagrafica.
    """

    def __init__(self, db_handler, twilio_client):
        self.db_handler = db_handler
        self.twilio_client = twilio_client

    def get_due_recalls(self, days_threshold=30):
        """
        Restituisce i richiami in scadenza entro X giorni.

        Args:
            days_threshold (int): giorni entro cui considerare i richiami

        Returns:
            list[dict]: richiami filtrati
        """
        richiami = self.db_handler.get_recalls_data()
        col = COLONNE['richiami']
        oggi = date.today()
        entro = oggi + timedelta(days=days_threshold)
        risultati = []

        for r in richiami:
            data1 = r.get(col['data1'])
            if not isinstance(data1, date):
                continue
            if oggi <= data1 <= entro:
                risultati.append(r)

        logging.info(f"Trovati {len(risultati)} richiami entro {days_threshold} giorni.")
        return risultati

    def invia_richiamo(self, richiamo: dict) -> bool:
        """
        Invia un messaggio di richiamo WhatsApp a un singolo paziente.

        Args:
            richiamo (dict): dati richiamo

        Returns:
            bool: True se inviato correttamente, False altrimenti
        """
        col = COLONNE['richiami']
        telefono = normalizza_numero_telefono(richiamo.get('TELEFONO', ''))

        if not telefono:
            logging.warning(f"Numero non valido per paziente: {richiamo.get(col['id_paziente'])}")
            return False

        messaggio = costruisci_messaggio_richiamo(richiamo)

        id_richiamo = f"{richiamo.get(col['id_paziente'])}_{richiamo.get(col['data1'])}"
        risultato = self.twilio_client.invia_messaggio(telefono, messaggio, id_richiamo)

        if risultato:
            logging.info(f"Richiamo inviato a {telefono}")
        else:
            logging.warning(f"Fallito l'invio del richiamo a {telefono}")

        return risultato

    def invia_tutti_i_richiami(self, days_threshold=30, solo_primo=False):
        """
        Invia tutti i richiami in scadenza entro X giorni.

        Args:
            days_threshold (int): soglia giorni
            solo_primo (bool): se True, invia solo il primo per test
        """
        richiami = self.get_due_recalls(days_threshold=days_threshold)
        inviati = falliti = 0

        for r in richiami:
            if self.invia_richiamo(r):
                inviati += 1
            else:
                falliti += 1

            if solo_primo:
                break

        logging.info(f"Richiami inviati: {inviati} | Falliti: {falliti} | Totali: {len(richiami)}")
