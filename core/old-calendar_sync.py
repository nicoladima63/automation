from datetime import datetime, timedelta
from datetime import time as dt_time  # per gestire gli orari
import time  # per i delay
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import json, os
import logging
import os.path
from config import (
    GOOGLE_CREDENTIALS_PATH,
    CALENDAR_TIMEZONE,
    STUDIO_CALENDAR_EMAIL,
    DEFAULT_CALENDAR_ID
)
from core.db_handler import DBHandler  # Aggiungi questo import
from google.api_core import retry

class GoogleCalendarSync:
    def __init__(self):
        self.credentials = None
        self.calendar_service = None
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.db_handler = DBHandler()  # Inizializza il db_handler

    def authenticate(self):
        """Gestisce l'autenticazione con Google Calendar"""
        try:
            token_path = os.path.join(os.path.dirname(__file__), 'token.json')
            
            if os.path.exists(token_path):
                self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GOOGLE_CREDENTIALS_PATH, 
                        self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=8080)
                
                # Salva il token nella stessa directory del file
                with open(token_path, 'w') as token:
                    token.write(self.credentials.to_json())
            
            # Costruisci il servizio calendar
            self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
            
            # Verifica l'account autenticato
            calendar = self.calendar_service.calendars().get(calendarId='primary').execute()
            logging.info(f"Autenticato come: {calendar['id']}")
            
            return True
            
        except Exception as e:
            logging.error(f"Errore durante l'autenticazione: {str(e)}")
            raise

    def _decimal_to_time(self, decimal_time):
        """Converte ora decimale in formato ore.minuti (es. 18.40 = 18:40)"""
        hours = int(decimal_time)
        minutes = int(round((decimal_time - hours) * 100))
        return dt_time(hours, minutes)

    def _safe_to_time(self, val):
        """Restituisce un oggetto time da float/int, oppure lo restituisce se è già time."""
        if isinstance(val, dt_time):
            return val
        try:
            return self._decimal_to_time(val)
        except Exception:
            return dt_time(8, 0)

    def sync_appointments(self):
        """Sincronizza gli appuntamenti con Google Calendar"""
        appointments = self.db_handler.get_appointments()
        for appointment in appointments:
            data_evento = appointment['DATA']
            ora_inizio = appointment.get('ORA_INIZIO', 0)
            ora_fine = appointment.get('ORA_FINE', 0)
            t_inizio = self._safe_to_time(ora_inizio)
            t_fine = self._safe_to_time(ora_fine)
            # Se ora_fine non valorizzato o uguale a ora_inizio, aggiungi 10 minuti
            if ora_fine == 0 or ora_fine == ora_inizio:
                from datetime import timedelta
                dt_inizio = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_inizio)
                dt_fine = dt_inizio + timedelta(minutes=10)
            else:
                dt_inizio = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_inizio)
                dt_fine = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_fine)
            event = {
                'summary': appointment['PAZIENTE'],
                'description': f"Dottore: {appointment['DOTTORE']}",
                'start': {
                    'dateTime': dt_inizio.isoformat(),
                    'timeZone': 'Europe/Rome',
                },
                'end': {
                    'dateTime': dt_fine.isoformat(),
                    'timeZone': 'Europe/Rome',
                }
            }
            try:
                self.calendar_service.events().insert(
                    calendarId='primary', 
                    body=event
                ).execute()
            except HttpError as error:
                print(f'Errore durante la sincronizzazione: {error}')

    def create_event(self, appointment,cal_id='primary'):
        """Crea un evento nel calendario Google"""
        data_evento = appointment['DATA']
        ora_inizio = appointment.get('ORA_INIZIO', 0)
        ora_fine = appointment.get('ORA_FINE', 0)
        t_inizio = self._safe_to_time(ora_inizio)
        t_fine = self._safe_to_time(ora_fine)
        # Se ora_fine non valorizzato o uguale a ora_inizio, aggiungi 10 minuti
        if ora_fine == 0 or ora_fine == ora_inizio:
            from datetime import timedelta
            dt_inizio = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_inizio)
            dt_fine = dt_inizio + timedelta(minutes=10)
        else:
            dt_inizio = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_inizio)
            dt_fine = datetime.combine(data_evento.date() if hasattr(data_evento, 'date') else data_evento, t_fine)
        event = {
            'summary': appointment['PAZIENTE'],
            'description': appointment['NOTE'] if appointment['NOTE'] else "",
            'start': {
                'dateTime': dt_inizio.isoformat(),
                'timeZone': CALENDAR_TIMEZONE,
            },
            'end': {
                'dateTime': dt_fine.isoformat(),
                'timeZone': CALENDAR_TIMEZONE,
            },
            'colorId': self._get_google_color_id(appointment['TIPO']),
            'reminders': {
                'useDefault': False,
                'overrides': []
            }
        }
        try:
            event = self.calendar_service.events().insert(
                calendarId=cal_id,
                body=event
            ).execute()
            logging.info(f"Evento creato: {event.get('htmlLink')}")
            return event
        except HttpError as error:
            logging.error(f'Errore durante la creazione evento: {error}')
            raise

    def get_calendars(self):
        """Recupera la lista dei calendari disponibili"""
        try:
            if not self.calendar_service:
                self.authenticate()
            
            calendars = []
            page_token = None
            
            while True:
                calendar_list = self.calendar_service.calendarList().list(
                    pageToken=page_token
                ).execute()
                
                for calendar_entry in calendar_list['items']:
                    calendars.append({
                        'id': calendar_entry['id'],
                        'summary': calendar_entry['summary'],
                        'primary': calendar_entry.get('primary', False)
                    })
                    
                page_token = calendar_list.get('nextPageToken')
                if not page_token:
                    break
            
            logging.info(f"Recuperati {len(calendars)} calendari")
            return calendars
            
        except Exception as e:
            logging.error(f"Errore nel recupero dei calendari: {str(e)}")
            raise

    def count_future_events(self, calendar_id):
        """Conta gli eventi futuri nel calendario"""
        try:
            now = datetime.now().isoformat() + 'Z'
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                singleEvents=True
            ).execute()
            return len(events_result.get('items', []))
        except Exception as e:
            logging.error(f"Errore conteggio eventi: {str(e)}")
            return 0

    def delete_all_events(self, calendar_id, progress_callback=None):
        """Cancella tutti gli eventi (passati e futuri) dal calendario specificato e azzera la mappatura locale."""
        import os
        try:
            if not self.calendar_service:
                self.authenticate()
            # Recupera tutti gli eventi, senza filtro timeMin
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            total = len(events)
            deleted = 0
            for event in events:
                try:
                    self.calendar_service.events().delete(
                        calendarId=calendar_id,
                        eventId=event['id']
                    ).execute()
                    deleted += 1
                    if progress_callback:
                        progress_callback(deleted, total)
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Errore eliminazione evento {event.get('id')}: {str(e)}")
            # Cancella anche il file di mappatura locale
            from core.sync_utils import SYNC_MAP_FILE
            if os.path.exists(SYNC_MAP_FILE):
                os.remove(SYNC_MAP_FILE)
                logging.info(f"File di mappatura locale '{SYNC_MAP_FILE}' eliminato dopo azzeramento calendario.")
            return deleted
        except Exception as e:
            logging.error(f"Errore pulizia calendario: {str(e)}")
            raise

    def sync_appointments_for_month(self, month=None, year=None, studio_calendar_ids=None, progress_callback=None, debug_export_first_50=False):
        """Sincronizza gli appuntamenti usando i calendar ID specifici per studio. Se debug_export_first_50 è True, esporta i primi 50 appuntamenti in JSON e interrompe."""
        try:
            if not studio_calendar_ids:
                raise ValueError("ID calendari studi non forniti")
            
            appointments = self.db_handler.get_appointments(month=month, year=year)

            # BLOCCO DEBUG: esporta TUTTI gli EVENTI FORMATTATI PER GOOGLE CALENDAR e interrompe la funzione
            if debug_export_first_50:
                events_to_export = []
                for app in appointments:
                    if not app.get('PAZIENTE'):
                        continue
                    data_evento = app['DATA']
                    if isinstance(data_evento, str):
                        try:
                            data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
                        except Exception:
                            continue
                    if not isinstance(app['ORA_INIZIO'], (int, float)) or not isinstance(app['ORA_FINE'], (int, float)):
                        continue
                    color_id = str(self._get_google_color_id(app['TIPO'] if app['TIPO'] else '1'))
                    event = {
                        'summary': app.get('PAZIENTE', 'Senza nome'),
                        'description': app.get('NOTE', ''),
                        'start': {
                            'dateTime': datetime.combine(
                                data_evento, 
                                self._decimal_to_time(app['ORA_INIZIO'])
                            ).isoformat(),
                            'timeZone': 'Europe/Rome',
                        },
                        'end': {
                            'dateTime': datetime.combine(
                                data_evento, 
                                self._decimal_to_time(app['ORA_FINE'])
                            ).isoformat(),
                            'timeZone': 'Europe/Rome',
                        },
                        'colorId': color_id
                    }
                    events_to_export.append(event)
                with open('debug_appointment.json', 'w', encoding='utf-8') as f:
                    json.dump(events_to_export, f, ensure_ascii=False, indent=2)
                logging.info(f"Esportati {len(events_to_export)} eventi formattati in debug_appointment.json. Sincronizzazione interrotta per debug.")
                return {'debug_exported': len(events_to_export), 'total': len(appointments)}

            # Raggruppa gli appuntamenti per studio
            appointments_by_studio = {}
            success = 0
            errors = 0
            studio_counts = {1: 0, 2: 0}
            
            for app in appointments:
                studio = int(app['STUDIO'])
                if studio in studio_calendar_ids:
                    if studio not in appointments_by_studio:
                        appointments_by_studio[studio] = []
                    appointments_by_studio[studio].append(app)
                    
            # Processa gli appuntamenti per studio in batch di 10
            total = sum(len(apps) for apps in appointments_by_studio.values())
            processed = 0
            for studio, apps in appointments_by_studio.items():
                calendar_id = studio_calendar_ids.get(studio)
                if not calendar_id:
                    continue

                batch_size = 10  # Limita a 10 appuntamenti per batch
                for i in range(0, len(apps), batch_size):
                    batch = apps[i:i + batch_size]
                    if progress_callback:
                        progress_callback(processed, total, f"Studio {studio}: processando batch {i//batch_size + 1}")

                    for app in batch:
                        try:
                            if not app.get('PAZIENTE'):
                                logging.warning(f"Appuntamento senza nome paziente saltato: {app}")
                                continue

                            data_evento = app['DATA']
                            if isinstance(data_evento, str):
                                try:
                                    data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
                                except Exception as e:
                                    logging.warning(f"Data non valida per appuntamento {app}: {e}")
                                    continue

                            if not isinstance(app['ORA_INIZIO'], (int, float)) or not isinstance(app['ORA_FINE'], (int, float)):
                                logging.warning(f"Orario non valido per appuntamento {app}")
                                continue

                            color_id = str(self._get_google_color_id(app['TIPO'] if app['TIPO'] else '1'))

                            # Logica coerente per il summary
                            paziente = app.get('PAZIENTE', '').strip()
                            descrizione = app.get('DESCRIZIONE', '').strip()
                            studio = int(app.get('STUDIO', 0))
                            medico = int(app.get('MEDICO', 0)) if 'MEDICO' in app else 0
                            if studio == 0 and medico == 0:
                                summary = "Nota del giorno"
                            elif not paziente:
                                summary = descrizione if descrizione else "Appuntamento paziente non in quaderno"
                            else:
                                summary = paziente
                            event = {
                                'summary': summary,
                                'description': app.get('NOTE', ''),
                                'start': {
                                    'dateTime': datetime.combine(
                                        data_evento, 
                                        self._decimal_to_time(app['ORA_INIZIO'])
                                    ).isoformat(),
                                    'timeZone': 'Europe/Rome',
                                },
                                'end': {
                                    'dateTime': datetime.combine(
                                        data_evento, 
                                        self._decimal_to_time(app['ORA_FINE'])
                                    ).isoformat(),
                                    'timeZone': 'Europe/Rome',
                                },
                                'colorId': color_id
                            }

                            # Logging dettagliato prima dell'invio
                            logging.info(f"Invio evento: {json.dumps(event, ensure_ascii=False)}")
                            retry_count = 0
                            max_retries = 3

                            while retry_count < max_retries:
                                try:
                                    self.calendar_service.events().insert(
                                        calendarId=calendar_id,
                                        body=event
                                    ).execute()
                                    success += 1
                                    studio_counts[studio] += 1
                                    break
                                except HttpError as error:
                                    logging.error(f"Errore durante la creazione evento: {error}")
                                    try:
                                        logging.error(f"Payload evento: {json.dumps(event, ensure_ascii=False, indent=2)}")
                                        logging.error(f"Dettagli risposta: {getattr(error, 'content', str(error))}")
                                        if error.resp.status == 400:
                                            with open('debug_sync_badrequest.json', 'a', encoding='utf-8') as f:
                                                json.dump({'event': event, 'appuntamento': app, 'error': str(error)}, f, ensure_ascii=False)
                                                f.write('\n')
                                    except Exception as e:
                                        logging.error(f"Errore serializzazione evento: {e}")
                                    if error.resp.status == 403 and "rateLimitExceeded" in str(error):
                                        retry_count += 1
                                        wait_time = min(2 ** retry_count, 5)
                                        if progress_callback:
                                            progress_callback(processed, total, f"Rate limit - attendo {wait_time}s...")
                                        time.sleep(wait_time)
                                    else:
                                        break  # Non riprovare su altri errori
                                except Exception as ex:
                                    logging.error(f"Eccezione generica durante la creazione evento: {ex}")
                                    try:
                                        with open('debug_sync_badrequest.json', 'a', encoding='utf-8') as f:
                                            json.dump({'event': event, 'appuntamento': app, 'error': str(ex)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except Exception as e:
                                        logging.error(f"Errore serializzazione evento generico: {e}")
                                    break
                        except Exception as e:
                            errors += 1
                            logging.error(f"Errore creazione evento: {str(e)}")
                        processed += 1
                    # Dopo il primo batch di 10, interrompi la sincronizzazione
                    logging.info(f"Sincronizzazione interrotta dopo {batch_size} appuntamenti per debug.")
                    return {
                        'total': total,
                        'success': success,
                        'errors': errors,
                        'studio_1': studio_counts.get(1, 0),
                        'studio_2': studio_counts.get(2, 0),
                        'debug_batch': batch_size
                    }
        
            return {
                'total': total,
                'success': success,
                'errors': errors,
                'studio_1': studio_counts.get(1, 0),
                'studio_2': studio_counts.get(2, 0)
            }
                    
        except Exception as e:
            logging.error(f"Errore sincronizzazione: {str(e)}")
            raise

    def _get_google_color_id(self, tipo_appuntamento):
        """Converte il tipo appuntamento nel colorId di Google Calendar"""
        from config import GOOGLE_COLOR_MAP
        return GOOGLE_COLOR_MAP.get(tipo_appuntamento, '1')  # Default a Lavender se non trovato