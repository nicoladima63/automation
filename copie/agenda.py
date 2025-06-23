import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import dbf
import pandas as pd
import core.calendar
from datetime import datetime, timedelta, date
import locale
import re

class CalendarioMedico:
    def __init__(self, root):
        self.root = root
        self.root.title("Calendario Medico - Gestione Appuntamenti")
        self.root.geometry("1400x900")
        
        # Dati
        self.table_dbf = None
        self.df_appuntamenti = None
        self.data_corrente = datetime.now()
        self.vista_corrente = "mese"  # giorno, settimana, mese
        
        # Colori
        self.colori = {
            'oggi': '#FFE4B5',
            'appuntamento': '#87CEEB',
            'appuntamento_urgente': '#FFB6C1',
            'weekend': '#F0F0F0',
            'selezionato': '#98FB98',
            'guardia': '#FFA07A'
        }
        
        # Imposta locale italiano se disponibile
        try:
            locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'Italian_Italy.1252')
            except:
                pass
        
        self.setup_ui()
    
    def setup_ui(self):
        # Frame principale
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar superiore
        self.create_toolbar(main_frame)
        
        # Frame contenuto principale
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Frame calendario (sinistra)
        self.calendar_frame = ttk.Frame(content_frame)
        self.calendar_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame dettagli (destra)
        self.details_frame = ttk.LabelFrame(content_frame, text="Dettagli Appuntamenti", padding="10")
        self.details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Lista appuntamenti nel frame dettagli
        self.create_details_panel()
        
        # Carica file DBF all'avvio
        self.carica_file_dbf()
    
    def create_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # Pulsante carica file
        ttk.Button(toolbar, text="📁 Carica DBF", 
                  command=self.carica_file_dbf).pack(side=tk.LEFT, padx=(0, 10))
        
        # Separatore
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Navigazione data
        ttk.Button(toolbar, text="◀◀", 
                  command=lambda: self.cambia_periodo(-1, "anno")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="◀", 
                  command=lambda: self.cambia_periodo(-1, "mese")).pack(side=tk.LEFT, padx=2)
        
        # Label data corrente
        self.label_data = ttk.Label(toolbar, font=('Arial', 12, 'bold'))
        self.label_data.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(toolbar, text="▶", 
                  command=lambda: self.cambia_periodo(1, "mese")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="▶▶", 
                  command=lambda: self.cambia_periodo(1, "anno")).pack(side=tk.LEFT, padx=2)
        
        # Separatore
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Pulsanti vista
        ttk.Button(toolbar, text="Giorno", 
                  command=lambda: self.cambia_vista("giorno")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Settimana", 
                  command=lambda: self.cambia_vista("settimana")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Mese", 
                  command=lambda: self.cambia_vista("mese")).pack(side=tk.LEFT, padx=2)
        
        # Pulsante oggi
        ttk.Button(toolbar, text="🏠 Oggi", 
                  command=self.vai_oggi).pack(side=tk.RIGHT)
        
        self.aggiorna_label_data()
    
    def create_details_panel(self):
        # Frame per i controlli
        controls_frame = ttk.Frame(self.details_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Statistiche
        self.stats_label = ttk.Label(controls_frame, text="Nessun file caricato")
        self.stats_label.pack()
        
        # Lista appuntamenti
        list_frame = ttk.Frame(self.details_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar per la lista
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox per appuntamenti
        self.listbox_appuntamenti = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                             width=40, height=20)
        self.listbox_appuntamenti.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox_appuntamenti.yview)
        
        # Bind per selezione
        self.listbox_appuntamenti.bind('<<ListboxSelect>>', self.on_appuntamento_select)
    
    def carica_file_dbf(self):
        file_path = filedialog.askopenfilename(
            title="Seleziona file DBF Appuntamenti",
            filetypes=[("File DBF", "*.dbf"), ("Tutti i file", "*.*")]
        )
        
        if file_path:
            try:
                # Apri il file DBF
                self.table_dbf = dbf.Table(file_path)
                self.table_dbf.open()
                
                # Converti in DataFrame per facilità d'uso
                records = []
                for record in self.table_dbf:
                    record_dict = {}
                    for field_name in self.table_dbf.field_names:
                        try:
                            value = record[field_name]
                            if value is None:
                                record_dict[field_name] = ""
                            else:
                                record_dict[field_name] = value
                        except:
                            record_dict[field_name] = ""
                    records.append(record_dict)
                
                self.df_appuntamenti = pd.DataFrame(records)
                
                # Processa le date
                self.processa_date()
                
                # Aggiorna interfaccia
                self.aggiorna_statistiche()
                self.aggiorna_calendario()
                
                messagebox.showinfo("Successo", 
                                  f"File caricato con successo!\n"
                                  f"Record: {len(self.df_appuntamenti)}\n"
                                  f"Campi: {len(self.df_appuntamenti.columns)}")
                
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nel caricamento del file:\n{str(e)}")
    
    def processa_date(self):
        """Processa e standardizza le colonne delle date"""
        if self.df_appuntamenti is None:
            return
        
        # Cerca colonne con date
        date_columns = []
        for col in self.df_appuntamenti.columns:
            if 'DATA' in col.upper():
                date_columns.append(col)
        
        # Processa ogni colonna data
        for col in date_columns:
            try:
                # Prova diversi formati di data
                self.df_appuntamenti[col + '_parsed'] = pd.to_datetime(
                    self.df_appuntamenti[col], 
                    format='%Y%m%d', 
                    errors='coerce'
                )
                
                # Se fallisce, prova altri formati
                if self.df_appuntamenti[col + '_parsed'].isna().all():
                    self.df_appuntamenti[col + '_parsed'] = pd.to_datetime(
                        self.df_appuntamenti[col], 
                        errors='coerce'
                    )
            except:
                continue
        
        # Usa DB_APDATA come data principale
        if 'DB_APDATA' in self.df_appuntamenti.columns:
            self.df_appuntamenti['data_appuntamento'] = pd.to_datetime(
                self.df_appuntamenti['DB_APDATA'], 
                format='%Y%m%d', 
                errors='coerce'
            )
        
        # Filtra righe con date valide
        if 'data_appuntamento' in self.df_appuntamenti.columns:
            self.df_appuntamenti = self.df_appuntamenti.dropna(subset=['data_appuntamento'])
    
    def aggiorna_statistiche(self):
        if self.df_appuntamenti is None:
            self.stats_label.config(text="Nessun file caricato")
            return
        
        total = len(self.df_appuntamenti)
        oggi = datetime.now().date()
        
        # Conta appuntamenti di oggi
        appuntamenti_oggi = 0
        if 'data_appuntamento' in self.df_appuntamenti.columns:
            appuntamenti_oggi = len(self.df_appuntamenti[
                self.df_appuntamenti['data_appuntamento'].dt.date == oggi
            ])
        
        # Conta appuntamenti di guardia
        guardia = 0
        if 'DB_GUARDIA' in self.df_appuntamenti.columns:
            guardia = len(self.df_appuntamenti[
                self.df_appuntamenti['DB_GUARDIA'].str.upper() == 'S'
            ])
        
        stats_text = f"Totale: {total}\nOggi: {appuntamenti_oggi}\nGuardia: {guardia}"
        self.stats_label.config(text=stats_text)
    
    def cambia_periodo(self, direzione, unita):
        if unita == "anno":
            self.data_corrente = self.data_corrente.replace(year=self.data_corrente.year + direzione)
        elif unita == "mese":
            nuovo_mese = self.data_corrente.month + direzione
            nuovo_anno = self.data_corrente.year
            
            if nuovo_mese > 12:
                nuovo_mese = 1
                nuovo_anno += 1
            elif nuovo_mese < 1:
                nuovo_mese = 12
                nuovo_anno -= 1
            
            self.data_corrente = self.data_corrente.replace(year=nuovo_anno, month=nuovo_mese)
        
        self.aggiorna_label_data()
        self.aggiorna_calendario()
    
    def cambia_vista(self, vista):
        self.vista_corrente = vista
        self.aggiorna_calendario()
    
    def vai_oggi(self):
        self.data_corrente = datetime.now()
        self.aggiorna_label_data()
        self.aggiorna_calendario()
    
    def aggiorna_label_data(self):
        if self.vista_corrente == "mese":
            mese_anno = self.data_corrente.strftime("%B %Y")
            self.label_data.config(text=mese_anno.title())
        elif self.vista_corrente == "settimana":
            # Calcola inizio e fine settimana
            inizio_settimana = self.data_corrente - timedelta(days=self.data_corrente.weekday())
            fine_settimana = inizio_settimana + timedelta(days=6)
            self.label_data.config(text=f"{inizio_settimana.strftime('%d/%m')} - {fine_settimana.strftime('%d/%m/%Y')}")
        else:  # giorno
            self.label_data.config(text=self.data_corrente.strftime("%d %B %Y"))
    
    def aggiorna_calendario(self):
        # Pulisci il frame calendario
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        if self.vista_corrente == "mese":
            self.mostra_vista_mese()
        elif self.vista_corrente == "settimana":
            self.mostra_vista_settimana()
        else:
            self.mostra_vista_giorno()
    
    def mostra_vista_mese(self):
        # Crea griglia mese
        cal = calendar.monthcalendar(self.data_corrente.year, self.data_corrente.month)
        
        # Intestazioni giorni settimana
        giorni = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        for i, giorno in enumerate(giorni):
            label = ttk.Label(self.calendar_frame, text=giorno, font=('Arial', 10, 'bold'))
            label.grid(row=0, column=i, padx=1, pady=1, sticky="nsew")
        
        oggi = datetime.now().date()
        
        # Crea celle per ogni giorno
        for settimana_num, settimana in enumerate(cal):
            for giorno_num, giorno in enumerate(settimana):
                if giorno == 0:
                    continue  # Giorno vuoto
                
                data_giorno = date(self.data_corrente.year, self.data_corrente.month, giorno)
                
                # Conta appuntamenti per questo giorno
                num_appuntamenti = self.conta_appuntamenti_giorno(data_giorno)
                
                # Determina colore
                bg_color = 'white'
                if data_giorno == oggi:
                    bg_color = self.colori['oggi']
                elif giorno_num >= 5:  # Weekend
                    bg_color = self.colori['weekend']
                elif num_appuntamenti > 0:
                    bg_color = self.colori['appuntamento']
                
                # Crea frame per il giorno
                day_frame = tk.Frame(self.calendar_frame, bg=bg_color, relief=tk.RAISED, bd=1)
                day_frame.grid(row=settimana_num+1, column=giorno_num, padx=1, pady=1, sticky="nsew")
                
                # Numero del giorno
                day_label = tk.Label(day_frame, text=str(giorno), bg=bg_color, font=('Arial', 12, 'bold'))
                day_label.pack(anchor=tk.NW)
                
                # Numero appuntamenti
                if num_appuntamenti > 0:
                    app_label = tk.Label(day_frame, text=f"{num_appuntamenti} app.", 
                                       bg=bg_color, font=('Arial', 8))
                    app_label.pack(anchor=tk.CENTER)
                
                # Bind click
                day_frame.bind("<Button-1>", lambda e, d=data_giorno: self.seleziona_giorno(d))
                day_label.bind("<Button-1>", lambda e, d=data_giorno: self.seleziona_giorno(d))
        
        # Configura grid
        for i in range(7):
            self.calendar_frame.columnconfigure(i, weight=1)
        for i in range(len(cal)+1):
            self.calendar_frame.rowconfigure(i, weight=1)
    
    def mostra_vista_settimana(self):
        # Calcola inizio settimana (lunedì)
        inizio_settimana = self.data_corrente - timedelta(days=self.data_corrente.weekday())
        
        # Crea vista settimana
        for i in range(7):
            data_giorno = inizio_settimana + timedelta(days=i)
            num_appuntamenti = self.conta_appuntamenti_giorno(data_giorno.date())
            
            # Frame per il giorno
            day_frame = ttk.LabelFrame(self.calendar_frame, 
                                     text=f"{data_giorno.strftime('%A %d/%m')}")
            day_frame.grid(row=0, column=i, padx=2, pady=2, sticky="nsew")
            
            # Lista appuntamenti del giorno
            if num_appuntamenti > 0:
                appuntamenti = self.get_appuntamenti_giorno(data_giorno.date())
                for app in appuntamenti[:5]:  # Mostra max 5 appuntamenti
                    descrizione = str(app.get('DESCRIZIONE', 'N/A'))[:20]
                    ora = str(app.get('DB_APOREIN', ''))[:5]
                    label_text = f"{ora} - {descrizione}"
                    ttk.Label(day_frame, text=label_text, font=('Arial', 8)).pack(anchor=tk.W)
                
                if num_appuntamenti > 5:
                    ttk.Label(day_frame, text=f"... e altri {num_appuntamenti-5}", 
                            font=('Arial', 8, 'italic')).pack(anchor=tk.W)
            else:
                ttk.Label(day_frame, text="Nessun appuntamento", 
                        font=('Arial', 8, 'italic')).pack()
            
            # Bind click
            day_frame.bind("<Button-1>", lambda e, d=data_giorno.date(): self.seleziona_giorno(d))
        
        # Configura grid
        for i in range(7):
            self.calendar_frame.columnconfigure(i, weight=1)
        self.calendar_frame.rowconfigure(0, weight=1)
    
    def mostra_vista_giorno(self):
        data_oggi = self.data_corrente.date()
        appuntamenti = self.get_appuntamenti_giorno(data_oggi)
        
        # Titolo
        title_label = ttk.Label(self.calendar_frame, 
                              text=f"Appuntamenti del {data_oggi.strftime('%d %B %Y')}", 
                              font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)
        
        if not appuntamenti:
            ttk.Label(self.calendar_frame, text="Nessun appuntamento per oggi", 
                    font=('Arial', 12)).pack(pady=20)
            return
        
        # Frame scrollabile per appuntamenti
        canvas = tk.Canvas(self.calendar_frame)
        scrollbar = ttk.Scrollbar(self.calendar_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mostra ogni appuntamento
        for i, app in enumerate(appuntamenti):
            app_frame = ttk.LabelFrame(scrollable_frame, text=f"Appuntamento {i+1}")
            app_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Dettagli appuntamento
            details = [
                ("Orario entrata", app.get('DB_APOREIN', 'N/A')),
                ("Orario uscita", app.get('DB_APOREOU', 'N/A')),
                ("Descrizione", app.get('DESCRIZIONE', 'N/A')),
                ("Medico", app.get('DB_APMEDIC', 'N/A')),
                ("Studio", app.get('DB_APSTUDI', 'N/A')),
                ("Priorità", app.get('DB_APPRIOR', 'N/A')),
                ("Note", app.get('DB_NOTE', 'N/A'))
            ]
            
            for label, value in details:
                if value and str(value).strip():
                    row_frame = ttk.Frame(app_frame)
                    row_frame.pack(fill=tk.X, padx=5, pady=2)
                    ttk.Label(row_frame, text=f"{label}:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
                    ttk.Label(row_frame, text=str(value), font=('Arial', 9)).pack(side=tk.LEFT, padx=(10, 0))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def conta_appuntamenti_giorno(self, data_giorno):
        if self.df_appuntamenti is None or 'data_appuntamento' not in self.df_appuntamenti.columns:
            return 0
        
        return len(self.df_appuntamenti[
            self.df_appuntamenti['data_appuntamento'].dt.date == data_giorno
        ])
    
    def get_appuntamenti_giorno(self, data_giorno):
        if self.df_appuntamenti is None or 'data_appuntamento' not in self.df_appuntamenti.columns:
            return []
        
        appuntamenti_giorno = self.df_appuntamenti[
            self.df_appuntamenti['data_appuntamento'].dt.date == data_giorno
        ]
        
        return appuntamenti_giorno.to_dict('records')
    
    def seleziona_giorno(self, data_giorno):
        # Aggiorna lista appuntamenti nel pannello dettagli
        appuntamenti = self.get_appuntamenti_giorno(data_giorno)
        
        self.listbox_appuntamenti.delete(0, tk.END)
        
        if not appuntamenti:
            self.listbox_appuntamenti.insert(0, f"Nessun appuntamento per {data_giorno.strftime('%d/%m/%Y')}")
            return
        
        for i, app in enumerate(appuntamenti):
            ora = str(app.get('DB_APOREIN', ''))[:5]
            descrizione = str(app.get('DESCRIZIONE', 'N/A'))[:25]
            medico = str(app.get('DB_APMEDIC', ''))[:15]
            
            testo = f"{ora} | {descrizione}"
            if medico:
                testo += f" | Dr. {medico}"
            
            self.listbox_appuntamenti.insert(tk.END, testo)
    
    def on_appuntamento_select(self, event):
        # Placeholder per gestire la selezione di un appuntamento
        selection = self.listbox_appuntamenti.curselection()
        if selection:
            index = selection[0]
            # Qui si potrebbero mostrare più dettagli dell'appuntamento selezionato
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarioMedico(root)
    root.mainloop()