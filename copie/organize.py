import os
import shutil

# Percorso radice (cartella in cui lanci lo script)
root = os.getcwd()

# Mappa cartelle di destinazione e relativi pattern o nomi file
folders = {
    "config": ["config.py", ".env", "env.example", ".gitignore", "credentials.json"],
    "core": [
        "db_handler.py", "db_handler-new.py",
        "sync_utils.py", "twilio_client.py", "twilio_client-new.py",
        "utils.py", "utils-new.py",
        "calendar.py", "calendar_sync.py", "calendar_sync-new.py",
        "recall_manager.py", "recall_manager-new.py",
        "leggi_appuntamenti.py"
    ],
    "scripts": [
        "automation.py", "automation-new.py",
        "appointment_manager.py", "appointment_manager-new.py",
        "main.py",
        "script.py",
        "sync_calendar_batch.py",
        "test_tools.py"  # se vuoi lasciare qui, altrimenti sposta in tests
    ],
    "gui": ["gui.py", "gui_app.py"],
    "tests": ["test_tools.py"],
    "logs": [".log"],
    "data": ["json", "token.json", "synced_events.json", "debug_appointment.json"]
}

# Funzione di supporto per spostare i file
def move_file(filename, dest_folder):
    src = os.path.join(root, filename)
    dest = os.path.join(root, dest_folder, filename)
    if not os.path.exists(os.path.join(root, dest_folder)):
        os.makedirs(os.path.join(root, dest_folder))
    if os.path.exists(src):
        print(f"Movendo {filename} in {dest_folder}/")
        shutil.move(src, dest)

# Primo, sposta file con nomi esatti
for folder, files in folders.items():
    if folder in ["logs", "data"]:
        continue  # gestiti dopo
    for f in files:
        move_file(f, folder)

# Sposta file .log in logs/
for f in os.listdir(root):
    if f.endswith(".log"):
        move_file(f, "logs")

# Sposta file json e token in data/
for f in os.listdir(root):
    if f.endswith(".json") and f not in folders["config"]:
        move_file(f, "data")

# Attenzione: rimangono in root i file non esplicitamente elencati

print("Spostamento completato.")
