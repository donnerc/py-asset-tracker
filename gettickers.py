import os
import sys
import csv
from collections import namedtuple

debug = False

def find_file() -> str:
    # find a file ACTIVITIES_REPORT-*.csv in the current directory
        files = [f for f in os.listdir('.') if f.startswith('ACTIVITIES_REPORT-') and f.endswith('.csv')]
        if not files:
            print("Aucun fichier ACTIVITIES_REPORT-*.csv trouvé dans le répertoire actuel.")
            sys.exit(1)
        filename = files[0]  # Prendre le premier fichier trouvé
        if debug: print(f"Fichier trouvé : {filename}")
        return filename


def get_tickers_from_csv(file_path: str) -> list[str]:
    # Nettoyer les noms de champs pour les rendre valides
    def clean_field_name(name):
        return name.strip('\ufeff').replace(' ', '_').replace('/', '_').replace(';', '').strip()
    
    tickers = []
    with open(file_path, 'r') as csvfile:
        # use namedtuple to read the header and access columns by name
        
        csvreader = csv.reader(csvfile, delimiter=';')
        header = next(csvreader)  # Lire l'en-tête
        clean_header = [clean_field_name(h) for h in header]
        if debug: print(f"En-tête nettoyé : {clean_header}")
        Row = namedtuple('Row', clean_header)
        for row in csvreader:
            row_tuple = Row(*row)
            tickers.append(row_tuple.ASSET)
    return tickers

EXCLUDE_TICKERS = set(['SWQ'])


if __name__ == "__main__":
    if sys.argv[1:]:
        filename = sys.argv[1]
    else:        
        filename = find_file()
        
    tickers = get_tickers_from_csv(filename)
    keep = lambda t: t.strip() != '' and t.strip() not in EXCLUDE_TICKERS
    tickers = list(set([line.strip() for line in tickers if keep(line)]))
    print(tickers)
