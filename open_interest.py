import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import sys

# 1. Gestion des paramètres de ligne de commande
ticker_symbol = "MU"
indice_echeance = 0

if len(sys.argv) > 1:
    ticker_symbol = sys.argv[1].upper()

if len(sys.argv) > 2:
    try:
        indice_echeance = int(sys.argv[2])
    except ValueError:
        print("Erreur : L'index d'échéance (2e paramètre) doit être un nombre entier.")
        exit()

# 2. Configuration du ticker et récupération des échéances
ticker = yf.Ticker(ticker_symbol)
try:
    dates_echeance = ticker.options
except Exception:
    print(f"Erreur lors de la récupération des données pour {ticker_symbol}.")
    exit()

if not dates_echeance:
    print(f"Impossible de récupérer les options pour {ticker_symbol}. Vérifiez que le ticker est correct.")
    exit()

# Validation de l'index d'échéance
if indice_echeance < 0 or indice_echeance >= len(dates_echeance):
    print(f"Erreur : Index {indice_echeance} hors limites pour {ticker_symbol}. Indices disponibles : 0 à {len(dates_echeance)-1}")
    print(f"Échéances disponibles : {', '.join(dates_echeance)}")
    exit()

prochaine_echeance = dates_echeance[indice_echeance]
print(f"Ticker : {ticker_symbol} | Échéance ({indice_echeance}) : {prochaine_echeance}")

# 3. Récupération de la chaîne d'options et du cours actuel
chaine_options = ticker.option_chain(prochaine_echeance)
# Récupération du dernier prix (lastPrice) pour tracer la ligne de cours actuel
try:
    hist = ticker.history(period="1d")
    if hist.empty:
        print(f"Impossible de récupérer le cours actuel pour {ticker_symbol}.")
        exit()
    cours_actuel = hist['Close'].iloc[-1]
except Exception as e:
    print(f"Erreur lors de la récupération du cours : {e}")
    exit()

df_calls = chaine_options.calls[['strike', 'openInterest']].copy()
df_puts = chaine_options.puts[['strike', 'openInterest']].copy()

# 4. Filtrage des données autour du cours actuel
marge = 50  # On regarde à +/- 50 dollars autour du cours actuel
df_calls = df_calls[(df_calls['strike'] >= cours_actuel - marge) & (df_calls['strike'] <= cours_actuel + marge)]
df_puts = df_puts[(df_puts['strike'] >= cours_actuel - marge) & (df_puts['strike'] <= cours_actuel + marge)]

# Fusionner les deux DataFrames
df_total = pd.merge(df_calls, df_puts, on='strike', how='outer', suffixes=('_call', '_put')).fillna(0)
df_total = df_total.sort_values(by='strike')

if df_total.empty:
    print("Aucune donnée d'options trouvée dans la marge spécifiée.")
    exit()

# 5. Construction du graphique Matplotlib
fig, ax = plt.subplots(figsize=(12, 8))

if len(df_total) > 1:
    min_diff = df_total['strike'].diff().min()
    bar_height = min_diff * 0.8 if min_diff > 0 else 0.8
else:
    bar_height = 0.8

ax.barh(df_total['strike'], -df_total['openInterest_put'], color='#e74c3c', label='Puts (Supports théoriques)', height=bar_height)
ax.barh(df_total['strike'], df_total['openInterest_call'], color='#2ecc71', label='Calls (Résistances théoriques)', height=bar_height)

ax.axhline(y=cours_actuel, color='#f1c40f', linestyle='--', linewidth=2, label=f'Cours actuel (~{cours_actuel:.2f} $)')

ax.set_title(f"Profil de l'Open Interest - {ticker_symbol} (Échéance : {prochaine_echeance})", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Volume d'Intérêt Ouvert (Open Interest)", fontsize=11)
ax.set_ylabel("Prix d'exercice (Strike Price en $)", fontsize=11)

ticks = ax.get_xticks()
ax.set_xticks(ticks)
ax.set_xticklabels([str(int(abs(tick))) for tick in ticks])

ax.grid(axis='x', linestyle=':', alpha=0.6)
ax.legend(loc='upper right', frameon=True, shadow=True)

plt.tight_layout()
nom_fichier = f"oi_{ticker_symbol}_{prochaine_echeance}.png"
plt.savefig(nom_fichier)
print(f"Graphique sauvegardé sous : {nom_fichier}")

try:
    plt.show()
except Exception:
    print("Note: L'affichage interactif n'est pas disponible dans cet environnement.")