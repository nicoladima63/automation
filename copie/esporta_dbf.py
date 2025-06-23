import os
from tkinter import Tk, filedialog, messagebox
import dbf
import pandas as pd
import csv

def scegli_file_dbf():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Seleziona file DBF",
        filetypes=[("File DBF", "*.dbf")]
    )
    return file_path

def converti_dbf_ottimizzato(file_path):
    try:
        # Apertura del file DBF
        table = dbf.Table(file_path)
        table.open()
        
        print(f"Conversione di {len(table)} record con {len(table.field_names)} campi")
        print(f"Campi: {table.field_names}")
        
        # Estrazione dati ottimizzata
        records = []
        field_names = table.field_names
        
        for i, record in enumerate(table):
            if i % 1000 == 0:  # Progress indicator
                print(f"Processati {i} record...")
            
            record_dict = {}
            for field_name in field_names:
                try:
                    value = record[field_name]
                    if value is None:
                        record_dict[field_name] = ""
                    elif isinstance(value, str):
                        # Pulisce caratteri problematici
                        record_dict[field_name] = value.strip().replace('\n', ' ').replace('\r', ' ')
                    else:
                        record_dict[field_name] = str(value).strip()
                except:
                    record_dict[field_name] = ""
            
            records.append(record_dict)
        
        table.close()
        print(f"Tutti {len(records)} record processati!")
        
        # Crea DataFrame
        df = pd.DataFrame(records, columns=field_names)
        
        # Nome file base
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # CSV con punto e virgola (funziona meglio)
        csv_path = os.path.join(os.getcwd(), f"{base_name}.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig", sep=';', quoting=csv.QUOTE_MINIMAL)
        
        # Verifica risultati
        print(f"\nFile creato: {os.path.basename(csv_path)}")
        print(f"Righe: {len(df)}, Colonne: {len(df.columns)}")
        print(f"Nomi colonne: {list(df.columns)}")
        
        # Mostra preview primi record
        print("\nPreview primi 3 record:")
        for idx, row in df.head(3).iterrows():
            print(f"\nRecord {idx + 1}:")
            for col in df.columns:
                value = str(row[col])[:50] + "..." if len(str(row[col])) > 50 else str(row[col])
                print(f"  {col}: {value}")
        
        messagebox.showinfo("Successo", 
                          f"Conversione completata!\n\n"
                          f"Record processati: {len(df)}\n"
                          f"Colonne: {len(df.columns)}\n\n"
                          f"File creato: {os.path.basename(csv_path)}")
        
        # Apri il file CSV direttamente
        os.startfile(csv_path)
        
        return csv_path
        
    except Exception as e:
        messagebox.showerror("Errore", f"Errore durante la conversione:\n{str(e)}")
        print("Errore dettagliato:", e)
        import traceback
        traceback.print_exc()
        return None

def verifica_csv(csv_path):
    """Verifica che il CSV sia stato creato correttamente"""
    try:
        # Leggi il CSV per verificare
        df_check = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        print(f"\nVerifica file {os.path.basename(csv_path)}:")
        print(f"Righe lette: {len(df_check)}")
        print(f"Colonne lette: {len(df_check.columns)}")
        print(f"Nomi colonne: {list(df_check.columns)}")
        
        if len(df_check.columns) == 1:
            print("⚠️  ATTENZIONE: Tutte le colonne sono in una sola colonna!")
        else:
            print("✅ File CSV creato correttamente con colonne separate!")
            
    except Exception as e:
        print(f"Errore nella verifica: {e}")

if __name__ == "__main__":
    file_dbf = scegli_file_dbf()
    if file_dbf:
        print(f"File selezionato: {file_dbf}")
        
        csv_risultato = converti_dbf_ottimizzato(file_dbf)
        
        if csv_risultato:
            print("\n" + "="*50)
            verifica_csv(csv_risultato)