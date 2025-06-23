import os
import re

root_dir = os.getcwd()  # lancia dentro automazioni/

module_paths = {
    "db_handler": "core",
    "sync_utils": "core",
    "twilio_client": "core",
    "utils": "core",
    "calendar": "core",
    "calendar_sync": "core",
    "recall_manager": "core",
    "leggi_appuntamenti": "core",
    "automation": "scripts",
    "appointment_manager": "scripts",
    "main": "scripts",
    "script": "scripts",
    "gui": "gui",
    "gui_app": "gui",
}

# regex per trovare import, gestisce "from X import Y" e "import X"
import_re = re.compile(r'^(from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)')

def update_imports_in_file(filepath):
    changed = False
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        m = import_re.match(line.strip())
        if m:
            kind, mod = m.groups()
            if mod in module_paths:
                new_mod = f"{module_paths[mod]}.{mod}"
                if kind == "from":
                    # sostituisco from X import Y -> from core.X import Y
                    line = line.replace(f"from {mod} ", f"from {new_mod} ")
                else:
                    # sostituisco import X -> import core.X
                    line = line.replace(f"import {mod}", f"import {new_mod}")
                changed = True
        new_lines.append(line)

    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Aggiornati import in {filepath}")

def main():
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(subdir, file)
                update_imports_in_file(path)

if __name__ == "__main__":
    main()
