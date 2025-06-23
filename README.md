# 🦷 Automazione Studio Dentistico - Promemoria, Richiami e Google Calendar

Sistema di automazione sviluppato in Python per la gestione:
- dei **promemoria WhatsApp degli appuntamenti**
- dei **richiami periodici dei pazienti**
- della **sincronizzazione automatica con Google Calendar**

Struttura delle cartelle
automazioni/
├── config/
│   ├── config.py
│   ├── credentials.json
│   ├── .env
│   └── env.example
├── core/
│   ├── db_handler.py
│   ├── sync_utils.py
│   ├── twilio_client.py
│   └── ...
├── scripts/
│   ├── automation.py
│   ├── recall_manager.py
│   ├── calendar_sync.py
│   └── ...
├── gui/
│   ├── gui_app.py
│   └── gui.py
├── tests/
│   └── test_tools.py
├── data/
│   ├── synced_events.json
│   ├── token.json
│   └── ...
├── logs/
│   └── promemoria_appuntamenti_gui.log
├── README.md
├── requirements.txt
└── .gitignore


## 👨‍⚕️ Autore

Studio Dr. Nicola Di Martino  
🦷 [www.studiodimartino.eu](https://www.studiodimartino.eu)
