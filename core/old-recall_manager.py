from datetime import datetime, timedelta, date
from core.db_handler import DBHandler
from core.twilio_client import TwilioWhatsAppClient
from config import (
    PATH_APPUNTAMENTI_DBF, 
    PATH_ANAGRAFICA_DBF,
    COL_RICHAMI_PAZIENTE_ID,
    COL_RICHAMI_DARICHIAMARE,
    COL_RICHAMI_MESI_RICHIAMO,
    COL_RICHAMI_TIPO_RICHIAMI,
    COL_RICHAMI_DATA1,
    COL_RICHAMI_DATA2,
    COL_RICHAMI_ULTIMA_VISITA
)
import logging

# Definizione all'inizio del file, dopo gli import
TIPO_RICHIAMI = {
    '1': 'Generico',
    '2': 'Igiene',
    '3': 'Rx Impianto',
    '4': 'Controllo',
    '5': 'Impianto',
    '6': 'Ortodonzia'
}

class RecallManager:
    def __init__(self, db_handler: DBHandler, whatsapp_client: TwilioWhatsAppClient):
        self.db_handler = db_handler
        self.whatsapp_client = whatsapp_client

    def get_due_recalls(self, days_threshold=7, selected_month=None):
        """
        Recupera i pazienti con richiami in scadenza
        Args:
            days_threshold (int): giorni di anticipo per il richiamo
            selected_month (int): mese selezionato (1-12), se None mostra tutti
        """
        recalls = self.db_handler.get_recalls_data()
        due_recalls = []
        
        for recall in recalls:
            if self._is_recall_due(recall, days_threshold, selected_month):
                due_recalls.append(recall)
        
        return due_recalls

    def _is_recall_due(self, recall, days_threshold, selected_month=None):
        """Verifica se un richiamo è in scadenza nel mese selezionato"""
        if not recall.get('DA_RICHIAMARE'):
            return False

        today = datetime.now().date()
        
        # Controllo date specifiche di richiamo
        data1 = recall.get('DATA_RICHIAMO1')
        data2 = recall.get('DATA_RICHIAMO2')
        
        # Se è specificato un mese, verifica solo i richiami di quel mese
        if selected_month is not None:
            if (data1 and data1.month != selected_month) and \
               (data2 and data2.month != selected_month):
                return False

        if data1 and isinstance(data1, date) and (data1 - today).days <= days_threshold:
            return True
        if data2 and isinstance(data2, date) and (data2 - today).days <= days_threshold:
            return True

        # Controllo basato su ultima visita + mesi richiamo
        ultima_visita = recall.get('ULTIMA_VISITA')
        mesi_richiamo = recall.get('MESI_RICHIAMO')
        
        if ultima_visita and mesi_richiamo and isinstance(ultima_visita, date):
            try:
                mesi = int(mesi_richiamo)
                data_richiamo = ultima_visita + timedelta(days=mesi * 30)
                return (data_richiamo - today).days <= days_threshold
            except (ValueError, TypeError):
                logging.warning(f"Valore mesi richiamo non valido: {mesi_richiamo}")
                return False

        return False

    def _parse_recall_types(self, recall_type_str):
        """
        Analizza la stringa dei tipi di richiamo e restituisce una lista di tipi
        Args:
            recall_type_str: stringa che può contenere uno o due numeri (es: "1", "15", "24")
        Returns:
            list: lista dei tipi di richiamo trovati
        """
        if not recall_type_str:
            return []
        
        # Converti in stringa per sicurezza
        recall_str = str(recall_type_str)
        # Estrai i singoli caratteri e convertili in tipi di richiamo
        return [char for char in recall_str if char in TIPO_RICHIAMI]

    def test_due_recalls(self, days_threshold=7, selected_month=None, selected_type=None):
        """Funzione di test che mostra i richiami in scadenza"""
        due_recalls = self.get_due_recalls(days_threshold, selected_month)
        
        # Filtra per tipo se specificato
        if selected_type:
            due_recalls = [r for r in due_recalls if selected_type in self._parse_recall_types(r.get('TIPO_RICHIAMO'))]
    
        # Contatori per tipo di richiamo
        type_counts = {v: 0 for v in TIPO_RICHIAMI.values()}
        type_counts['Non specificato'] = 0
        
        summary = {
            'total': len(due_recalls),
            'recalls': [],
            'type_counts': type_counts
        }
        
        for recall in due_recalls:
            # Ottieni lista dei tipi di richiamo
            tipo_numeri = self._parse_recall_types(recall.get('TIPO_RICHIAMO'))
            
            if not tipo_numeri:
                tipo_richiamo = 'Non specificato'
                type_counts[tipo_richiamo] += 1
            else:
                # Incrementa il contatore per ogni tipo trovato
                for tipo_num in tipo_numeri:
                    tipo_richiamo = TIPO_RICHIAMI.get(tipo_num)
                    type_counts[tipo_richiamo] += 1
                # Per la visualizzazione, unisci i tipi con "+"
                tipo_richiamo = " e ".join(TIPO_RICHIAMI.get(t) for t in tipo_numeri)
        
            recall_details = {
                'paziente_id': recall.get('PAZIENTE_ID', ''),
                'nome': recall.get('NOME', 'Non specificato'),
                'tipo_richiamo': tipo_richiamo,
                'mesi_richiamo': recall.get('MESI_RICHIAMO', ''),
                'ultima_visita': recall.get('ULTIMA_VISITA', ''),
                'data_richiamo1': recall.get('DATA_RICHIAMO1', ''),
                'data_richiamo2': recall.get('DATA_RICHIAMO2', ''),
                'telefono': recall.get('TELEFONO', 'Non disponibile')
            }
            
            summary['recalls'].append(recall_details)
    
        return summary

    def debug_recall_data(self, recall):
        """Debug dei dati di un singolo richiamo"""
        logging.info("--- DEBUG RECALL DATA ---")
        for key, value in recall.items():
            logging.info(f"{key}: {value} ({type(value)})")
        logging.info("------------------------")