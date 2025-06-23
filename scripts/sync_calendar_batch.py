import json
import logging
from datetime import datetime
from core.calendar_sync import GoogleCalendarSync
from core.db_handler import DBHandler
from config import PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF
from core.sync_utils import (
    filter_appointments_for_sync,
    map_appointment,
    compute_appointment_hash,
    load_sync_map,
    save_sync_map
)

def test_sync(preview_only=True):
    db = DBHandler(PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF)
    appointments_df = db.estrai_appuntamenti_mese(month=datetime.now().month, year=datetime.now().year)
    print('Colonne appuntamenti:', appointments_df.columns.tolist())
    appointments = appointments_df.to_dict(orient='records')
    print('Primo appuntamento:', appointments[0] if appointments else 'Nessun appuntamento')
    sync_map = load_sync_map()
    to_create, to_update, to_skip = filter_appointments_for_sync(appointments, sync_map)
    print(f"Da creare: {len(to_create)} | Da aggiornare: {len(to_update)} | Da saltare: {len(to_skip)}")
    if preview_only:
        for app in to_create:
            print(f"CREA: {app}")
        for app, eid in to_update:
            print(f"AGGIORNA: {app} (evento Google: {eid})")
        for app in to_skip:
            print(f"OK (già sincronizzato): {app}")
    return to_create, to_update, to_skip

def sync_production():
    db = DBHandler(PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF)
    appointments_df = db.estrai_appuntamenti_mese(month=datetime.now().month, year=datetime.now().year)
    appointments = appointments_df.to_dict(orient='records')
    sync_map = load_sync_map()
    to_create, to_update, to_skip = filter_appointments_for_sync(appointments, sync_map)
    gcal = GoogleCalendarSync()
    n_inserted, n_updated = 0, 0
    for app in to_create:
        try:
            mapped = map_appointment(app)
            event = gcal.create_event(mapped)
            app_id = f"{app['DATA']}_{app['ORA_INIZIO']}_{app['STUDIO']}_{app.get('PAZIENTE','') or app.get('DESCRIZIONE','')}"
            app_hash = compute_appointment_hash(app)
            sync_map[app_id] = {'event_id': event['id'], 'hash': app_hash}
            n_inserted += 1
        except Exception as e:
            print(f"[SKIP] Appuntamento non valido: {e}")
    # (Opzionale) Aggiorna eventi modificati (se implementato update_event)
    # for app, eid in to_update:
    #     try:
    #         mapped = map_appointment(app)
    #         gcal.update_event(mapped, eid)
    #         app_id = f"{app['DATA']}_{app['ORA_INIZIO']}_{app['STUDIO']}_{app.get('PAZIENTE','') or app.get('DESCRIZIONE','')}"
    #         app_hash = compute_appointment_hash(app)
    #         sync_map[app_id] = {'event_id': eid, 'hash': app_hash}
    #         n_updated += 1
    #     except Exception as e:
    #         print(f"[SKIP] Appuntamento non aggiornato: {e}")
    save_sync_map(sync_map)
    if n_inserted == 0 and n_updated == 0:
        print("Nessun evento da inserire o aggiornare: tutto già sincronizzato.")
    else:
        print(f"Sincronizzazione completata. Inseriti: {n_inserted}, Aggiornati: {n_updated}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sincronizzazione batch Google Calendar - TEST/PRODUZIONE")
    parser.add_argument('--test', action='store_true', help='Esegui solo il test (dry-run)')
    parser.add_argument('--sync', action='store_true', help='Esegui la sincronizzazione reale')
    args = parser.parse_args()
    if args.sync:
        sync_production()
    else:
        test_sync(preview_only=args.test)
