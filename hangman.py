import argparse
import random
import sys
from datetime import date
from pathlib import Path

import pygame


WIDTH = 960
HEIGHT = 640
SCORE_FILE = Path(__file__).with_name("high_scores.txt")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIFFICULTIES = {
    "Facile": {"lives": 10, "time": 0},
    "Normal": {"lives": 7, "time": 90},
    "Difficile": {"lives": 5, "time": 45},
}
COLORS = {
    "sky": (35, 190, 224), "cream": (255, 222, 151), "orange": (237, 156, 32),
    "brown": (111, 66, 35), "white": (255, 255, 255), "ink": (31, 48, 65),
    "red": (215, 66, 59), "muted": (126, 163, 180),
}


def load_words(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Le fichier {file_path} est introuvable.")
    try:
        with path.open("r", encoding="utf-8") as file:
            words = [line.strip().lower() for line in file if line.strip().isalpha()]
    except UnicodeDecodeError as error:
        raise ValueError("Le fichier de mots doit être encodé en UTF-8.") from error
    except OSError as error:
        raise ValueError("Impossible de lire le fichier de mots.") from error
    if not words:
        raise ValueError("Le fichier ne contient aucun mot valide.")
    return words


def read_scores():
    if not SCORE_FILE.is_file():
        return []
    try:
        scores = []
        for line in SCORE_FILE.read_text(encoding="utf-8").splitlines():
            parts = [part.strip() for part in line.split("|")]
            if len(parts) == 3 and parts[1].isdigit():
                scores.append((int(parts[1]), parts[0], parts[2]))
        return sorted(scores, key=lambda score: score[0])[:10]
    except (OSError, UnicodeDecodeError):
        return []


def save_score(word, attempts):
    try:
        with SCORE_FILE.open("a", encoding="utf-8") as file:
            file.write(f"{word} | {attempts} | {date.today().isoformat()}\n")
    except OSError:
        pass


def draw_text(screen, font, text, position, color, center=False):
    surface = font.render(text, True, color)
    rectangle = surface.get_rect()
    rectangle.center = position if center else rectangle.topleft
    if not center:
        rectangle.topleft = position
    screen.blit(surface, rectangle)
    return rectangle


def draw_button(screen, font, rectangle, text, selected=False):
    color = COLORS["orange"] if selected else COLORS["cream"]
    pygame.draw.rect(screen, color, rectangle, border_radius=12)
    pygame.draw.rect(screen, COLORS["brown"], rectangle, 3, border_radius=12)
    draw_text(screen, font, text, rectangle.center, COLORS["ink"], center=True)


def draw_background(screen):
    screen.fill(COLORS["sky"])
    pygame.draw.circle(screen, (255, 237, 163), (820, 90), 45)
    pygame.draw.ellipse(screen, (187, 224, 193), (20, 285, 250, 110))
    pygame.draw.ellipse(screen, (169, 218, 158), (200, 300, 300, 115))
    pygame.draw.ellipse(screen, (145, 207, 133), (500, 290, 390, 125))
    pygame.draw.rect(screen, (123, 183, 86), (0, 390, WIDTH, 105))
    pygame.draw.rect(screen, (132, 88, 52), (0, 495, WIDTH, 145))


def draw_gallows(screen, missed, font):
    pygame.draw.rect(screen, COLORS["brown"], (650, 435, 230, 18), border_radius=4)
    pygame.draw.rect(screen, COLORS["brown"], (690, 155, 18, 280), border_radius=4)
    pygame.draw.rect(screen, COLORS["brown"], (690, 145, 170, 16), border_radius=4)
    pygame.draw.line(screen, COLORS["brown"], (795, 160), (795, 205), 7)
    pygame.draw.line(screen, COLORS["brown"], (795, 160), (850, 205), 7)
    pygame.draw.line(screen, COLORS["brown"], (850, 205), (850, 435), 7)
    stages = [
        lambda: pygame.draw.circle(screen, COLORS["ink"], (795, 240), 32, 7),
        lambda: pygame.draw.line(screen, COLORS["ink"], (795, 272), (795, 355), 8),
        lambda: pygame.draw.line(screen, COLORS["ink"], (795, 290), (750, 330), 8),
        lambda: pygame.draw.line(screen, COLORS["ink"], (795, 290), (840, 330), 8),
        lambda: pygame.draw.line(screen, COLORS["ink"], (795, 355), (755, 415), 8),
        lambda: pygame.draw.line(screen, COLORS["ink"], (795, 355), (835, 415), 8),
    ]
    for stage in stages[:min(missed, len(stages))]:
        stage()
    if missed >= len(stages):
        draw_text(screen, font, "PERDU", (795, 465), COLORS["red"], center=True)


def draw_game(screen, fonts, game):
    draw_background(screen)
    title, body, small = fonts
    draw_text(screen, title, "HANGMAN", (35, 25), COLORS["white"])
    draw_text(screen, small, f"Niveau : {game['difficulty']}", (40, 88), COLORS["ink"])
    draw_text(screen, small, f"Vies : {game['lives']}", (230, 88), COLORS["red"])
    timer = "infini" if game["limit"] == 0 else f"{max(0, int(game['remaining']))} s"
    draw_text(screen, small, f"Temps : {timer}", (375, 88), COLORS["ink"])
    draw_gallows(screen, game["missed"], body)
    hidden = " ".join(letter if letter in game["found"] else "_" for letter in game["word"])
    draw_text(screen, title, hidden, (320, 535), COLORS["white"], center=True)
    draw_text(screen, small, "Choisis une lettre", (38, 130), COLORS["white"])
    for index, letter in enumerate(LETTERS):
        x = 35 + (index % 9) * 58
        y = 175 + (index // 9) * 48
        rectangle = pygame.Rect(x, y, 45, 36)
        used = letter.lower() in game["used"]
        color = COLORS["muted"] if used else COLORS["cream"]
        pygame.draw.rect(screen, color, rectangle, border_radius=7)
        draw_text(screen, small, letter, rectangle.center, COLORS["ink"], center=True)
    if game["message"]:
        draw_text(screen, small, game["message"], (40, 410), COLORS["red"])


def new_game(words, difficulty):
    settings = DIFFICULTIES[difficulty]
    return {
        "word": random.choice(words), "difficulty": difficulty,
        "lives": settings["lives"], "missed": 0, "limit": settings["time"],
        "remaining": settings["time"], "found": set(), "used": set(),
        "attempts": 0, "message": "", "finished": None,
    }


def letter_at(position):
    for index, letter in enumerate(LETTERS):
        x = 35 + (index % 9) * 58
        y = 175 + (index // 9) * 48
        if pygame.Rect(x, y, 45, 36).collidepoint(position):
            return letter.lower()
    return None


def finish_game(game, won):
    game["finished"] = won
    if won:
        save_score(game["word"], game["attempts"])
        game["message"] = f"Gagne ! {game['word']} en {game['attempts']} tentatives"
    else:
        game["message"] = f"Perdu ! Le mot etait : {game['word']}"


def run(words):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hangman - Jeu du pendu")
    clock = pygame.time.Clock()
    fonts = (pygame.font.Font(None, 54), pygame.font.Font(None, 34), pygame.font.Font(None, 26))
    state = "menu"
    difficulty_index = 1
    game = None
    running = True
    while running:
        elapsed = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = "menu"
            elif state == "menu" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    difficulty_index = (difficulty_index - 1) % 3
                elif event.key == pygame.K_DOWN:
                    difficulty_index = (difficulty_index + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    game = new_game(words, list(DIFFICULTIES)[difficulty_index])
                    state = "game"
                elif event.key == pygame.K_s:
                    state = "scores"
            elif state == "menu" and event.type == pygame.MOUSEBUTTONDOWN:
                if pygame.Rect(330, 345, 300, 55).collidepoint(event.pos):
                    game = new_game(words, list(DIFFICULTIES)[difficulty_index])
                    state = "game"
                elif pygame.Rect(330, 420, 300, 55).collidepoint(event.pos):
                    state = "scores"
                elif pygame.Rect(330, 495, 300, 55).collidepoint(event.pos):
                    running = False
            elif state == "game" and game and game["finished"] is None:
                guess = None
                if event.type == pygame.KEYDOWN and event.unicode.isalpha():
                    guess = event.unicode.lower()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    guess = letter_at(event.pos)
                if guess and guess not in game["used"]:
                    game["used"].add(guess)
                    game["attempts"] += 1
                    if guess in game["word"]:
                        game["found"].add(guess)
                        game["message"] = "Bonne lettre !"
                    else:
                        game["missed"] += 1
                        game["lives"] -= 1
                        game["message"] = "Mauvaise lettre."
                    if all(letter in game["found"] for letter in game["word"]):
                        finish_game(game, True)
                    elif game["lives"] <= 0:
                        finish_game(game, False)
            elif state == "game" and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                state = "menu"
            elif state == "scores" and event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                state = "menu"
        if state == "game" and game and game["finished"] is None and game["limit"]:
            game["remaining"] -= elapsed
            if game["remaining"] <= 0:
                game["lives"] = 0
                finish_game(game, False)
        if state == "menu":
            draw_background(screen)
            draw_text(screen, fonts[0], "HANGMAN", (WIDTH // 2, 100), COLORS["white"], center=True)
            draw_text(screen, fonts[2], "Un pendu graphique", (WIDTH // 2, 155), COLORS["ink"], center=True)
            difficulty = list(DIFFICULTIES)[difficulty_index]
            draw_button(screen, fonts[2], pygame.Rect(330, 245, 300, 55), f"Difficulte : {difficulty}", True)
            draw_button(screen, fonts[2], pygame.Rect(330, 345, 300, 55), "Jouer")
            draw_button(screen, fonts[2], pygame.Rect(330, 420, 300, 55), "Classement")
            draw_button(screen, fonts[2], pygame.Rect(330, 495, 300, 55), "Quitter")
        elif state == "game":
            draw_game(screen, fonts, game)
            if game["finished"] is not None:
                draw_button(screen, fonts[2], pygame.Rect(40, 575, 230, 45), "Entree : menu", True)
        else:
            draw_background(screen)
            draw_text(screen, fonts[0], "CLASSEMENT", (WIDTH // 2, 90), COLORS["white"], center=True)
            scores = read_scores()
            if not scores:
                draw_text(screen, fonts[2], "Aucun score pour le moment", (WIDTH // 2, 180), COLORS["ink"], center=True)
            for index, (attempts, word, score_date) in enumerate(scores):
                text = f"{index + 1}. {attempts} tentatives - {word} - {score_date}"
                draw_text(screen, fonts[2], text, (WIDTH // 2, 165 + index * 35), COLORS["ink"], center=True)
            draw_text(screen, fonts[2], "Entree ou Echap : retour au menu", (WIDTH // 2, 570), COLORS["white"], center=True)
        pygame.display.flip()
    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Jeu du pendu graphique avec Pygame")
    parser.add_argument("word_file", help="Fichier contenant un mot par ligne.")
    args = parser.parse_args()
    try:
        run(load_words(args.word_file))
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()
