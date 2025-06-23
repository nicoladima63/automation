import os
import schedule
import time
from datetime import datetime, date, timedelta
import dbf
import pandas as pd
from twilio.rest import Client
import logging
import argparse
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env
load_dotenv()

# Configurazione logging con encoding UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('promemoria_appuntamenti.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class GestorePromemoriaAppuntamenti:
    def __init__(self, modalita_test=False, test_numero=None):
        self.modalita_test = modalita_test
        self.test_numero = test_numero

        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN') 
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        self.path_appuntamenti = os.getenv('PATH_APPUNTAMENTI_DBF', './appunta.dbf')
        self.path_anagrafica = os.getenv('PATH_ANAGRAFICA_DBF', './pazienti.dbf')

        if not self.modalita_test and self.twilio_account_sid and self.twilio_auth_token:
            self.client = Client(self.twilio_account_sid, self.twilio_auth_token)
        else:
            if self.modalita_test:
                logging.info("MODALITÀ TEST - Nessun messaggio WhatsApp verrà inviato")
            else:
                logging.warning("Credenziali Twilio non configurate!")
            self.client = None

    def decodifica_tipo_appuntamento(self, codice_guardia):
        """
        Decodifica il tipo di appuntamento dal campo DB_GUARDIA
        """
        tipi_appuntamento = {
            'V': 'Prima visita',
            'I': 'Igiene',
            'C': 'Conservativa',
            'E': 'Endodonzia',
            'H': 'Chirurgia',
            'P': 'Protesi',
            'O': 'Ortodonzia',
            'L': 'Implantologia',
            'R': 'Parodontologia',
            'S': 'Controllo'
        }
        
        if pd.isna(codice_guardia):
            return ''
        
        codice = str(codice_guardia).strip().upper()
        return tipi_appuntamento.get(codice, codice)
    
    def decodifica_medico(self, numero_medico):
        """
        Decodifica il medico dal campo DB_APMEDIC
        """
        medici = {
            1: 'Dr. Nicola',
            2: 'Dr.ssa Lara',
            3: 'Dr. Giacomo',
            4: 'Dr. Roberto',
            5: 'Dr.ssa Anet',
            6: 'Dr.ssa Rossella'
        }
        
        if pd.isna(numero_medico):
            return ''
        
        try:
            numero = int(float(numero_medico))
            return medici.get(numero, f'Medico {numero}')
        except (ValueError, TypeError):
            return ''
    
    def calcola_giorni_prenotazione(self, data_inserimento):
        """
        Calcola i giorni trascorsi dalla prenotazione
        """
        if pd.isna(data_inserimento):
            return 0
        
        try:
            data_inserimento_dt = pd.to_datetime(data_inserimento, errors='coerce')
            if pd.isna(data_inserimento_dt):
                return 0
            
            oggi = pd.Timestamp.now()
            giorni = (oggi - data_inserimento_dt).days
            return giorni
        except:
            return 0

    def debug_campi_appuntamenti(self):
        """
        Funzione di debug per ispezionare i campi della tabella appuntamenti
        """
        try:
            df_appuntamenti = self.leggi_tabella_dbf(self.path_appuntamenti)
            if not df_appuntamenti.empty:
                #logging.info("=== DEBUG CAMPI APPUNTAMENTI ===")
                #logging.info(f"Campi disponibili: {list(df_appuntamenti.columns)}")
                
                # Mostra i primi 3 record per capire il contenuto
                for i, row in df_appuntamenti.head(3).iterrows():
                    logging.info(f"Record {i+1}:")
                    for col in df_appuntamenti.columns:
                        logging.info(f"  {col}: {row[col]}")
                    logging.info("---")
                logging.info("=== FINE DEBUG ===")
        except Exception as e:
            logging.error(f"Errore debug: {e}")

    def leggi_tabella_dbf(self, percorso_file):
        try:
            table = dbf.Table(percorso_file, codepage='cp1252')
            table.open()

            records = []
            for record in table:
                try:
                    record_dict = {field: record[field] for field in table.field_names}
                    records.append(record_dict)
                except Exception as field_error:
                    logging.warning(f"Errore lettura record in {percorso_file}: {field_error}")
                    continue

            table.close()
            df = pd.DataFrame(records)
            logging.info(f"Letta tabella {percorso_file}: {len(df)} record")

            return df

        except Exception as e:
            logging.error(f"Errore lettura {percorso_file}: {e}")
            return pd.DataFrame()

    def estrai_appuntamenti_domani(self, data_test=None):
        try:
            df_appuntamenti = self.leggi_tabella_dbf(self.path_appuntamenti)

            if df_appuntamenti.empty:
                return pd.DataFrame()

            target_date = data_test if data_test else date.today() + timedelta(days=1)
            if 'DB_APDATA' in df_appuntamenti.columns:
                df_appuntamenti['DATA_APP'] = pd.to_datetime(df_appuntamenti['DB_APDATA'], errors='coerce').dt.date
                return df_appuntamenti[df_appuntamenti['DATA_APP'] == target_date]
            else:
                logging.error("Campo DB_APDATA non trovato")
                return pd.DataFrame()

        except Exception as e:
            logging.error(f"Errore estrazione appuntamenti: {e}")
            return pd.DataFrame()

    def recupera_dati_pazienti(self, lista_id_pazienti):
        try:
            df_anagrafica = self.leggi_tabella_dbf(self.path_anagrafica)

            if df_anagrafica.empty:
                return pd.DataFrame()

            col_id = 'DB_CODE'
            col_nome = 'DB_PANOME'
            col_telefono_fisso = 'DB_PATELEF'
            col_cellulare = 'DB_PACELLU'

            if col_id not in df_anagrafica.columns or col_nome not in df_anagrafica.columns:
                return pd.DataFrame()

            pazienti = df_anagrafica[df_anagrafica[col_id].isin(lista_id_pazienti)].copy()
            if pazienti.empty:
                return pd.DataFrame()

            pazienti['telefono_uso'] = ''
            if col_cellulare in df_anagrafica.columns:
                mask_cell = pazienti[col_cellulare].notna() & (pazienti[col_cellulare].str.strip() != '')
                pazienti.loc[mask_cell, 'telefono_uso'] = pazienti.loc[mask_cell, col_cellulare]

            if col_telefono_fisso in df_anagrafica.columns:
                mask_fisso = (pazienti['telefono_uso'] == '') & pazienti[col_telefono_fisso].notna() & (pazienti[col_telefono_fisso].str.strip() != '')
                pazienti.loc[mask_fisso, 'telefono_uso'] = pazienti.loc[mask_fisso, col_telefono_fisso]

            pazienti = pazienti[pazienti['telefono_uso'].str.strip() != '']
            risultato = pazienti[[col_id, col_nome, 'telefono_uso']].copy()
            risultato.columns = ['id_paziente', 'nome', 'telefono']
            risultato['nome'] = risultato['nome'].fillna('Nome sconosciuto').str.strip()
            risultato['telefono'] = risultato['telefono'].str.strip()
            return risultato

        except Exception as e:
            logging.error(f"Errore recupero dati pazienti: {e}")
            return pd.DataFrame()

    def normalizza_numero_telefono(self, numero_telefono):
        """
        Normalizza il numero di telefono per WhatsApp
        Gestisce prefissi internazionali esistenti e numeri italiani
        """
        if not numero_telefono or pd.isna(numero_telefono):
            return None
        
        # Pulisci il numero da spazi, trattini e parentesi
        numero_pulito = str(numero_telefono).replace(' ', '').replace('-', '').replace('(', '').replace(')', '').strip()
        
        # Se è vuoto dopo la pulizia, ritorna None
        if not numero_pulito:
            return None
        
        # Se inizia già con +, è già un numero internazionale
        if numero_pulito.startswith('+'):
            logging.info(f"Numero internazionale rilevato: {numero_pulito}")
            return numero_pulito
        
        # Se inizia con 00, converte in formato +
        if numero_pulito.startswith('00'):
            numero_convertito = '+' + numero_pulito[2:]
            logging.info(f"Convertito da 00 a +: {numero_pulito} -> {numero_convertito}")
            return numero_convertito
        
        # Se inizia con 39 ed è lungo abbastanza per essere un numero italiano con prefisso
        if numero_pulito.startswith('39') and len(numero_pulito) >= 12:
            numero_convertito = '+' + numero_pulito
            logging.info(f"Rilevato numero italiano con prefisso: {numero_pulito} -> {numero_convertito}")
            return numero_convertito
        
        # Se inizia con 3 (cellulare italiano) o con un prefisso fisso italiano
        if numero_pulito.startswith('3') or any(numero_pulito.startswith(prefisso) for prefisso in ['0', '1', '2', '4', '5', '6', '7', '8', '9']):
            if len(numero_pulito) >= 9:  # Numero italiano valido
                numero_convertito = f"+39{numero_pulito}"
                logging.info(f"Aggiunto prefisso italiano: {numero_pulito} -> {numero_convertito}")
                return numero_convertito
        
        # Se non riconosce il formato, prova comunque ad aggiungere +39 (fallback per numeri italiani)
        logging.warning(f"Formato numero non riconosciuto, tentativo con +39: {numero_pulito}")
        return f"+39{numero_pulito}"
    
    def invia_messaggio_whatsapp(self, numero_telefono, nome_paziente, dettagli_appuntamento="", promemoria_prenotazione=""):
        numero_whatsapp = self.normalizza_numero_telefono(numero_telefono)
        
        if not numero_whatsapp:
            logging.error(f"Numero di telefono non valido per {nome_paziente}: {numero_telefono}")
            return False

        # Costruisci il messaggio base
        messaggio = f"Gentile {nome_paziente},\n\nLe ricordiamo che ha un appuntamento DOMANI {dettagli_appuntamento.strip()}."
        
        # Aggiungi promemoria sulla prenotazione se necessario
        if promemoria_prenotazione:
            messaggio += f"\n\n{promemoria_prenotazione}"
        
        messaggio += "\n\nSe non può presentarsi, La preghiamo di avvisarci il prima possibile rispondendo a questo messaggio o chiamandoci.\n\nGrazie!"

        if self.modalita_test:
            logging.info(f"[TEST] Messaggio per {nome_paziente} ({numero_whatsapp}):\n{messaggio}")
            return True

        if not self.client:
            logging.error("Client Twilio non inizializzato")
            return False

        try:
            message = self.client.messages.create(
                from_=self.twilio_whatsapp_number,
                body=messaggio,
                to=f'whatsapp:{numero_whatsapp}'
            )
            logging.info(f"Messaggio inviato a {nome_paziente} ({numero_whatsapp}): {message.sid}")
            return True
        except Exception as e:
            logging.error(f"Errore invio messaggio a {nome_paziente}: {e}")
            return False

    def elabora_promemoria_giornalieri(self, data_test=None, solo_test_primo=False):
        logging.info("=== INIZIO ELABORAZIONE PROMEMORIA ===")
        
        # Determina la data di domani
        if data_test:
            target_date = data_test
        else:
            target_date = date.today() + timedelta(days=1)
        
        # Controlla se domani è sabato (5) o domenica (6)
        if target_date.weekday() >= 5:  # 5=sabato, 6=domenica
            giorno_nome = "sabato" if target_date.weekday() == 5 else "domenica"
            logging.info(f"Domani è {giorno_nome} ({target_date}) - Nessun invio di promemoria")
            logging.info("=== FINE ELABORAZIONE PROMEMORIA ===")
            return
        
        appuntamenti = self.estrai_appuntamenti_domani(data_test)
        logging.info(f"Appuntamenti trovati per {target_date}: {len(appuntamenti)}")
        
        if appuntamenti.empty:
            logging.info("Nessun appuntamento trovato")
            return

        # Debug: mostra i campi disponibili se in modalità test
        if self.modalita_test:
            self.debug_campi_appuntamenti()

        if 'DB_APPACOD' not in appuntamenti.columns:
            logging.error("Campo DB_APPACOD mancante")
            return

        lista_id_pazienti = appuntamenti['DB_APPACOD'].dropna().unique().tolist()
        logging.info(f"ID pazienti con appuntamenti: {lista_id_pazienti[:5]}...")  # Mostra solo i primi 5
        
        dati_pazienti = self.recupera_dati_pazienti(lista_id_pazienti)
        logging.info(f"Pazienti recuperati: {len(dati_pazienti)}")
        
        if dati_pazienti.empty:
            logging.warning("Nessun dato paziente recuperato")
            return

        if self.test_numero:
            logging.info(f"🔍 Filtro per numero: {self.test_numero}")
            
            # Mostra alcuni numeri per capire il formato
            if not dati_pazienti.empty:
                logging.info("📱 Primi 5 numeri nel database:")
                for i, (_, paziente) in enumerate(dati_pazienti.head(5).iterrows()):
                    logging.info(f"  {i+1}: '{paziente['telefono']}' - {paziente['nome']}")
            
            # Cerca il numero in modo più flessibile
            numero_trovato = False
            for _, paziente in dati_pazienti.iterrows():
                tel = str(paziente['telefono']).strip()
                tel_clean = tel.replace('+', '').replace(' ', '').replace('-', '')
                test_clean = self.test_numero.replace('+', '').replace(' ', '').replace('-', '')
                
                if test_clean in tel_clean or tel_clean in test_clean:
                    numero_trovato = True
                    logging.info(f"✅ TROVATO match: '{tel}' per paziente {paziente['nome']}")

            if not numero_trovato:
                logging.warning(f"❌ Numero {self.test_numero} NON trovato nel database!")
            
            # Applica il filtro con correzione regex
            dati_pazienti = dati_pazienti[dati_pazienti['telefono'].str.contains(self.test_numero, regex=False, na=False)]
            logging.info(f"Pazienti dopo filtro: {len(dati_pazienti)}")

        if solo_test_primo:
            dati_pazienti = dati_pazienti.head(1)
            logging.info("🎯 Modalità solo-primo attiva: invio solo al primo paziente")

        messaggi_inviati = 0
        for _, paziente in dati_pazienti.iterrows():
            app_paziente = appuntamenti[appuntamenti['DB_APPACOD'] == paziente['id_paziente']]
            dettagli = ""
            promemoria_prenotazione = ""
            
            if not app_paziente.empty:
                app = app_paziente.iloc[0]
                
                # Estrai i dati corretti dai campi specificati
                orario_inizio = app.get('DB_APOREIN')  # Corretto dal debug precedente
                orario_fine = app.get('DB_APOREOU')
                codice_tipo = app.get('DB_GUARDIA')
                numero_medico = app.get('DB_APMEDIC')
                data_inserimento = app.get('DB_APDATAI')
                
                # Decodifica i valori
                orario_inizio_str = str(orario_inizio).strip() if pd.notna(orario_inizio) else ''
                orario_fine_str = str(orario_fine).strip() if pd.notna(orario_fine) else ''
                tipo_appuntamento = self.decodifica_tipo_appuntamento(codice_tipo)
                nome_medico = self.decodifica_medico(numero_medico)
                giorni_prenotazione = self.calcola_giorni_prenotazione(data_inserimento)

                # Debug: mostra i valori estratti se in modalità test
                if self.modalita_test:
                    logging.info(f"📋 DEBUG - Paziente {paziente['nome']}:")
                    logging.info(f"  Orario inizio: {orario_inizio} -> '{orario_inizio_str}'")
                    logging.info(f"  Orario fine: {orario_fine} -> '{orario_fine_str}'")
                    logging.info(f"  Codice tipo: {codice_tipo} -> {tipo_appuntamento}")
                    logging.info(f"  Numero medico: {numero_medico} -> {nome_medico}")
                    logging.info(f"  Giorni prenotazione: {giorni_prenotazione}")

                # Costruisci i dettagli dell'appuntamento
                parti_dettaglio = []
                
                if orario_inizio_str:
                    if orario_fine_str and orario_fine_str != orario_inizio_str:
                        parti_dettaglio.append(f"dalle {orario_inizio_str} alle {orario_fine_str}")
                    else:
                        parti_dettaglio.append(f"alle {orario_inizio_str}")
                
                if tipo_appuntamento:
                    parti_dettaglio.append(f"per {tipo_appuntamento}")
                
                if nome_medico:
                    parti_dettaglio.append(f"con {nome_medico}")
                
                dettagli = " ".join(parti_dettaglio)
                
                # Aggiungi promemoria se la prenotazione è stata fatta più di 15 giorni fa
                if giorni_prenotazione >= 15:
                    promemoria_prenotazione = f"Ricordiamo che questa seduta è stata fissata {giorni_prenotazione} giorni fa."

            if self.invia_messaggio_whatsapp(paziente['telefono'], paziente['nome'], dettagli, promemoria_prenotazione):
                messaggi_inviati += 1
                if not self.modalita_test:
                    time.sleep(2)

        logging.info(f"Elaborazione completata: {messaggi_inviati} messaggi {'simulati' if self.modalita_test else 'inviati'}")
        logging.info("=== FINE ELABORAZIONE PROMEMORIA ===")

    # --- FUNZIONI DI TEST E DEBUG SPOSTATE DA script.py ---
    # Vedi test_tools.py per test_connessione_database
    def test_twilio_config(self):
        """Test configurazione Twilio"""
        logging.info("=== TEST CONFIGURAZIONE TWILIO ===")
        
        if not self.twilio_account_sid:
            logging.error("TWILIO_ACCOUNT_SID non configurato")
        else:
            logging.info("TWILIO_ACCOUNT_SID: configurato")
        
        if not self.twilio_auth_token:
            logging.error("TWILIO_AUTH_TOKEN non configurato")
        else:
            logging.info("TWILIO_AUTH_TOKEN: configurato")
        
        if not self.twilio_whatsapp_number:
            logging.error("TWILIO_WHATSAPP_NUMBER non configurato")
        else:
            logging.info(f"TWILIO_WHATSAPP_NUMBER: {self.twilio_whatsapp_number}")
        
        if self.client:
            try:
                # Test connessione
                account = self.client.api.accounts(self.twilio_account_sid).fetch()
                logging.info(f"Connessione Twilio OK - Account: {account.friendly_name}")
            except Exception as e:
                logging.error(f"Errore connessione Twilio: {e}")
        
        logging.info("=== FINE TEST TWILIO ===")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--test-db', action='store_true')
    parser.add_argument('--test-twilio', action='store_true')
    parser.add_argument('--test-numero', type=str)
    parser.add_argument('--test-data', type=str)
    parser.add_argument('--esegui-ora', action='store_true')
    parser.add_argument('--solo-primo', action='store_true')
    args = parser.parse_args()

    data_test = None
    if args.test_data:
        try:
            data_test = datetime.strptime(args.test_data, '%Y-%m-%d').date()
        except ValueError:
            logging.error("Formato data non valido. Usa YYYY-MM-DD")
            return

    gestore = GestorePromemoriaAppuntamenti(modalita_test=args.test, test_numero=args.test_numero)

    if args.test_db:
        gestore.test_connessione_database()
        return

    if args.test_twilio:
        gestore.test_twilio_config()
        return

    if args.esegui_ora:
        gestore.elabora_promemoria_giornalieri(data_test, args.solo_primo)
        return

    schedule.every().day.at("18:30").do(
        gestore.elabora_promemoria_giornalieri,
        data_test=None,
        solo_test_primo=False
    )
    logging.info(f"Sistema promemoria avviato in modalità {'TEST' if args.test else 'PRODUZIONE'} - invierà messaggi alle 18:30")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()