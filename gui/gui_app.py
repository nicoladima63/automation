import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime, timedelta
from io import StringIO
from textwrap import dedent
from contextlib import redirect_stdout
import logging
import sys, os,json
from threading import Thread
# Aggiungi la root del progetto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.sync_utils import load_sync_map, save_sync_map, map_appointment, filter_appointments_for_sync, compute_appointment_hash

# Assicurati che le variabili d'ambiente siano caricate per config.py
from dotenv import load_dotenv
load_dotenv()

# Importa le classi principali dal tuo progetto diviso
from scripts.appointment_manager import AppointmentManager
from config.constants import TIPO_RICHIAMI, PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, Environment, CURRENT_ENV
from core.calendar_sync import GoogleCalendarSync

# --- Configurazione Logging per la GUI ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

for handler in logger.handlers[:]:
    if not isinstance(handler, logging.FileHandler):
        logger.removeHandler(handler)

file_handler = logging.FileHandler('promemoria_appuntamenti_gui.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class TextRedirector(object):
    """
    Classe per reindirizzare l'output del logger a un widget Text/ScrolledText di Tkinter.
    """
    def __init__(self, widget, tag_map=None):
        self.widget = widget
        self.tag_map = tag_map if tag_map is not None else {}

    def write(self, str_):
        self.widget.configure(state='normal')
        tag = "INFO"
        if "ERROR" in str_:
            tag = "ERROR"
        elif "WARNING" in str_:
            tag = "WARNING"
        elif "CRITICAL" in str_:
            tag = "CRITICAL"

        self.widget.insert(tk.END, str_, (tag,))
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')

    def flush(self):
        pass

class GuiApp(tk.Tk):
    """
    Applicazione GUI per gestire e testare i promemoria appuntamenti.
    """
    def __init__(self):
        super().__init__()
        self.title("Gestore Studio Dentistico")
        self.geometry("1480x800")  # Aumentato per le nuove funzionalità

        # Inizializza le variabili PRIMA di create_widgets
        self.env_var = tk.StringVar(value=CURRENT_ENV.value)
        self.test_mode_var = tk.BooleanVar(value=False)
        self.simulate_send_var = tk.BooleanVar(value=False)
        self.test_number_var = tk.StringVar(value="")
        self.test_date_var = tk.StringVar(value="")
        self.solo_primo_var = tk.BooleanVar(value=False)
        
        # Nuove variabili per i richiami
        self.recall_test_mode_var = tk.BooleanVar(value=False)
        self.recall_simulate_var = tk.BooleanVar(value=False)
        self.recall_days_var = tk.StringVar(value="7")  # Default 7 giorni
        self.month_var = tk.StringVar(value="Tutti")
        self.tipo_richiamo_var = tk.StringVar(value="Tutti")

        # Crea i widget dopo l'inizializzazione delle variabili
        self.create_widgets()
        self.manager = None
        self.calendar_sync = None

        self.log_handler = logging.StreamHandler(TextRedirector(self.log_area))
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_handler)

        logging.info("Applicazione GUI avviata.")
        self.check_env_vars()

    def create_widgets(self):
        # Frame per l'ambiente (comune)
        self.create_environment_frame()

        # Notebook per le tab
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both', padx=10, pady=5)

        # Tab Promemoria Appuntamenti
        appointments_frame = ttk.Frame(notebook)
        notebook.add(appointments_frame, text='Promemoria Appuntamenti')
        self.create_appointments_widgets(appointments_frame)

        # Tab Richiami
        recalls_frame = ttk.Frame(notebook)
        notebook.add(recalls_frame, text='Gestione Richiami')
        self.create_recalls_widgets(recalls_frame)

        # Tab Google Calendar
        calendar_frame = ttk.Frame(notebook)
        notebook.add(calendar_frame, text='Google Calendar')
        self.create_calendar_widgets(calendar_frame)

        # Area log comune
        self.create_log_area()

    def create_calendar_widgets(self, parent):
        """Crea i widget per la gestione di Google Calendar"""
        # Frame controlli con solo il pulsante di sincronizzazione
        control_frame = ttk.LabelFrame(parent, text="Controlli Calendar", padding="10")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            control_frame,
            text="Sincronizza Giugno 2025",
            command=lambda: self.sync_month(6, 2025)
        ).pack(side=tk.LEFT, padx=5)

        # Frame per i risultati
        results_frame = ttk.Frame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Area risultati 
        self.calendar_result = scrolledtext.ScrolledText(results_frame, height=15)
        self.calendar_result.pack(fill=tk.BOTH, expand=True, pady=5)

        # Frame per selezione calendario (manteniamo questa sezione)
        calendar_select_frame = ttk.LabelFrame(parent, text="Selezione Calendario")
        calendar_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(calendar_select_frame, text="Calendario:").pack(side=tk.LEFT, padx=5)
        
        # Combobox per i calendari
        self.calendar_var = tk.StringVar()
        self.calendar_combo = ttk.Combobox(
            calendar_select_frame, 
            textvariable=self.calendar_var,
            state="readonly",
            width=30
        )
        self.calendar_combo.pack(side=tk.LEFT, padx=5)
        
        # Bottoni
        ttk.Button(
            calendar_select_frame,
            text="Aggiorna Lista",
            command=self.update_calendar_list
        ).pack(side=tk.LEFT, padx=5)
        
        self.btn_clear = ttk.Button(
            calendar_select_frame,
            text="Azzera Calendario",
            command=self.clear_selected_calendar,
            state='disabled'
        )
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # Combo per selezione mese
        self.export_month_var = tk.StringVar(value="6")
        mesi = [str(m) for m in range(1, 13)]
        ttk.Label(calendar_select_frame, text="Mese:").pack(side=tk.LEFT, padx=5)
        self.export_month_combo = ttk.Combobox(
            calendar_select_frame,
            textvariable=self.export_month_var,
            values=mesi,
            state="readonly",
            width=5
        )
        self.export_month_combo.pack(side=tk.LEFT, padx=5)
        # Pulsante esporta eventi mese in JSON
        ttk.Button(
            calendar_select_frame,
            text="Esporta eventi mese in JSON",
            command=self.export_month_events_to_json
        ).pack(side=tk.LEFT, padx=5)

        # Pulsante per sincronizzazione diretta mese/calendario
        ttk.Button(
            parent,
            text="Sincronizza mese su calendario selezionato",
            command=self.sync_selected_month_calendar
        ).pack(pady=5)

        # Progress bar
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(parent, textvariable=self.progress_var)
        self.progress_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(parent, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        self.progress.pack_forget()

        # --- AGGIUNTA DEL PULSANTE DI DEBUG ---
        ttk.Button(
            control_frame,
            text="Debug Appuntamenti",
            command=lambda: self.debug_appointments_gui()
        ).pack(side=tk.LEFT, padx=5)
        # ----------------------------------------

        # --- AGGIUNTA DEL PULSANTE DI TEST EVENTO SINGOLO ---
        ttk.Button(
            control_frame,
            text="Test Evento Singolo",
            command=lambda: self.test_single_event_gui()
        ).pack(side=tk.LEFT, padx=5)
        # ----------------------------------------

        # --- AGGIUNTA DEL PULSANTE PER INVIARE TUTTI DA DEBUG JSON ---
        ttk.Button(
            control_frame,
            text="Invia Tutti da Debug JSON",
            command=lambda: self.test_send_debug_json_events()
        ).pack(side=tk.LEFT, padx=5)
        # ----------------------------------------

    # --- FUNZIONI DI TEST E DEBUG SPOSTATE DA gui_app.py ---
    # Puoi importare queste funzioni in test_tools.py per eseguire test manuali sulla GUI o logica collegata.
    #
    # - test_calendar_auth(self)
    # - test_appointments_read(self)
    # - test_recalls(self)
    # - debug_appointments_gui(self)
    # - test_single_event_gui(self)
    # - test_send_debug_json_events(self)
    #

    def sync_calendar(self):
        """Gestisce la sincronizzazione con Google Calendar"""
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
                
            self.calendar_sync.authenticate()
            
            # Crea un'istanza di AppointmentManager per accedere al db_handler
            if not self.manager:
                self.manager = AppointmentManager()
                
            # Ottieni gli appuntamenti
            appointments = self.manager.db_handler.get_appointments()
            
            for appointment in appointments:
                self.calendar_sync.create_event(appointment)
                
            messagebox.showinfo(
                "Successo", 
                "Sincronizzazione completata!"
            )
            
        except Exception as e:
            logging.error(f"Errore sincronizzazione: {str(e)}")
            messagebox.showerror(
                "Errore", 
                f"Errore durante la sincronizzazione: {str(e)}"
            )

    def update_calendar_list(self):
        """Aggiorna la lista dei calendari disponibili"""
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
                
            if not self.calendar_sync.calendar_service:
                self.calendar_sync.authenticate()
        
            calendars = self.calendar_sync.get_calendars()
            
            # Dizionari per mappatura
            self.calendar_ids = {}
            self.studio_calendar_ids = {}
            
            calendar_options = ['Tutti']
            
            for calendar in calendars:
                name = calendar['summary']
                cal_id = calendar['id']
                
                if "Studio blu" in name:
                    self.studio_calendar_ids[1] = cal_id
                    calendar_options.append(name)
                elif "Studio giallo" in name:
                    self.studio_calendar_ids[2] = cal_id
                    calendar_options.append(name)
            
                self.calendar_ids[name] = cal_id
        
            # Aggiorna la combo e seleziona 'Tutti'
            self.calendar_combo['values'] = calendar_options
            self.calendar_combo.set('Tutti')
            
            # Abilita il pulsante di cancellazione
            self.btn_clear['state'] = 'normal'
            
            logging.info(f"Trovati calendari: {calendar_options}")
            self.calendar_result.insert(tk.END, "\nLista calendari aggiornata\n")
            
        except Exception as e:
            error_msg = f"Errore recupero calendari: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("Errore", error_msg)
            self.btn_clear['state'] = 'disabled'  # Disabilita in caso di errore

    def sync_month(self, month, year):
        """Sincronizza gli appuntamenti di un mese specifico"""
        try:
            # Disabilita controlli
            self.calendar_combo['state'] = 'disabled'
            self.btn_clear['state'] = 'disabled'
            
            # Mostra e avvia progress bar
            self.progress.pack()
            self.progress.start(10)  # Velocità più alta per animazione più visibile
            self.progress_var.set("Inizializzazione sincronizzazione...")
            self.update_idletasks()  # Forza l'aggiornamento immediato della GUI
            
            # Determina quali calendari sincronizzare
            selected = self.calendar_var.get()
            calendars_to_sync = {}
            
            if selected == 'Tutti':
                calendars_to_sync = self.studio_calendar_ids
            else:
                for studio, cal_id in self.studio_calendar_ids.items():
                    if cal_id == self.calendar_ids.get(selected):
                        calendars_to_sync[studio] = cal_id
                        break
            
            # Avvia thread di sincronizzazione
            Thread(target=self._do_sync, args=(month, year, calendars_to_sync)).start()
            
        except Exception as e:
            self.handle_sync_error(e)

    def _do_sync(self, month, year, calendars_to_sync):
        """Esegue la sincronizzazione vera e propria: ora esporta solo il JSON come la funzione di debug."""
        try:
            total_appointments = 0
            all_events = []
            for studio, cal_id in calendars_to_sync.items():
                try:
                    logging.info(f"Preparazione appuntamenti per {studio}...")
                    if not self.manager:
                        self.manager = AppointmentManager()
                    appointments = self.manager.db_handler.get_appointments(month=month, year=year)
                    total_appointments += len(appointments)
                    for app in appointments:
                        try:
                            data_evento = app['DATA']
                            if isinstance(data_evento, str):
                                data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
                            ora_inizio = app['ORA_INIZIO']
                            ora_fine = app['ORA_FINE']
                            if not isinstance(ora_inizio, (int, float)) or not isinstance(ora_fine, (int, float)):
                                continue
                            color_id = str(self.calendar_sync._get_google_color_id(app['TIPO'] if app['TIPO'] else '1'))
                            summary = app.get('PAZIENTE', '').strip()
                            if not summary:
                                summary = f"Nota/Evento senza paziente (ID: {app.get('ID', '-')})"
                            event = {
                                'summary': summary,
                                'description': app.get('NOTE', ''),
                                'start': {
                                    'dateTime': datetime.combine(
                                        data_evento, 
                                        self.calendar_sync._decimal_to_time(ora_inizio)
                                    ).isoformat(),
                                    'timeZone': 'Europe/Rome',
                                },
                                'end': {
                                    'dateTime': datetime.combine(
                                        data_evento, 
                                        self.calendar_sync._decimal_to_time(ora_fine)
                                    ).isoformat(),
                                    'timeZone': 'Europe/Rome',
                                },
                                'colorId': color_id
                            }
                            all_events.append(event)
                        except Exception as e:
                            logging.warning(f"Evento saltato per errore: {e}")
                except Exception as e:
                    logging.error(f"Errore durante la preparazione per {studio}: {str(e)}")
            # Esporta tutti gli eventi in debug_appointment.json
            with open('debug_appointment.json', 'w', encoding='utf-8') as f:
                json.dump(all_events, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(
                "Esportazione Completata",
                f"Appuntamenti esportati: {len(all_events)}\nTotale appuntamenti mese: {total_appointments}\nOra puoi inviare con la funzione 'Invia Tutti da Debug JSON'"
            )
        except Exception as e:
            self.handle_sync_error(e)
        finally:
            self.calendar_combo['state'] = 'readonly'
            self.btn_clear['state'] = 'normal'
            self.progress.stop()
            self.progress.pack_forget()
            self.progress_var.set("")

    def handle_sync_error(self, error):
        """Gestisce gli errori di sincronizzazione"""
        logging.error(f"Errore durante la sincronizzazione: {str(error)}")
        messagebox.showerror("Errore Sincronizzazione", f"Si è verificato un errore durante la sincronizzazione: {str(error)}")

    def create_environment_frame(self):
        """Crea il frame dell'ambiente comune a tutte le tab"""
        env_frame = ttk.LabelFrame(self, text="Ambiente", padding="10")
        env_frame.pack(fill=tk.X, padx=10, pady=5)

        # Radio buttons per la selezione dell'ambiente
        ttk.Radiobutton(env_frame, 
                       text="Development", 
                       variable=self.env_var, 
                       value="development",
                       command=self.change_environment).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(env_frame, 
                       text="Production", 
                       value="production",
                       variable=self.env_var,
                       command=self.change_environment).pack(side=tk.LEFT, padx=10)

        # Label per mostrare l'ambiente corrente
        self.env_label = ttk.Label(env_frame, 
                                 text=f"Ambiente attuale: {self.env_var.get()}")
        self.env_label.pack(side=tk.RIGHT, padx=10)

    def create_appointments_widgets(self, parent):
        # Sezione Controlli Promemoria
        control_frame = ttk.LabelFrame(parent, text="Controlli Promemoria", padding="10")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Checkbutton(control_frame, text="Modalità Test (non invia messaggi reali)",
                        variable=self.test_mode_var, command=self._update_test_controls).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        ttk.Checkbutton(control_frame, text="Simula Invio Messaggi (non chiama Twilio)",
                        variable=self.simulate_send_var, command=self._update_test_controls).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(control_frame, text="Numero Test (+39...):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.test_number_entry = ttk.Entry(control_frame, textvariable=self.test_number_var, width=30)
        self.test_number_entry.grid(row=row, column=1, sticky=tk.EW, pady=2)
        row += 1

        ttk.Label(control_frame, text="Data Test (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.test_date_entry = ttk.Entry(control_frame, textvariable=self.test_date_var, width=30)
        self.test_date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2)
        row += 1

        ttk.Checkbutton(control_frame, text="Solo Primo Appuntamento",
                        variable=self.solo_primo_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # Bottoni delle azioni
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Test DB Connection", command=self.run_test_db).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Test Twilio Config", command=self.run_test_twilio).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Esegui Promemoria Ora", command=self.run_daily_reminders).pack(side=tk.LEFT, padx=5)
        # --- AGGIUNTA DEL NUOVO PULSANTE CLEAR ---
        ttk.Button(button_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        # ----------------------------------------

        self._update_test_controls()

    def create_recalls_widgets(self, parent):
        """Crea i widget per la gestione dei richiami"""
        recalls_control = ttk.LabelFrame(parent, text="Controlli Richiami", padding="10")
        recalls_control.pack(fill=tk.X, padx=10, pady=5)

        # Frame per i filtri
        filter_frame = ttk.LabelFrame(recalls_control, text="Filtri", padding="5")
        filter_frame.pack(fill=tk.X, pady=5)

        # Combobox per la selezione del mese
        mesi = ["Tutti"] + [
            "Gennaio", "Febbraio", "Marzo", "Aprile", 
            "Maggio", "Giugno", "Luglio", "Agosto",
            "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        ttk.Label(filter_frame, text="Mese:").pack(side=tk.LEFT, padx=5)
        month_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.month_var,
            values=mesi,
            state="readonly",
            width=10
        )
        month_combo.pack(side=tk.LEFT, padx=5)

        # Combobox per il tipo di richiamo
        tipi_richiamo = ["Tutti", "Generico", "Igiene", "Rx Impianto", 
                         "Controllo", "Impianto", "Ortodonzia"]
        ttk.Label(filter_frame, text="Tipo:").pack(side=tk.LEFT, padx=5)
        type_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.tipo_richiamo_var,
            values=tipi_richiamo,
            state="readonly",
            width=15
        )
        type_combo.pack(side=tk.LEFT, padx=5)

        # Frame per i pulsanti
        button_frame = ttk.Frame(recalls_control)
        button_frame.pack(fill=tk.X, pady=5)

        # Pulsanti per le azioni
        ttk.Button(
            button_frame,
            text="Test Richiami",
            command=self.test_recalls
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Reset Filtri",
            command=self.reset_recall_filters
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Pulisci Log",
            command=self.clear_recall_log
        ).pack(side=tk.LEFT, padx=5)

        # Area risultati
        self.recall_test_result = scrolledtext.ScrolledText(recalls_control, height=15)
        self.recall_test_result.pack(fill=tk.BOTH, expand=True, pady=5)

    def execute_recalls(self):
        try:
            days = int(self.recall_days_var.get())
            is_test = self.recall_test_mode_var.get()
            simulate = self.recall_simulate_var.get()
            
            if not self.manager:
                self.manager = AppointmentManager()
            
            # Implementa la logica dei richiami qui
            logging.info(f"Esecuzione richiami con {days} giorni di anticipo")
            logging.info(f"Test: {is_test}, Simulazione: {simulate}")
            
            # TODO: Implementare la logica dei richiami
            
        except ValueError:
            messagebox.showerror("Errore", "Il numero di giorni deve essere un numero intero")
            return

    def reset_recall_filters(self):
        """Resetta tutti i filtri dei richiami"""
        self.month_var.set("Tutti")
        self.tipo_richiamo_var.set("Tutti")
        self.test_recalls()

    def clear_recall_log(self):
        """Pulisce l'area dei risultati dei richiami"""
        self.recall_test_result.delete(1.0, tk.END)

    def test_recalls(self):
        """Esegue il test dei richiami e mostra i risultati"""
        try:
            days = int(self.recall_days_var.get())
            selected_month = None
            selected_type = None
            
            # Gestione mese selezionato
            month_str = self.month_var.get()
            if month_str != "Tutti":
                mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", 
                       "Maggio", "Giugno", "Luglio", "Agosto",
                       "Settembre", "Ottobre", "Novembre", "Dicembre"]
                selected_month = mesi.index(month_str) + 1

            # Gestione tipo selezionato
            tipo_str = self.tipo_richiamo_var.get()
            if tipo_str != "Tutti":
                # Inverti il dizionario TIPO_RICHIAMI per trovare il codice
                tipo_to_code = {v: k for k, v in TIPO_RICHIAMI.items()}
                selected_type = tipo_to_code.get(tipo_str)
                logging.debug(f"Tipo selezionato: {tipo_str}, codice: {selected_type}")
        
            if not self.manager:
                self.manager = AppointmentManager()
            
            results = self.manager.recall_manager.test_due_recalls(
                days, 
                selected_month=selected_month,
                selected_type=selected_type
            )
            
            # Visualizzazione risultati
            self.recall_test_result.delete(1.0, tk.END)
            header = f"Trovati {results['total']} richiami in scadenza"
            filters = []
            if month_str != "Tutti":
                filters.append(f"mese: {month_str}")
            if tipo_str != "Tutti":
                filters.append(f"tipo: {tipo_str}")
            if filters:
                header += f" ({', '.join(filters)})"
            
            self.recall_test_result.insert(tk.END, header + "\n\n")
            
            # Mostra statistiche per tipo
            self.recall_test_result.insert(tk.END, "=== Statistiche per Tipo ===\n")
            for tipo, count in results['type_counts'].items():
                if count > 0:
                    self.recall_test_result.insert(tk.END, f"{tipo}: {count}\n")
            
            # Mostra dettagli richiami
            self.recall_test_result.insert(tk.END, "\n=== Dettagli Richiami ===\n")
            for recall in results['recalls']:
                self.recall_test_result.insert(tk.END, 
                    f"\nPaziente: {recall['nome']}\n"
                    f"Tipo: {recall['tipo_richiamo']}\n"
                    f"Telefono: {recall['telefono']}\n"
                    f"Ultima visita: {recall['ultima_visita']}\n"
                    f"Data richiamo 1: {recall['data_richiamo1']}\n"
                    f"Data richiamo 2: {recall['data_richiamo2']}\n"
                    f"------------------------\n"
                )
                
        except Exception as e:
            logging.error(f"Errore durante il test dei richiami: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'elaborazione: {str(e)}")
            return

    def create_log_area(self):
        """Crea l'area log comune"""
        log_frame = ttk.LabelFrame(self, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log_area.tag_config("INFO", foreground="black")
        self.log_area.tag_config("WARNING", foreground="orange")
        self.log_area.tag_config("ERROR", foreground="red")
        self.log_area.tag_config("CRITICAL", foreground="darkred", font=('TkDefaultFont', 10, 'bold'))

    def _update_test_controls(self):
        is_test_mode = self.test_mode_var.get()
        is_simulate_send = self.simulate_send_var.get()

        if is_test_mode or is_simulate_send:
            self.test_number_entry.config(state='normal')
        else:
            self.test_number_entry.config(state='disabled')

    def _get_manager_instance(self):
        return AppointmentManager(
            modalita_test=self.test_mode_var.get(),
            test_numero=self.test_number_var.get() if self.test_number_var.get() else None,
            simula_invio=self.simulate_send_var.get()
        )

    def update_env_file(self, new_env):
        """Aggiorna il file .env con il nuovo ambiente"""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            
            # Verifica che il file esista
            if not os.path.exists(env_path):
                env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
                if not os.path.exists(env_path):
                    raise FileNotFoundError("File .env non trovato")

            # Prima di modificare, verifica se il valore è già quello desiderato
            current_env = None
            with open(env_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip().startswith('APP_ENV='):
                        current_env = line.strip().split('=')[1]
                        break
            
            if current_env == new_env:
                logging.info(f"L'ambiente è già impostato su {new_env}")
                return False

            # Leggi tutto il file
            with open(env_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Modifica il file
            with open(env_path, 'w', encoding='utf-8') as file:
                env_found = False
                for line in lines:
                    if line.strip().startswith('APP_ENV='):
                        file.write(f'APP_ENV={new_env}\n')
                        env_found = True
                    else:
                        file.write(line)
                
                if not env_found:
                    file.write(f'\nAPP_ENV={new_env}\n')

            # Forza il ricaricamento delle variabili d'ambiente
            load_dotenv(env_path, override=True)
            
            logging.info(f"Ambiente aggiornato con successo da {current_env} a {new_env}")
            return True

        except Exception as e:
            logging.error(f"Errore nell'aggiornamento del file .env: {str(e)}")
            messagebox.showerror("Errore", f"Impossibile aggiornare il file .env: {str(e)}")
            return False

    def change_environment(self):
        """Gestisce il cambio di ambiente"""
        try:
            new_env = self.env_var.get()
            current_env = os.getenv('APP_ENV')
            
            if new_env == current_env:
                logging.info(f"Ambiente già impostato su {new_env}")
                return
                
            if messagebox.askyesno("Cambio Ambiente", 
                                  f"Sei sicuro di voler passare da {current_env} a {new_env}?\n"
                                  f"L'applicazione verrà riavviata."):
                
                # Aggiorna il file .env
                if self.update_env_file(new_env):
                    self.quit()
                    python = sys.executable
                    os.execl(python, python, *sys.argv)
                else:
                    # Ripristina il valore precedente
                    self.env_var.set(current_env)
            else:
                # Ripristina il valore precedente
                self.env_var.set(current_env)
                
        except Exception as e:
            logging.error(f"Errore nel cambio ambiente: {str(e)}")
            messagebox.showerror("Errore", str(e))
            # Ripristina il valore precedente
            self.env_var.set(current_env)

    def restart_application(self):
        """Riavvia l'applicazione"""
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def check_env_vars(self):
        from config.constants import PATH_APPUNTAMENTI_DBF, PATH_ANAGRAFICA_DBF, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

        missing_vars = []
        if not PATH_APPUNTAMENTI_DBF:
            missing_vars.append("PATH_APPUNTAMENTI_DBF")
        if not PATH_ANAGRAFICA_DBF:
            missing_vars.append("PATH_ANAGRAFICA_DBF")
        if not TWILIO_ACCOUNT_SID:
            missing_vars.append("TWILIO_ACCOUNT_SID")
        if not TWILIO_AUTH_TOKEN:
            missing_vars.append("TWILIO_AUTH_TOKEN")
        if not TWILIO_WHATSAPP_NUMBER:
            missing_vars.append("TWILIO_WHATSAPP_NUMBER")

        if missing_vars:
            messagebox.showwarning(
                "Variabili d'Ambiente Mancanti",
                f"Le seguenti variabili d'ambiente cruciali non sono impostate nel file .env o nel sistema:\n"
                f"{', '.join(missing_vars)}\n"
                f"L'applicazione potrebbe non funzionare correttamente in modalità non di test."
            )
            logging.warning(f"Variabili d'ambiente mancanti: {', '.join(missing_vars)}")
        else:
            logging.info("Tutte le variabili d'ambiente richieste sono caricate.")
        logging.info(f"Ambiente corrente: {CURRENT_ENV.value}")

    def run_test_db(self):
        self.clear_logs() # Pulisci i log prima di un nuovo test
        manager = self._get_manager_instance()
        logging.info("Avvio Test Connessione Database...")
        manager.test_database_connection()
        logging.info("Test Connessione Database Completato.")

    def run_test_twilio(self):
        self.clear_logs() # Pulisci i log prima di un nuovo test
        manager = self._get_manager_instance()
        logging.info("Avvio Test Configurazione Twilio...")
        manager.test_twilio_configuration()
        logging.info("Test Configurazione Twilio Completato.")

    def run_daily_reminders(self):
        self.clear_logs() # Pulisci i log prima di un nuovo run
        manager = self._get_manager_instance()

        test_data = None
        if self.test_date_var.get():
            try:
                test_data = datetime.strptime(self.test_date_var.get(), '%Y-%m-%d').date()
            except ValueError:
                messagebox.showerror("Errore Data", "Formato data non valido. Usa YYYY-MM-DD.")
                logging.error(f"Formato data non valido: {self.test_date_var.get()}. Usa YYYY-MM-DD.")
                return

        logging.info("Avvio Elaborazione Promemoria Giornalieri...")
        manager.elabora_promemoria_giornalieri(
            data_test=test_data,
            solo_primo=self.solo_primo_var.get()
        )
        logging.info("Elaborazione Promemoria Giornalieri Completata.")

    def clear_logs(self):
        """Pulisce l'area dei log."""
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END) # Cancella tutto dal carattere 1.0 (inizio) alla fine
        self.log_area.configure(state='disabled')
        logging.info("Log dell'interfaccia puliti.") # Aggiungi un messaggio dopo la pulizia

    def clear_calendar(self):
        """Pulisce tutti gli eventi (passati e futuri) del calendario selezionato"""
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            # Assicurati che il servizio sia autenticato
            if not self.calendar_sync.calendar_service:
                self.calendar_sync.authenticate()
            # Recupera l'ID del calendario selezionato
            calendar_name = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(calendar_name, 'primary')
            if messagebox.askyesno("Conferma Pulizia Calendario", 
                                 "Sei sicuro di voler BRASARE tutti gli eventi (passati e futuri) dal calendario selezionato?"):
                # Disabilita i pulsanti durante l'operazione
                self.disable_calendar_controls()
                # Mostra loader/progress bar e messaggio
                self.progress.pack()
                self.progress.start(10)
                self.progress_var.set("Azzeramento calendario in corso...")
                self.update_idletasks()
                # Esegui la pulizia in un thread separato
                Thread(target=self._clear_calendar_events, args=(calendar_id,)).start()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la pulizia del calendario: {str(e)}")
            logging.error(f"Errore durante la pulizia del calendario: {str(e)}")

    def _clear_calendar_events(self, calendar_id):
        """Funzione eseguita nel thread per pulire tutti gli eventi del calendario"""
        try:
            deleted = self.calendar_sync.delete_all_events(calendar_id)
            messagebox.showinfo("Successo", f"Tutti gli eventi sono stati eliminati dal calendario selezionato. ({deleted} eventi)")
            logging.info(f"Pulizia calendario completata. Eliminati {deleted} eventi.")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la pulizia del calendario: {str(e)}")
            logging.error(f"Errore durante la pulizia del calendario: {str(e)}")
        finally:
            # Riabilita i controlli del calendario
            self.enable_calendar_controls()
            # Nascondi loader/progress bar
            self.progress.stop()
            self.progress.pack_forget()
            self.progress_var.set("")

    def clear_calendars(self):
        """Azzera completamente tutti i calendari degli studi (passato e futuro) in un thread separato."""
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            if not hasattr(self, 'studio_calendar_ids'):
                messagebox.showerror("Errore", "Prima aggiorna la lista dei calendari")
                return
            if not messagebox.askyesno("Conferma", "Questa operazione cancellerà TUTTI gli eventi (passati e futuri) dai calendari degli studi. Vuoi continuare?"):
                return
            self.progress.pack()
            self.progress.start()
            self.progress_var.set("Pulizia calendari in corso...")
            Thread(target=self._threaded_clear_calendars).start()
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _threaded_clear_calendars(self):
        """Funzione eseguita nel thread per pulire tutti i calendari degli studi."""
        total_deleted = 0
        try:
            for studio, cal_id in self.studio_calendar_ids.items():
                try:
                    deleted = self.calendar_sync.delete_all_events(cal_id)
                    total_deleted += deleted
                    self.calendar_result.insert(tk.END, f"Eliminati {deleted} eventi dal calendario Studio {studio}\n")
                except Exception as e:
                    self.calendar_result.insert(tk.END, f"Errore pulizia Studio {studio}: {str(e)}\n")
            self.after(0, lambda: messagebox.showinfo("Completato", f"Eliminati {total_deleted} eventi dai calendari"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Errore", str(e)))
        finally:
            self.after(0, self.progress.stop)
            self.after(0, self.progress.pack_forget)
            self.after(0, lambda: self.progress_var.set(""))

    def clear_selected_calendar(self):
        """Azzera completamente il calendario selezionato (passato e futuro)"""
        try:
            if not self.calendar_var.get():
                messagebox.showwarning("Attenzione", "Seleziona un calendario")
                return
                
            calendar_name = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(calendar_name)
            
            if not calendar_id:
                messagebox.showerror("Errore", "ID calendario non trovato")
                return
                
            if not messagebox.askyesno("Conferma", 
                f"Questa operazione cancellerà TUTTI gli eventi (passati e futuri) dal calendario:\n{calendar_name}\nVuoi continuare?"):
                return

            self.progress.pack()
            self.progress.start()
            self.progress_var.set("Eliminazione eventi in corso...")
            
            def update_progress(current, total):
                self.progress_var.set(f"Eliminazione eventi in corso... {current}/{total}")
                
            deleted = self.calendar_sync.delete_all_events(calendar_id, progress_callback=update_progress)
            
            self.calendar_result.insert(tk.END, 
                f"\nEliminati {deleted} eventi dal calendario {calendar_name}\n")
            
            messagebox.showinfo("Completato", f"Eliminati {deleted} eventi dal calendario")

        except Exception as e:
            error_msg = f"Errore pulizia calendario: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("Errore", error_msg)
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.progress_var.set("")

    def debug_appointments_gui(self):
        """Esporta i primi 50 appuntamenti del mese selezionato in debug_appointment.json e mostra risultato."""
        try:
            # Determina mese e anno selezionati (qui esempio: giugno 2025, puoi collegare a selezione GUI se presente)
            month = 6
            year = 2025
            selected = self.calendar_var.get()
            calendars_to_sync = {}
            if selected == 'Tutti':
                calendars_to_sync = self.studio_calendar_ids
            else:
                for studio, cal_id in self.studio_calendar_ids.items():
                    if cal_id == self.calendar_ids.get(selected):
                        calendars_to_sync[studio] = cal_id
                        break
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            self.calendar_sync.authenticate()
            result = self.calendar_sync.sync_appointments_for_month(
                month=month,
                year=year,
                studio_calendar_ids=calendars_to_sync,
                debug_export_first_50=True
            )
            messagebox.showinfo("Debug Appuntamenti", f"Esportati {result['debug_exported']} appuntamenti in debug_appointment.json.\nTotale appuntamenti mese: {result['total']}")
        except Exception as e:
            logging.error(f"Errore debug appuntamenti: {e}")
            messagebox.showerror("Errore Debug", str(e))

    def test_single_event_gui(self):
        """Invia un evento di test al calendario selezionato nella combo."""
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            self.calendar_sync.authenticate()
            selected = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(selected, 'primary')
            # Evento di test minimale
            event = {
                'summary': 'Narisi Annarita',
                'description': 'Evento di test creato dalla GUI',
                'start': {
                    'dateTime': "2025-06-18T15:00:00",
                    'timeZone': 'Europe/Rome',
                },
                'end': {
                    'dateTime': "2025-06-18T16:00:00",
                    'timeZone': 'Europe/Rome',
                },
                'colorId': '11'
            }
            try:
                result = self.calendar_sync.calendar_service.events().insert(
                    calendarId=calendar_id,
                    body=event
                ).execute()
                messagebox.showinfo("Test Evento Singolo", f"Evento creato con successo!\nID: {result.get('id')}\nLink: {result.get('htmlLink')}")
                logging.info(f"Evento di test creato su {calendar_id}: {result.get('id')}")
            except Exception as e:
                logging.error(f"Errore creazione evento di test su {calendar_id}: {e}")
                messagebox.showerror("Errore Test Evento", str(e))
        except Exception as e:
            logging.error(f"Errore generale test evento singolo: {e}")
            messagebox.showerror("Errore Test Evento", str(e))

    def test_send_debug_json_events(self):
        """Avvia l'invio degli eventi debug in un thread separato per non bloccare la GUI."""
        Thread(target=self._threaded_send_debug_json_events).start()

    def _threaded_send_debug_json_events(self):
        """Invia tutti gli eventi presenti in debug_appointment.json al calendario selezionato, loggando esito per ciascuno. Si ferma al primo errore non rate limit."""
        import time
        from googleapiclient.errors import HttpError
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            self.calendar_sync.authenticate()
            selected = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(selected, 'primary')
            with open('debug_appointment.json', 'r', encoding='utf-8') as f:
                events = json.load(f)
            for event in events:
                summary = event.get('summary', 'N/D')
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        result = self.calendar_sync.calendar_service.events().insert(
                            calendarId=calendar_id,
                            body=event
                        ).execute()
                        logging.info(f"Invio: {summary} - OK (ID: {result.get('id')})")
                        break
                    except HttpError as e:
                        error_content = getattr(e, 'content', str(e))
                        if e.resp.status == 403 and 'rateLimitExceeded' in str(e):
                            retry_count += 1
                            wait_time = min(2 ** retry_count, 10)
                            logging.warning(f"Rate limit per {summary}, retry {retry_count} tra {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logging.error(f"Invio: {summary} - ERRORE: {e}\nDettaglio: {error_content}")
                            self._show_error_async(f"Errore su: {summary}\n{e}\nDettaglio: {error_content}")
                            return
                else:
                    logging.error(f"Invio: {summary} - ERRORE: superato numero massimo di retry per rate limit")
                    self._show_error_async(f"Rate limit su: {summary} - superato numero massimo di retry")
                    return
            else:
                self._show_info_async("Test completato. Controlla il log per i risultati dettagliate.")
        except Exception as e:
            logging.error(f"Errore generale test invio debug json: {e}")
            self._show_error_async(str(e))

    def _show_error_async(self, msg):
        self.after(0, lambda: messagebox.showerror("Errore Invio Evento", msg))

    def _show_info_async(self, msg):
        self.after(0, lambda: messagebox.showinfo("Test Invio Debug JSON", msg))

    def export_month_events_to_json(self):
        """Estrae tutti gli eventi del mese selezionato e li esporta in un file JSON, loggando quelli problematici."""
        try:
            if not self.manager:
                self.manager = AppointmentManager()
            month = int(self.export_month_var.get())
            year = datetime.now().year
            selected = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(selected)
            if not calendar_id:
                messagebox.showerror("Errore", "Seleziona un calendario valido")
                return
            appointments = self.manager.db_handler.get_appointments(month=month, year=year)
            events = []
            problematic = []
            for app in appointments:
                try:
                    data_evento = app['DATA']
                    if isinstance(data_evento, str):
                        data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
                    ora_inizio = app['ORA_INIZIO']
                    ora_fine = app['ORA_FINE']
                    if not isinstance(ora_inizio, (int, float)) or not isinstance(ora_fine, (int, float)):
                        raise ValueError("Orario non valido")
                    color_id = str(self.calendar_sync._get_google_color_id(app['TIPO'] if app['TIPO'] else '1'))
                    summary = app.get('PAZIENTE', '').strip()
                    if not summary:
                        # Se manca il paziente, prova a dedurre una descrizione alternativa
                        summary = f"Nota/Evento senza paziente (ID: {app.get('ID', '-')})"
                    event = {
                        'summary': summary,
                        'description': app.get('NOTE', ''),
                        'start': {
                            'dateTime': datetime.combine(
                                data_evento, 
                                self.calendar_sync._decimal_to_time(ora_inizio)
                            ).isoformat(),
                            'timeZone': 'Europe/Rome',
                        },
                        'end': {
                            'dateTime': datetime.combine(
                                data_evento, 
                                self.calendar_sync._decimal_to_time(ora_fine)
                            ).isoformat(),
                            'timeZone': 'Europe/Rome',
                        },
                        'colorId': color_id
                    }
                    events.append(event)
                except Exception as e:
                    problematic.append({'appuntamento': app, 'errore': str(e)})
            # Esporta tutto in JSON
            with open('debug_export_mese.json', 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
            with open('debug_export_mese_problematici.json', 'w', encoding='utf-8') as f:
                json.dump(problematic, f, ensure_ascii=False, indent=2)
            msg = f"Esportati {len(events)} eventi validi in debug_export_mese.json.\n" \
                  f"Eventi problematici: {len(problematic)} (vedi debug_export_mese_problematici.json)"
            self.calendar_result.insert(tk.END, msg + "\n")
            messagebox.showinfo("Esportazione completata", msg)
        except Exception as e:
            logging.error(f"Errore esportazione eventi mese: {str(e)}")
            messagebox.showerror("Errore", f"Errore esportazione eventi mese: {str(e)}")

    def sync_selected_month_calendar(self):
        """Sincronizza direttamente gli eventi del mese e calendario selezionato, con loader e log."""
        try:
            month = int(self.export_month_var.get())
            year = datetime.now().year
            selected = self.calendar_var.get()
            calendar_id = self.calendar_ids.get(selected)
            if not calendar_id:
                messagebox.showerror("Errore", "Seleziona un calendario valido")
                return
            if not self.manager:
                self.manager = AppointmentManager()
            # Mostra loader
            self.progress.pack()
            self.progress.start(10)
            self.progress_var.set("Sincronizzazione in corso...")
            self.update_idletasks()
            Thread(target=self._threaded_sync_month_calendar, args=(month, year, calendar_id, selected)).start()
        except Exception as e:
            logging.error(f"Errore avvio sync diretta: {e}")
            messagebox.showerror("Errore", str(e))

    def _threaded_sync_month_calendar(self, month, year, calendar_id, calendar_name):
        import time
        from googleapiclient.errors import HttpError
        try:
            if not self.calendar_sync:
                self.calendar_sync = GoogleCalendarSync()
            self.calendar_sync.authenticate()
            studio = None
            for s, cid in self.studio_calendar_ids.items():
                if cid == calendar_id:
                    studio = s
                    break
            appointments = self.manager.db_handler.get_appointments(month=month, year=year)
            # Applica filtro studio se necessario
            if studio:
                appointments = [a for a in appointments if int(a.get('STUDIO', 0)) == studio]
            # Carica mappatura locale
            sync_map = load_sync_map()
            to_create, to_update, to_skip = filter_appointments_for_sync(appointments, sync_map)
            n_inserted, n_updated, errors = 0, 0, 0
            # Crea nuovi eventi
            for app in to_create:
                try:
                    mapped = map_appointment(app)
                    event = self.calendar_sync.create_event(mapped, cal_id=calendar_id)
                    # Aggiorna mappatura locale
                    app_id = f"{app['DATA']}_{app['ORA_INIZIO']}_{app['STUDIO']}_{app.get('PAZIENTE','') or app.get('DESCRIZIONE','')}"
                    app_hash = compute_appointment_hash(app)
                    sync_map[app_id] = {'event_id': event['id'], 'hash': app_hash}
                    n_inserted += 1
                except Exception as e:
                    errors += 1
                    logging.warning(f"[SKIP] Appuntamento non valido: {e}")
            # (Opzionale) Aggiorna eventi modificati (se implementato update_event)
            # for app, eid in to_update:
            #     try:
            #         mapped = map_appointment(app)
            #         self.calendar_sync.update_event(mapped, eid, cal_id=calendar_id)
            #         app_id = f"{app['DATA']}_{app['ORA_INIZIO']}_{app['STUDIO']}_{app.get('PAZIENTE','') or app.get('DESCRIZIONE','')}
            #         app_hash = compute_appointment_hash(app)
            #         sync_map[app_id] = {'event_id': eid, 'hash': app_hash}
            #         n_updated += 1
            #     except Exception as e:
            #         errors += 1
            #         logging.warning(f"[SKIP] Appuntamento non aggiornato: {e}")
            save_sync_map(sync_map)
            if n_inserted == 0 and n_updated == 0:
                msg = "Nessun evento da inserire o aggiornare: tutto già sincronizzato."
            else:
                msg = f"Sincronizzazione completata su {calendar_name}\nEventi inseriti: {n_inserted}\nAggiornati: {n_updated}\nErrori: {errors}"
            self.after(0, lambda: messagebox.showinfo("Sync completata", msg))
            self.after(0, lambda: self.calendar_result.insert(tk.END, msg + "\n"))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Errore Sync", str(e)))
        finally:
            self.after(0, self.progress.stop)
            self.after(0, self.progress.pack_forget)
            self.after(0, lambda: self.progress_var.set(""))

def main():
    app = GuiApp()
    app.mainloop()

if __name__ == "__main__":
    main()