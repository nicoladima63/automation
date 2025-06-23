from datetime import datetime, timedelta, time as dt_time
import time
import json
import os
import logging

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.api_core import retry

from config.constants import GOOGLE, COLONNE

class GoogleCalendarSync:
    def __init__(self, db_handler):
        self.credentials = None
        self.calendar_service = None
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.db_handler = db_handler

    def authenticate(self):
        try:
            token_path = os.path.join(os.path.dirname(__file__), 'token.json')

            if os.path.exists(token_path):
                self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)

            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GOOGLE['credentials_path'], 
                        self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=8080)

                with open(token_path, 'w') as token:
                    token.write(self.credentials.to_json())

            self.calendar_service = build('calendar', 'v3', credentials=self.credentials)

            calendar = self.calendar_service.calendars().get(calendarId='primary').execute()
            logging.info(f"Autenticato come: {calendar['id']}")
            return True

        except Exception as e:
            logging.error(f"Errore autenticazione: {e}")
            raise

    def _decimal_to_time(self, decimal_time):
        hours = int(decimal_time)
        minutes = int(round((decimal_time - hours) * 100))
        return dt_time(hours, minutes)

    def _safe_to_time(self, val):
        if isinstance(val, dt_time):
            return val
        try:
            return self._decimal_to_time(val)
        except Exception:
            return dt_time(8, 0)

    def _get_google_color_id(self, tipo):
        from config import GOOGLE_COLOR_MAP
        return GOOGLE_COLOR_MAP.get(tipo, '1')

    def sync_appointments_for_month(self, month=None, year=None, studio_calendar_ids=None, progress_callback=None, debug_export_first_50=False):
        try:
            if not studio_calendar_ids:
                raise ValueError("ID calendari non forniti")

            appointments = self.db_handler.get_appointments(month=month, year=year)

            if debug_export_first_50:
                events_to_export = []
                for app in appointments[:50]:
                    if not app.get('PAZIENTE'):
                        continue
                    data_evento = app['DATA']
                    if isinstance(data_evento, str):
                        data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
                    if not isinstance(app['ORA_INIZIO'], (int, float)) or not isinstance(app['ORA_FINE'], (int, float)):
                        continue
                    event = {
                        'summary': app.get('PAZIENTE', 'Senza nome'),
                        'description': app.get('NOTE', ''),
                        'start': {
                            'dateTime': datetime.combine(data_evento, self._decimal_to_time(app['ORA_INIZIO'])).isoformat(),
                            'timeZone': GOOGLE['timezone'],
                        },
                        'end': {
                            'dateTime': datetime.combine(data_evento, self._decimal_to_time(app['ORA_FINE'])).isoformat(),
                            'timeZone': GOOGLE['timezone'],
                        },
                        'colorId': self._get_google_color_id(app.get('TIPO'))
                    }
                    events_to_export.append(event)

                with open('debug_appointment.json', 'w', encoding='utf-8') as f:
                    json.dump(events_to_export, f, ensure_ascii=False, indent=2)

                logging.info(f"Esportati {len(events_to_export)} eventi.")
                return {'debug_exported': len(events_to_export), 'total': len(appointments)}

            appointments_by_studio = {}
            for app in appointments:
                studio = int(app.get('STUDIO', 0))
                if studio in studio_calendar_ids:
                    appointments_by_studio.setdefault(studio, []).append(app)

            total = sum(len(a) for a in appointments_by_studio.values())
            success = errors = 0

            for studio, apps in appointments_by_studio.items():
                calendar_id = studio_calendar_ids[studio]

                for app in apps:
                    try:
                        if not app.get('PAZIENTE'):
                            continue

                        data_evento = app['DATA']
                        if isinstance(data_evento, str):
                            data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()

                        t_inizio = self._safe_to_time(app.get('ORA_INIZIO'))
                        t_fine = self._safe_to_time(app.get('ORA_FINE'))

                        dt_inizio = datetime.combine(data_evento, t_inizio)
                        dt_fine = datetime.combine(data_evento, t_fine) if t_fine > t_inizio else dt_inizio + timedelta(minutes=10)

                        summary = app.get('PAZIENTE') or app.get('DESCRIZIONE') or "Appuntamento"

                        event = {
                            'summary': summary.strip(),
                            'description': app.get('NOTE', ''),
                            'start': {
                                'dateTime': dt_inizio.isoformat(),
                                'timeZone': GOOGLE['timezone'],
                            },
                            'end': {
                                'dateTime': dt_fine.isoformat(),
                                'timeZone': GOOGLE['timezone'],
                            },
                            'colorId': self._get_google_color_id(app.get('TIPO'))
                        }

                        self.calendar_service.events().insert(
                            calendarId=calendar_id,
                            body=event
                        ).execute()

                        success += 1

                    except HttpError as error:
                        logging.error(f"Errore Google API: {error}")
                        errors += 1
                    except Exception as e:
                        logging.error(f"Errore generico: {e}")
                        errors += 1

            return {'total': total, 'success': success, 'errors': errors}

        except Exception as e:
            logging.error(f"Errore sincronizzazione: {e}")
            raise
