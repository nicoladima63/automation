import pandas as pd
import logging
from datetime import datetime, date, timedelta
import dbf
import os
import json

from config import PATHS_DBF, COLONNE

class DBHandler:
    def __init__(self, path_appuntamenti=None, path_anagrafica=None):
        self.path_appuntamenti = path_appuntamenti or PATHS_DBF['appuntamenti']
        self.path_anagrafica = path_anagrafica or PATHS_DBF['anagrafica']

    def leggi_tabella_dbf(self, percorso_file):
        try:
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
            logging.info(f"DBF letto: {percorso_file} → {len(df)} record.")
            return df

        except dbf.DbfError as e:
            logging.error(f"Errore lettura DBF '{percorso_file}': {e}")
        except FileNotFoundError:
            logging.error(f"File DBF non trovato: {percorso_file}")
        except Exception as e:
            logging.error(f"Errore imprevisto '{percorso_file}': {e}")
        return pd.DataFrame()

    def estrai_appuntamenti_domani(self, data_test=None):
        df = self.leggi_tabella_dbf(self.path_appuntamenti)
        col_data = COLONNE['appuntamenti']['data']

        if df.empty or col_data not in df.columns:
            logging.warning("DBF appuntamenti vuoto o colonna data mancante.")
            return pd.DataFrame()

        df[col_data] = pd.to_datetime(df[col_data], errors='coerce').dt.date
        target_date = data_test or (date.today() + timedelta(days=1))

        filtrati = df[
            (df[col_data] == target_date) & df[col_data].notna()
        ]

        logging.info(f"Trovati {len(filtrati)} appuntamenti per {target_date}")
        return filtrati

    def estrai_appuntamenti_mese(self, month, year):
        df = self.leggi_tabella_dbf(self.path_appuntamenti)
        col_data = COLONNE['appuntamenti']['data']

        if df.empty or col_data not in df.columns:
            return pd.DataFrame()

        df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
        return df[(df[col_data].dt.month == month) & (df[col_data].dt.year == year)].copy()

    def recupera_dati_pazienti(self, lista_id_pazienti):
        if not lista_id_pazienti:
            return pd.DataFrame()

        df = self.leggi_tabella_dbf(self.path_anagrafica)
        cols = COLONNE['pazienti']
        richieste = [cols['id'], cols['nome'], cols['cellulare'], cols['telefono']]

        if any(c not in df.columns for c in richieste):
            logging.error(f"Colonne mancanti in anagrafica: {richieste}")
            return pd.DataFrame()

        df[cols['id']] = df[cols['id']].astype(str).str.strip()
        df_filtrati = df[df[cols['id']].isin([str(x).strip() for x in lista_id_pazienti])].copy()

        df_filtrati['nome_completo'] = df_filtrati[cols['nome']].fillna('').str.strip().str.title()
        df_filtrati['numero_contatto'] = ''

        mask_cell = df_filtrati[cols['cellulare']].notna() & (df_filtrati[cols['cellulare']].str.strip() != '')
        df_filtrati.loc[mask_cell, 'numero_contatto'] = df_filtrati.loc[mask_cell, cols['cellulare']]

        mask_fisso = (df_filtrati['numero_contatto'] == '') & df_filtrati[cols['telefono']].notna()
        df_filtrati.loc[mask_fisso, 'numero_contatto'] = df_filtrati.loc[mask_fisso, cols['telefono']]

        return df_filtrati[[cols['id'], 'nome_completo', 'numero_contatto']]

    def get_appointments(self, month=None, year=None):
        col = COLONNE['appuntamenti']
        paz = COLONNE['pazienti']

        appointments = []
        patients_dict = {}

        try:
            pazienti = dbf.Table(self.path_anagrafica, codepage='cp1252')
            pazienti.open()
            for r in pazienti:
                pid = str(r[paz['id']]).strip()
                name = str(r[paz['nome']]).strip() if r[paz['nome']] else ''
                if pid:
                    patients_dict[pid] = name
            pazienti.close()

            apps = dbf.Table(self.path_appuntamenti, codepage='cp1252')
            apps.open()
            for r in apps:
                if not r[col['data']]:
                    continue
                app_date = r[col['data']]
                if month and year and (app_date.month != month or app_date.year != year):
                    continue
                idpaz = str(r[col['id_paziente']]).strip()
                appointments.append({
                    'DATA': app_date,
                    'ORA_INIZIO': float(r[col['ora_inizio']] or 0),
                    'ORA_FINE': float(r[col['ora_fine']] or 0),
                    'TIPO': r[col['tipo']].strip() if r[col['tipo']] else '',
                    'STUDIO': r[col['studio']] or 1,
                    'NOTE': r[col['note']].strip() if r[col['note']] else '',
                    'DESCRIZIONE': r[col['descrizione']].strip() if r[col['descrizione']] else '',
                    'PAZIENTE': patients_dict.get(idpaz, '')
                })
            apps.close()
            return appointments

        except Exception as e:
            logging.error(f"Errore lettura appuntamenti: {e}")
            return []

    def test_connessione(self):
        """Debug connessione DBF"""
        self.leggi_tabella_dbf(self.path_appuntamenti)
        self.leggi_tabella_dbf(self.path_anagrafica)
