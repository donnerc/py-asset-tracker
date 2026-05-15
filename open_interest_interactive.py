import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.backends.backend_agg as agg
import pygame
import sys
import time

# --- Configuration initiale ---
TICKER_SYMBOL = "MU"
INDICE_ECHEANCE = 0
UPDATE_INTERVAL = 60  # secondes

if len(sys.argv) > 1:
    TICKER_SYMBOL = sys.argv[1].upper()
if len(sys.argv) > 2:
    try:
        INDICE_ECHEANCE = int(sys.argv[2])
    except ValueError:
        print("Erreur : L'index d'échéance doit être un entier.")
        exit()

# Initialisation Pygame
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(f"Open Interest Real-Time - {TICKER_SYMBOL}")
clock = pygame.time.Clock()
font_main = pygame.font.SysFont("Arial", 18)
font_input = pygame.font.SysFont("Arial", 32, bold=True)

# Variables globales pour le mapping et l'état
y_min, y_max = 0, 1
plot_rect = pygame.Rect(0, 0, 1, 1)
is_input_mode = False
input_text = ""

def fetch_and_plot(symbol):
    """Récupère les données et génère une surface Pygame du graphique."""
    global y_min, y_max, plot_rect
    print(f"[{time.strftime('%H:%M:%S')}] Mise à jour des données pour {symbol}...")
    ticker = yf.Ticker(symbol)
    
    try:
        dates_echeance = ticker.options
        if not dates_echeance:
            return None, f"Options non disponibles pour {symbol}"
        
        # S'assurer que l'index est valide pour le nouveau ticker
        idx = INDICE_ECHEANCE if INDICE_ECHEANCE < len(dates_echeance) else 0
        prochaine_echeance = dates_echeance[idx]
        chaine_options = ticker.option_chain(prochaine_echeance)
        
        hist = ticker.history(period="1d")
        if hist.empty:
            return None, "Cours indisponible"
        cours_actuel = hist['Close'].iloc[-1]

        df_calls = chaine_options.calls[['strike', 'openInterest']].copy()
        df_puts = chaine_options.puts[['strike', 'openInterest']].copy()

        marge = 50
        df_calls = df_calls[(df_calls['strike'] >= cours_actuel - marge) & (df_calls['strike'] <= cours_actuel + marge)]
        df_puts = df_puts[(df_puts['strike'] >= cours_actuel - marge) & (df_puts['strike'] <= cours_actuel + marge)]

        df_total = pd.merge(df_calls, df_puts, on='strike', how='outer', suffixes=('_call', '_put')).fillna(0)
        df_total = df_total.sort_values(by='strike')

        if df_total.empty:
            return None, "Aucune donnée dans la marge"

        # Création du graphique Matplotlib
        fig, ax = plt.subplots(figsize=(10, 7), dpi=100)
        
        if len(df_total) > 1:
            min_diff = df_total['strike'].diff().min()
            bar_height = min_diff * 0.8 if min_diff > 0 else 0.8
        else:
            bar_height = 0.8

        ax.barh(df_total['strike'], -df_total['openInterest_put'], color='#e74c3c', label='Puts', height=bar_height)
        ax.barh(df_total['strike'], df_total['openInterest_call'], color='#2ecc71', label='Calls', height=bar_height)
        ax.axhline(y=cours_actuel, color='#f1c40f', linestyle='--', linewidth=2, label=f'Prix: {cours_actuel:.2f}')

        ax.set_title(f"OI {symbol} - {prochaine_echeance} (MàJ: {time.strftime('%H:%M:%S')})", fontsize=12, fontweight='bold')
        ax.set_xlabel("Nombre de contrats (Open Interest)")
        ax.set_ylabel("Valeur des strikes ($)")
        
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(int(abs(tick))) for tick in ticks])
        ax.grid(axis='x', linestyle=':', alpha=0.6)
        ax.legend(loc='upper right', fontsize='small')
        
        plt.tight_layout()

        # Sauvegarder les limites pour le suivi de la souris
        y_min, y_max = ax.get_ylim()
        pos = ax.get_position()
        plot_rect = pygame.Rect(
            int(pos.x0 * SCREEN_WIDTH),
            int((1 - pos.y1) * SCREEN_HEIGHT),
            int(pos.width * SCREEN_WIDTH),
            int(pos.height * SCREEN_HEIGHT)
        )

        # Conversion Figure -> Pygame Surface
        canvas = agg.FigureCanvasAgg(fig)
        canvas.draw()
        size = canvas.get_width_height()
        raw_data = canvas.buffer_rgba()
        
        surf = pygame.image.frombuffer(raw_data, size, "RGBA")
        plt.close(fig)
        return surf, None

    except Exception as e:
        return None, str(e)

# --- Boucle principale ---
running = True
last_update = 0
image_surface = None
error_msg = "Chargement..."

while running:
    current_time = time.time()
    
    # Mise à jour périodique (seulement si pas en mode saisie)
    if not is_input_mode and (current_time - last_update > UPDATE_INTERVAL):
        new_surf, err = fetch_and_plot(TICKER_SYMBOL)
        if new_surf:
            image_surface = new_surf
            error_msg = None
            pygame.display.set_caption(f"Open Interest Real-Time - {TICKER_SYMBOL}")
        else:
            error_msg = f"Erreur: {err}"
        last_update = current_time

    # Gestion des événements
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if is_input_mode:
                if event.key == pygame.K_RETURN:
                    if input_text.strip():
                        TICKER_SYMBOL = input_text.strip().upper()
                        last_update = 0 # Force refresh
                    is_input_mode = False
                    input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_ESCAPE:
                    is_input_mode = False
                    input_text = ""
                else:
                    # Ajouter le caractère tapé
                    if event.unicode.isalnum():
                        input_text += event.unicode.upper()
            else:
                if event.key == pygame.K_f:
                    is_input_mode = True
                    input_text = ""
                elif event.key == pygame.K_r:
                    last_update = 0

    # Affichage
    screen.fill((30, 30, 30))
    if image_surface:
        screen.blit(image_surface, (0, 0))
        
        # Suivi de la souris (seulement si pas en mode saisie)
        if not is_input_mode:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if plot_rect.collidepoint(mouse_x, mouse_y):
                relative_y = (mouse_y - plot_rect.top) / plot_rect.height
                current_strike = y_max - (relative_y * (y_max - y_min))
                pygame.draw.line(screen, (200, 200, 200), (plot_rect.left, mouse_y), (plot_rect.right, mouse_y), 1)
                label = font_main.render(f"{current_strike:.2f} $", True, (255, 255, 255), (50, 50, 50))
                screen.blit(label, (mouse_x + 15, mouse_y - 10))

    # Overlay de saisie
    if is_input_mode:
        # Rectangle de fond semi-transparent
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Boîte de dialogue
        dialog_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 50, 400, 100)
        pygame.draw.rect(screen, (50, 50, 50), dialog_rect)
        pygame.draw.rect(screen, (200, 200, 200), dialog_rect, 2)
        
        prompt_surf = font_main.render("Entrez un nouveau ticker :", True, (200, 200, 200))
        screen.blit(prompt_surf, (dialog_rect.x + 20, dialog_rect.y + 15))
        
        input_surf = font_input.render(input_text + "|", True, (255, 255, 255))
        screen.blit(input_surf, (dialog_rect.x + 20, dialog_rect.y + 45))

    if error_msg and not is_input_mode:
        font_err = pygame.font.SysFont("Arial", 24)
        text_surf = font_err.render(error_msg, True, (255, 100, 100))
        screen.blit(text_surf, (20, 20))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
