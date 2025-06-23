import pandas as pd
import logging
from datetime import datetime, date, timedelta, time
import dbf # <-- Assicurati che dbf sia importato qui
import os,json
from config import (
    PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF,

    COL_APPUNTAMENTI_DATA, COL_APPUNTAMENTI_IDPAZIENTE,
    COL_APPUNTAMENTI_TIPO, COL_APPUNTAMENTI_ORA, COL_APPUNTAMENTI_ORA_FINE,
    COL_APPUNTAMENTI_MEDICO, COL_APPUNTAMENTI_STUDIO,COL_APPUNTAMENTI_NOTE,
    TIPI_APPUNTAMENTO, COLORI_APPUNTAMENTO, COL_APPUNTAMENTI_DESCRIZIONE,

    COL_PAZIENTI_ID, COL_PAZIENTI_NOME,
    COL_PAZIENTI_CELLULARE, COL_PAZIENTI_TELEFONO_FISSO, MEDICI,
    
    COL_RICHAMI_PAZIENTE_ID,
    COL_RICHAMI_DARICHIAMARE,
    COL_RICHAMI_MESI_RICHIAMO,
    COL_RICHAMI_TIPO_RICHIAMI,
    COL_RICHAMI_DATA1,
    COL_RICHAMI_DATA2,
    COL_RICHAMI_ULTIMA_VISITA
)

class DBHandler:
    """
    Gestisce la lettura e l'estrazione dati dai file DBF degli appuntamenti e dell'anagrafica pazienti.
    """
    def __init__(self, path_appuntamenti=PATH_APPUNTAMENTI_DBF, path_anagrafica=PATH_ANAGRAFICA_DBF):
        self.path_appuntamenti = path_appuntamenti
        self.path_anagrafica = path_anagrafica

    def get_recalls_data(self):
        """
        Recupera i dati dei richiami dal database.
        Returns:
            list: Lista di dizionari contenenti i dati dei richiami
        """
        recalls = []
        try:
            patients_db = dbf.Table(self.path_anagrafica, codepage='cp1252')
            patients_db.open()

            for record in patients_db:
                # Verifica se il paziente è da richiamare
                if record[COL_RICHAMI_DARICHIAMARE]:
                    recall = {
                        'PAZIENTE_ID': record[COL_RICHAMI_PAZIENTE_ID],
                        'NOME': record[COL_PAZIENTI_NOME],
                        'TELEFONO': record[COL_PAZIENTI_CELLULARE] or record[COL_PAZIENTI_TELEFONO_FISSO],
                        'DA_RICHIAMARE': record[COL_RICHAMI_DARICHIAMARE],
                        'MESI_RICHIAMO': record[COL_RICHAMI_MESI_RICHIAMO],
                        'TIPO_RICHIAMO': record[COL_RICHAMI_TIPO_RICHIAMI],
                        'DATA_RICHIAMO1': record[COL_RICHAMI_DATA1],
                        'DATA_RICHIAMO2': record[COL_RICHAMI_DATA2],
                        'ULTIMA_VISITA': record[COL_RICHAMI_ULTIMA_VISITA]
                    }
                    recalls.append(recall)

            patients_db.close()
            logging.info(f"Trovati {len(recalls)} pazienti da richiamare")
            return recalls

        except Exception as e:
            logging.error(f"Errore nella lettura dei dati dei richiami: {str(e)}")
            return []

    def get_recalls(self, month=None, tipo=None):
        """
        Restituisce i richiami filtrati per mese e tipo.
        Args:
            month (int, opzionale): mese (1-12)
            tipo (str, opzionale): codice tipo richiamo
        Returns:
            list: richiami filtrati
        """
        recalls = self.get_recalls_data()
        filtered = []
        for recall in recalls:
            # Filtro per mese sulla data del richiamo 1 (puoi cambiare su quale campo filtrare)
            if month:
                data_richiamo1 = recall.get('DATA_RICHIAMO1')
                if not data_richiamo1 or not isinstance(data_richiamo1, (date, datetime)):
                    continue
                if data_richiamo1.month != month:
                    continue
            # Filtro per tipo
            if tipo:
                if recall.get('TIPO_RICHIAMO') != tipo:
                    continue
            filtered.append(recall)
        return filtered

    def leggi_tabella_dbf(self, percorso_file):
        """
        Legge un file DBF specificato e restituisce un DataFrame Pandas.

        Args:
            percorso_file (str): Percorso al file DBF da leggere.

        Returns:
            pd.DataFrame: DataFrame contenente i dati del file DBF, o un DataFrame vuoto in caso di errore.
        """
        try:
            # --- LOGICA COPIATA ESATTAMENTE DAL TUO SCRIPT ORIGINALE ---
            dbf_table = dbf.Table(percorso_file, codepage='cp1252')
            dbf_table.open()
            records = []
            for record in dbf_table:
                try:
                    record_dict = {field: record[field] for field in dbf_table.field_names}
                    records.append(record_dict)
                except Exception as field_error:
                    logging.warning(f"Errore lettura record in {percorso_file}: {field_error}")
                    continue

            df = pd.DataFrame(records)
            dbf_table.close()
            logging.info(f"File DBF letto con successo: '{percorso_file}' - {len(df)} record.")
            return df
        except dbf.DbfError as e:
            logging.error(f"Errore di lettura del file DBF '{percorso_file}': {e}")
            return pd.DataFrame()
        except FileNotFoundError:
            logging.error(f"File DBF non trovato: '{percorso_file}'")
            return pd.DataFrame()
        except Exception as e: # Catch-all per eventuali altri errori non previsti
            logging.error(f"Errore inatteso durante la lettura di '{percorso_file}': {e}")
            return pd.DataFrame()
            # -------------------------------------------------------------

    def estrai_appuntamenti_domani(self, data_test=None):
        """
        Estrae gli appuntamenti programmati per il giorno successivo.
        ... (il resto della funzione rimane invariato) ...
        """
        df_appuntamenti = self.leggi_tabella_dbf(self.path_appuntamenti)

        if df_appuntamenti.empty:
            logging.warning("Nessun appuntamento letto dal file DBF o file vuoto.")
            return pd.DataFrame()

        if COL_APPUNTAMENTI_DATA not in df_appuntamenti.columns:
            logging.error(f"Colonna '{COL_APPUNTAMENTI_DATA}' non trovata nel file appuntamenti. Verificare la struttura del DBF.")
            return pd.DataFrame()

        target_date = data_test if data_test else (date.today() + timedelta(days=1))
        logging.info(f"Ricerca appuntamenti per il giorno: {target_date.strftime('%Y-%m-%d')}")

        df_appuntamenti[COL_APPUNTAMENTI_DATA] = pd.to_datetime(
            df_appuntamenti[COL_APPUNTAMENTI_DATA],
            errors='coerce'
        ).dt.date

        appuntamenti_filtrati = df_appuntamenti[
            (df_appuntamenti[COL_APPUNTAMENTI_DATA] == target_date) &
            (df_appuntamenti[COL_APPUNTAMENTI_DATA].notna())
        ]

        logging.info(f"Trovati {len(appuntamenti_filtrati)} appuntamenti per il {target_date.strftime('%Y-%m-%d')}.")
        return appuntamenti_filtrati

    def estrai_appuntamenti_mese(self, month, year):
        """
        Estrae tutti gli appuntamenti del mese/anno specificato.
        Args:
            month (int): mese (1-12)
            year (int): anno (es. 2024)
        Returns:
            pd.DataFrame: Appuntamenti filtrati per mese e anno
        """
        df_appuntamenti = self.leggi_tabella_dbf(self.path_appuntamenti)
        if df_appuntamenti.empty or COL_APPUNTAMENTI_DATA not in df_appuntamenti.columns:
            return pd.DataFrame()
        df_appuntamenti[COL_APPUNTAMENTI_DATA] = pd.to_datetime(
            df_appuntamenti[COL_APPUNTAMENTI_DATA], errors='coerce'
        )
        mask = (
            (df_appuntamenti[COL_APPUNTAMENTI_DATA].dt.month == month) &
            (df_appuntamenti[COL_APPUNTAMENTI_DATA].dt.year == year)
        )
        return df_appuntamenti[mask].copy()

    def recupera_dati_pazienti(self, lista_id_pazienti):
        """
        Recupera i dettagli dei pazienti (ID, nome, cognome, numero di telefono)
        da una lista di ID paziente.
        ... (il resto della funzione rimane invariato) ...
        """
        if not lista_id_pazienti:
            return pd.DataFrame()

        df_pazienti = self.leggi_tabella_dbf(self.path_anagrafica)

        if df_pazienti.empty:
            logging.warning("Nessun dato paziente letto dal file DBF o file vuoto.")
            return pd.DataFrame()

        required_cols = [COL_PAZIENTI_ID, COL_PAZIENTI_NOME, COL_PAZIENTI_CELLULARE, COL_PAZIENTI_TELEFONO_FISSO]
        missing_cols = [col for col in required_cols if col not in df_pazienti.columns]
        if missing_cols:
            logging.error(f"Colonne paziente mancanti nel file '{self.path_anagrafica}': {missing_cols}")
            return pd.DataFrame()

        df_pazienti[COL_PAZIENTI_ID] = df_pazienti[COL_PAZIENTI_ID].astype(str).str.strip()

        pazienti_filtrati = df_pazienti[df_pazienti[COL_PAZIENTI_ID].isin([str(x).strip() for x in lista_id_pazienti])].copy()

        pazienti_filtrati['nome_completo'] = pazienti_filtrati[COL_PAZIENTI_NOME].fillna('').str.strip().str.title()

        pazienti_filtrati['numero_contatto'] = ''
        mask_cell = pazienti_filtrati[COL_PAZIENTI_CELLULARE].notna() & (pazienti_filtrati[COL_PAZIENTI_CELLULARE].str.strip() != '')
        pazienti_filtrati.loc[mask_cell, 'numero_contatto'] = pazienti_filtrati.loc[mask_cell, COL_PAZIENTI_CELLULARE]

        mask_fisso = (pazienti_filtrati['numero_contatto'] == '') & pazienti_filtrati[COL_PAZIENTI_TELEFONO_FISSO].notna() & (pazienti_filtrati[COL_PAZIENTI_TELEFONO_FISSO].str.strip() != '')
        pazienti_filtrati.loc[mask_fisso, 'numero_contatto'] = pazienti_filtrati.loc[mask_fisso, COL_PAZIENTI_TELEFONO_FISSO]

        pazienti_filtrati = pazienti_filtrati[pazienti_filtrati['numero_contatto'].str.strip() != '']

        return pazienti_filtrati[[COL_PAZIENTI_ID, 'nome_completo', 'numero_contatto']]

    def get_appointments(self, month=None, year=None):
        """Recupera gli appuntamenti filtrando per mese/anno se specificati"""
        appointments = []
        patients_dict = {}
        
        try:
            # Carica anagrafica pazienti
            try:
                patients_table = dbf.Table(self.path_anagrafica, codepage='cp1252')
                patients_table.open()
                
                for record in patients_table:
                    try:
                        patient_id = record[COL_PAZIENTI_ID]
                        if patient_id:
                            patient_id = str(patient_id).strip()
                            patient_name = str(record[COL_PAZIENTI_NOME]).strip() if record[COL_PAZIENTI_NOME] else ''
                            if patient_id:
                                patients_dict[patient_id] = patient_name
                    except Exception as e:
                        logging.warning(f"Errore lettura paziente: {str(e)}")
                        continue
                        
                patients_table.close()
                
            except Exception as e:
                logging.error(f"Errore apertura tabella pazienti: {str(e)}")
                patients_dict = {}
                
            # Carica appuntamenti
            try:
                apps_table = dbf.Table(self.path_appuntamenti, codepage='cp1252')
                apps_table.open()

                for record in apps_table:
                    try:
                        # Salta i record marcati come cancellati nel DBF
                        #if hasattr(record, 'deleted') and record.deleted:
                            #continue
                        # Verifica data valida
                        if not record[COL_APPUNTAMENTI_DATA]:
                            continue
                        
                        # Filtra per mese/anno se specificati
                        if month and year:
                            app_date = record[COL_APPUNTAMENTI_DATA]
                            if app_date.month != month or app_date.year != year:
                                continue
                        
                        # Crea dizionario con i dati dell'appuntamento
                        appointment = {
                            'DATA': record[COL_APPUNTAMENTI_DATA],
                            'ORA_INIZIO': float(record[COL_APPUNTAMENTI_ORA]) if record[COL_APPUNTAMENTI_ORA] else 0,
                            'ORA_FINE': float(record[COL_APPUNTAMENTI_ORA_FINE]) if record[COL_APPUNTAMENTI_ORA_FINE] else 0,
                            'TIPO': record[COL_APPUNTAMENTI_TIPO].strip() if record[COL_APPUNTAMENTI_TIPO] else '',
                            'STUDIO': record[COL_APPUNTAMENTI_STUDIO] if record[COL_APPUNTAMENTI_STUDIO] else 1,
                            'NOTE': record[COL_APPUNTAMENTI_NOTE].strip() if record[COL_APPUNTAMENTI_NOTE] else '',
                            'PAZIENTE': patients_dict.get(str(record[COL_APPUNTAMENTI_IDPAZIENTE]).strip(), '')
                        }
                        
                        appointments.append(appointment)
                        
                    except Exception as e:
                        logging.warning(f"Errore lettura appuntamento: {str(e)}")
                        continue


                apps_table.close()


            except Exception as e:
                logging.error(f"Errore apertura tabella appuntamenti: {str(e)}")
                raise
                
            return appointments
            
        except Exception as e:
            logging.error(f"Errore recupero appuntamenti: {str(e)}")
            raise


# --- FUNZIONI DI TEST E DEBUG SPOSTATE IN test_tools.py ---
# Vedi test_tools.py per test_connessione, debug_campi_dbf, debug_richiami