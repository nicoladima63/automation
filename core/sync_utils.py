import hashlib
import json
from datetime import datetime, date, time
import logging

SYNC_MAP_FILE = 'synced_events.json'

# Colonne standard (adatta se necessario)
COL_DATA = 'DATA'
COL_ORA_INIZIO = 'ORA_INIZIO'
COL_ORA_FINE = 'ORA_FINE'
COL_STUDIO = 'STUDIO'
COL_PAZIENTE = 'PAZIENTE'
COL_DESCRIZIONE = 'DESCRIZIONE'
COL_NOTE = 'NOTE'


def _float_to_time(val):
    """Converte un float tipo 8.4 in time(8,40) (minuti in base 10)."""
    try:
        h = int(val)
        m = int(round((val - h) * 100))
        if m >= 60:
            m = 59  # fallback di sicurezza
        return datetime.min.time().replace(hour=h, minute=m)
    except Exception:
        return datetime.min.time().replace(hour=8, minute=0)


def _normalize_for_hash(app):
    """Restituisce una copia normalizzata dell'appuntamento per hash/idempotenza."""
    norm = dict(app)
    # Normalizza DATA e orari in stringa ISO
    if isinstance(norm.get('DATA'), datetime):
        norm['DATA'] = norm['DATA'].isoformat()
    if isinstance(norm.get('ORA_INIZIO'), time):
        norm['ORA_INIZIO'] = norm['ORA_INIZIO'].strftime('%H:%M')
    if isinstance(norm.get('ORA_FINE'), time):
        norm['ORA_FINE'] = norm['ORA_FINE'].strftime('%H:%M')
    return norm


def compute_appointment_hash(app):
    norm = _normalize_for_hash(app)
    relevant = f"{norm['DATA']}_{norm['ORA_INIZIO']}_{norm['ORA_FINE']}_{norm['STUDIO']}_{norm.get('PAZIENTE','')}_{norm.get('DESCRIZIONE','')}_{norm.get('NOTE','')}"
    return hashlib.md5(relevant.encode('utf-8')).hexdigest()


def load_sync_map(sync_map_file=SYNC_MAP_FILE):
    try:
        with open(sync_map_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_sync_map(sync_map, sync_map_file=SYNC_MAP_FILE):
    with open(sync_map_file, 'w', encoding='utf-8') as f:
        json.dump(sync_map, f, ensure_ascii=False, indent=2)


def map_appointment(app):
    paziente = app.get(COL_PAZIENTE, '').strip()
    data = app.get(COL_DATA)
    tipo = app.get('TIPO', '').strip() or app.get('DB_APPACOD', '').strip()
    note = app.get(COL_NOTE, '').strip()
    dottore = app.get('DOTTORE', '').strip() or app.get('DB_DOTT', '').strip() or app.get('MEDICO', '').strip() or str(app.get('DB_APMEDIC', '')).strip()
    studio = app.get(COL_STUDIO)
    descrizione = app.get(COL_DESCRIZIONE, '').strip()
    ora_inizio = app.get(COL_ORA_INIZIO)
    ora_fine = app.get(COL_ORA_FINE)

    # Conversione robusta dei campi numerici
    try:
        dottore_int = int(dottore) if dottore not in (None, '', 'None') else 0
    except Exception:
        dottore_int = 0
    try:
        studio_int = int(studio) if studio not in (None, '', 'None') else 0
    except Exception:
        studio_int = 0

    # Conversione orari float in oggetti time
    t_inizio = _float_to_time(ora_inizio) if ora_inizio is not None else datetime.min.time().replace(hour=8)
    t_fine = _float_to_time(ora_fine) if ora_fine is not None else None

    # Se ora_fine non valorizzato o uguale a ora_inizio, aggiungi 10 minuti di default
    if t_fine is None or t_fine == t_inizio:
        from datetime import timedelta
        dt_inizio = datetime.combine(date(2000,1,1), t_inizio)
        dt_fine = dt_inizio + timedelta(minutes=10)
        t_fine = dt_fine.time()

    # Conversione robusta data
    if not isinstance(data, datetime):
        # Se è un date puro, lo converto in datetime con orario t_inizio
        if isinstance(data, date):
            data = datetime.combine(data, t_inizio)
        else:
            try:
                data = datetime.strptime(str(data), '%Y-%m-%d %H:%M:%S')
            except Exception:
                raise ValueError(f"DATA non è un datetime valido: {data} (tipo: {type(data)})")

    # Nota giornaliera: dottore==0, studio==0, paziente vuoto
    if dottore_int == 0 and studio_int == 0 and not paziente:
        summary = f"NOTA GIORNALIERA"
        description = note or descrizione or "Nota giornaliera gestionale"
        mapped = {
            'PAZIENTE': '',
            'DATA': data,
            'ORA_INIZIO': t_inizio,
            'ORA_FINE': t_fine,
            'STUDIO': studio_int,
            'DESCRIZIONE': summary,
            'NOTE': description,
            'TIPO': tipo,
            'DOTTORE': dottore_int,
            'SPECIAL': 'NOTA_GIORNALIERA',
        }
        return mapped

    # Appuntamento di servizio: dottore>0, studio>0, paziente vuoto
    if dottore_int > 0 and studio_int > 0 and not paziente:
        summary = f"SERVIZIO (Dott. {dottore_int}, Studio {studio_int})"
        description = note or descrizione or f"Servizio interno gestionale (Dottore {dottore_int}, Studio {studio_int})"
        mapped = {
            'PAZIENTE': '',
            'DATA': data,
            'ORA_INIZIO': t_inizio,
            'ORA_FINE': t_fine,
            'STUDIO': studio_int,
            'DESCRIZIONE': summary,
            'NOTE': description,
            'TIPO': tipo,
            'DOTTORE': dottore_int,
            'SPECIAL': 'APP_SERVIZIO',
        }
        return mapped

    # Appuntamento standard (paziente presente)
    summary = f"{paziente}" if paziente else descrizione
    mapped = {
        'PAZIENTE': paziente,
        'DATA': data,
        'ORA_INIZIO': t_inizio,
        'ORA_FINE': t_fine,
        'STUDIO': studio_int,
        'DESCRIZIONE': summary,
        'NOTE': note,
        'TIPO': tipo,
        'DOTTORE': dottore_int,
    }
    return mapped


def filter_appointments_for_sync(appointments, sync_map):
    to_create, to_update, to_skip = [], [], []
    for app in appointments:
        app_id = f"{app[COL_DATA]}_{app[COL_ORA_INIZIO]}_{app[COL_STUDIO]}_{app.get(COL_PAZIENTE,'') or app.get(COL_DESCRIZIONE,'')}"
        app_hash = compute_appointment_hash(app)
        logging.debug(f"DEBUG SYNC: app_id={app_id} | app_hash={app_hash}")
        if app_id in sync_map:
            if sync_map[app_id]['hash'] != app_hash:
                to_update.append((app, sync_map[app_id]['event_id']))
            else:
                to_skip.append(app)
        else:
            to_create.append(app)
    return to_create, to_update, to_skip
