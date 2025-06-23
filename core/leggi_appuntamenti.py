import argparse
from dbfread import DBF
from datetime import datetime, date, timedelta
from config import (
    PATH_APPUNTAMENTI_DBF,
    PATH_ANAGRAFICA_DBF,
    COL_APPUNTAMENTI_DATA,
    COL_APPUNTAMENTI_ORA,
    COL_APPUNTAMENTI_ORA_FINE,
    COL_APPUNTAMENTI_IDPAZIENTE,
    COL_APPUNTAMENTI_TIPO,
    COL_APPUNTAMENTI_MEDICO,
    COL_PAZIENTI_ID,
    COL_PAZIENTI_NOME,
    COL_PAZIENTI_COGNOME,
    TIPI_APPUNTAMENTO,
    MEDICI,
)

def main():
    parser = argparse.ArgumentParser(description="Leggi appuntamenti dal DBF")
    parser.add_argument("--test-mese", type=int, help="Mese da testare (1-12), default mese corrente")
    args = parser.parse_args()

    today = date.today()
    mese = args.test_mese if args.test_mese and 1 <= args.test_mese <= 12 else today.month
    anno = today.year

    start_date = date(anno, mese, 1)
    if mese == 12:
        end_date = date(anno + 1, 1, 1)
    else:
        end_date = date(anno, mese + 1, 1)

    print(f"Appuntamenti dal {start_date.strftime('%d/%m/%Y')} al {(end_date - timedelta(days=1)).strftime('%d/%m/%Y')}:")

    # Carica pazienti in dizionario {id: "Cognome Nome"}
    pazienti_dbf = DBF(PATH_ANAGRAFICA_DBF, encoding='latin-1')
    PAZIENTI_NOMI = {
        str(record[COL_PAZIENTI_ID]).strip(): record[COL_PAZIENTI_NOME].strip()
        for record in pazienti_dbf
    }

    # Carica appuntamenti
    dbf = DBF(PATH_APPUNTAMENTI_DBF, encoding='latin-1')
    for record in dbf:
        data = record.get(COL_APPUNTAMENTI_DATA)
        if isinstance(data, date) and start_date <= data < end_date:
            ora_inizio = record.get(COL_APPUNTAMENTI_ORA, 0)
            ora_fine = record.get(COL_APPUNTAMENTI_ORA_FINE, 0)
            cod_paziente = str(record.get(COL_APPUNTAMENTI_IDPAZIENTE, '')).strip()
            nome_paziente = PAZIENTI_NOMI.get(cod_paziente, f"ID: {cod_paziente}")
            tipo_codice = (record.get(COL_APPUNTAMENTI_TIPO, '') or '').strip().upper()
            tipo_descrizione = TIPI_APPUNTAMENTO.get(tipo_codice, "Nota giornaliera")
            medico_codice = record.get(COL_APPUNTAMENTI_MEDICO)
            try:
                medico_int = int(medico_codice)
            except (TypeError, ValueError):
                medico_int = None

            medico_nome = MEDICI.get(medico_int) if medico_int else None

            # Formatto orari da interi tipo 830 -> "08:30"
            ora_inizio_str = f"{int(ora_inizio):04d}"
            ora_fine_str = f"{int(ora_fine):04d}"

            print(f"{data.strftime('%d/%m/%Y')} {ora_inizio_str[:2]}:{ora_inizio_str[2:]} - "
                  f"{ora_fine_str[:2]}:{ora_fine_str[2:]} | Paziente: {nome_paziente} | "
                  f"Tipo: {tipo_descrizione} | Medico: {medico_nome}")

if __name__ == "__main__":
    main()
