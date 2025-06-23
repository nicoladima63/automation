import tkinter as tk
from tkinter import messagebox
import subprocess
import datetime
import os

def esegui_script(opzioni):
    comando = ['python', 'script.py'] + opzioni
    try:
        risultato = subprocess.run(comando, capture_output=True, text=True)
        output_text.delete('1.0', tk.END)
        output_text.insert(tk.END, risultato.stdout)
        if risultato.stderr:
            output_text.insert(tk.END, "\n--- ERRORI ---\n" + risultato.stderr)
    except Exception as e:
        messagebox.showerror("Errore", f"Errore durante l'esecuzione: {e}")


def invia_test():
    esegui_script(['--test', '--solo-primo', '--esegui-ora'])

def test_conn_db():
    esegui_script(['--test-db'])

def test_config_twilio():
    esegui_script(['--test-twilio'])

def esegui_invio():
    esegui_script(['--esegui-ora'])

def genera_report_pdf():
    from report_generator import genera_pdf_log
    oggi = datetime.date.today().strftime('%Y-%m-%d')
    filename = f"report_promemoria_{oggi}.pdf"
    genera_pdf_log('promemoria_appuntamenti.log', filename)
    messagebox.showinfo("PDF Creato", f"Report salvato come {filename}")

# GUI
root = tk.Tk()
root.title("Gestione Promemoria Appuntamenti")

frame_btn = tk.Frame(root)
frame_btn.pack(pady=10)

btn_test = tk.Button(frame_btn, text="Invia test (1° solo)", width=25, command=invia_test)
btn_test.grid(row=0, column=0, padx=5, pady=5)

btn_db = tk.Button(frame_btn, text="Test connessione DB", width=25, command=test_conn_db)
btn_db.grid(row=0, column=1, padx=5, pady=5)

btn_twilio = tk.Button(frame_btn, text="Test config Twilio", width=25, command=test_config_twilio)
btn_twilio.grid(row=1, column=0, padx=5, pady=5)

btn_esegui = tk.Button(frame_btn, text="Esegui Invio Reale", width=25, bg='red', fg='white', command=esegui_invio)
btn_esegui.grid(row=1, column=1, padx=5, pady=5)

btn_pdf = tk.Button(root, text="Genera PDF report invii", width=30, command=genera_report_pdf)
btn_pdf.pack(pady=10)

output_text = tk.Text(root, wrap=tk.WORD, height=20, width=100)
output_text.pack(padx=10, pady=10)

root.mainloop()
