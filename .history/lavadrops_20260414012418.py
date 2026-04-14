import pygame
import random
import sys
import math
import os

pygame.init()

def get_korean_font(size):
    candidates = ["malgungothic", "applegothic", "nanumgothic", "notosanscjk"]
    for name in candidates:
        font = pygame.font.SysFont(name, size)
        if font.get_ascent() > 0:
            return font
    return pygame.font.SysFont(None, size)

# 전역 변수
dev_mode = False
DEFAULT_WIDTH, DEFAULT_HEIGHT = 800, 600
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
FPS = 60

# --- 게임 상수 ---
PLAYER_SPEED = 5
INVINCIBLE_FRAMES = 90
SCORE_PER_LEVEL = 20

# --- 레이저 설정 ---
LASER_WARNING_DURATION = 60    
MAX_ACTIVE_LASERS = 3
LASER_THICKNESS = 30        

# --- 슬로우 게이지 설정 ---
MAX_SLOW_GAUGE = 180  
SLOW_CONSUME_RATE = 1
SLOW_RECHARGE_RATE = 0.5
SLOW_TIME_MULTIPLIER = 0.3 

# --- 페이즈 구간 설정 ---
PHASE_MID_THRESHOLD = 50      
PHASE_LATE_THRESHOLD = 100    
PHASE_LAST_THRESHOLD = 200    
PHASE_ENDLESS_THRESHOLD = 400 

WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
BLUE   = (50,  120, 220)
RED    = (220, 50,  50)
YELLOW = (240, 200, 0)
ORANGE = (255, 165, 0) 
GRAY   = (40,  40,  40)
CYAN   = (0,   255, 255) 
GREEN  = (0,   255, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Lava Drops - Ice Edition")
clock = pygame.time.Clock()

font = get_korean_font(36)
font_big = get_korean_font(72)
font_small = get_korean_font(28) 

LEVELS = [
    {"min_speed": 3, "max_speed": 5,  "spawn": 40, "label": "Lv.1",   "laser_interval": 240, "laser_duration": 300},
    {"min_speed": 5, "max_speed": 8,  "spawn": 25, "label": "Lv.2",   "laser_interval": 180, "laser_duration": 240},
    {"min_speed": 7, "max_speed": 12, "spawn": 15, "label": "Lv.3",   "laser_interval": 120, "laser_duration": 180},
    {"min_speed": 9, "max_speed": 14, "spawn": 10, "label": "Lv.4",   "laser_interval": 90,  "laser_duration": 120},
    {"min_speed": 10,"max_speed": 16, "spawn": 8,  "label": "Lv.Max", "laser_interval": 60,  "laser_duration": 60},
]

PLAYER_W, PLAYER_H = 40, 40
ENEMY_W,  ENEMY_H  = 32, 32  

# --- 캐릭터 이미지 로딩 (경로 문제 해결 버전) ---
player_img = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHARACTER_FILE = os.path.join(BASE_DIR, "ice.jpg")

try:
    img = pygame.image.load(CHARACTER_FILE).convert_alpha()
    player_img = pygame.transform.scale(img, (PLAYER_W, PLAYER_H))
    print(f"✅ 캐릭터 이미지 로딩 성공: {CHARACTER_FILE}")
except Exception as e:
    print(f"❌ 캐릭터 이미지 로딩 실패: {e}")
    print(f"이미지 파일 'ice.jpg'가 '{BASE_DIR}' 폴더 안에 있는지 확인해주세요.")

# --- 용암 이미지 로딩 ---
lava_images = []
LAVA_FOLDER = os.path.join(BASE_DIR, "32x32 Lava Tiles")

if os.path.exists(LAVA_FOLDER):
    for i in range(1, 46):
        filename = os.path.join(LAVA_FOLDER, f"{10000 + i}.png")
        try:
            img = pygame.image.load(filename).convert_alpha()
            img = pygame.transform.scale(img, (ENEMY_W, ENEMY_H))
            lava_images.append(img)
        except: pass
else:
    print(f"⚠️ 용암 폴더를 찾을 수 없습니다: {LAVA_FOLDER}")

def main_menu():
    global screen, dev_mode
    input_seq = ""  
    secret_code = "whtjdals"
    while True:
        screen.fill(GRAY)
        cx, cy = screen.get_width() // 2, screen.get_height() // 2
        title_text = font_big.render("LAVA DROPS", True, RED)
        start_text = font.render("Press SPACE to Start", True, YELLOW)
        quit_text = font.render("Press Q to Quit", True, WHITE)
        screen.blit(title_text, title_text.get_rect(center=(cx, cy - 120)))
        screen.blit(start_text, start_text.get_rect(center=(cx, cy - 20)))
        screen.blit(quit_text, quit_text.get_rect(center=(cx, cy + 30)))
        if dev_mode:
            dev_hint = font_small.render("[DEV MODE ACTIVE]", True, GREEN)
            screen.blit(dev_hint, (10, screen.get_height() - 40))
        pygame.display.flip()
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "QUIT"
            if e.type == pygame.VIDEORESIZE: screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN:
                char = e.unicode.lower()
                if char in secret_code:
                    input_seq += char
                    if secret_code in input_seq: dev_mode = True; input_seq = ""
                else: input_seq = ""
                if e.key == pygame.K_SPACE: return "START"
                if e.key == pygame.K_q: return "QUIT"

def draw_hud(surface, display_score, level_cfg, lives, current_phase):
    surface.blit(font.render(f"Score: {display_score}", True, WHITE), (10, 10))
    phase_text = ["", " [MID]", " [LAST]", " [FINAL]", " [ENDLESS]"][current_phase]
    surface.blit(font.render(f"{level_cfg['label']}{phase_text}", True, YELLOW), (10, 40))
    lives_text = font.render(f"Lives: {'♥ ' * lives}", True, RED)
    surface.blit(lives_text, lives_text.get_rect(topright=(surface.get_width() - 20, 10)))

def game_over_screen(display_score):
    global screen
    while True:
        screen.fill(GRAY)
        cx, cy = screen.get_width() // 2, screen.get_height() // 2
        go_text = font_big.render("GAME OVER", True, RED)
        score_text = font.render(f"Score: {display_score}", True, WHITE)
        restart_text = font.render("R: Restart   Q: Main Menu", True, WHITE)
        screen.blit(go_text, go_text.get_rect(center=(cx, cy - 60)))
        screen.blit(score_text, score_text.get_rect(center=(cx, cy + 10)))
        screen.blit(restart_text, restart_text.get_rect(center=(cx, cy + 60)))
        pygame.display.flip()
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "QUIT"
            if e.type == pygame.VIDEORESIZE: screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return "RESTART"
                if e.key == pygame.K_q: return "MENU"

def main():
    global screen, dev_mode, player_img
    player_x, player_y = float(screen.get_width() // 2 - PLAYER_W // 2), float(screen.get_height() - 60)
    player = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
    enemies, particles, lasers = [], [], []
    score, lives, level_idx, invincible, last_phase = 0.0, 3, 0, 0, 0
    v_timer, h_timer, b_timer, laser_timer = 0.0, 0.0, 0.0, 0.0
    slow_gauge, is_slow_overheated, shake_timer, shake_magnitude = float(MAX_SLOW_GAUGE), False, 0, 0

    while True:
        clock.tick(FPS)
        sw, sh = screen.get_width(), screen.get_height()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "QUIT"
            elif e.type == pygame.VIDEORESIZE: screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN and dev_mode and e.key == pygame.K_1: score += 20

        display_score = int(score)
        w_ratio, h_ratio = max(0.1, sw / DEFAULT_WIDTH), max(0.1, sh / DEFAULT_HEIGHT)
        level_idx = min(display_score // SCORE_PER_LEVEL, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        current_phase = 0
        if display_score >= PHASE_ENDLESS_THRESHOLD: current_phase = 4
        elif display_score >= PHASE_LAST_THRESHOLD: current_phase = 3
        elif display_score >= PHASE_LATE_THRESHOLD: current_phase = 2
        elif display_score >= PHASE_MID_THRESHOLD: current_phase = 1

        if current_phase > last_phase:
            last_phase = current_phase
            enemies.clear(); lasers.clear(); particles.clear()
            shake_timer, shake_magnitude = 60, 30

        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or pygame.mouse.get_pressed()[2]
        is_slow_active = False
        if shift_held and not is_slow_overheated and slow_gauge > 0:
            is_slow_active = True
            slow_gauge -= SLOW_CONSUME_RATE
            if slow_gauge <= 0: is_slow_overheated = True
        else:
            slow_gauge = min(MAX_SLOW_GAUGE, slow_gauge + SLOW_RECHARGE_RATE)
            if is_slow_overheated and slow_gauge >= MAX_SLOW_GAUGE: is_slow_overheated = False
        
        time_mult = SLOW_TIME_MULTIPLIER if is_slow_active else 1.0
        
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx - (player_x + PLAYER_W/2), my - (player_y + PLAYER_H/2)
            dist = math.hypot(dx, dy)
            if dist > PLAYER_SPEED:
                player_x += (dx/dist) * PLAYER_SPEED
                player_y += (dy/dist) * PLAYER_SPEED
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:  player_x -= PLAYER_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: player_x += PLAYER_SPEED
            if keys[pygame.K_UP] or keys[pygame.K_w]:    player_y -= PLAYER_SPEED
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:  player_y += PLAYER_SPEED

        player_x = max(0, min(sw - PLAYER_W, player_x))
        player_y = max(0, min(sh - PLAYER_H, player_y))
        player.topleft = (int(player_x), int(player_y))

        if shake_timer <= 0:
            v_timer += time_mult
            bonus = (display_score - PHASE_ENDLESS_THRESHOLD) * 0.05 if current_phase == 4 else 0
            if v_timer >= max(1, int(level_cfg["spawn"] * (0.25 if current_phase >= 3 else 0.5 if current_phase >= 2 else 1) / w_ratio)):
                v_timer = 0; x = random.randint(0, sw - ENEMY_W); speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + bonus) * (0.5 if current_phase >= 2 else 1)
                enemies.append({"rect": pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H), "exact_x": float(x), "exact_y": float(-ENEMY_H), "speed_x": 0, "speed_y": speed, "score_value": 1.0 / w_ratio, "image": random.choice(lava_images) if lava_images else None})
            if current_phase >= 2:
                h_timer += time_mult
                if h_timer >= max(1, int(level_cfg["spawn"] * 2 / h_ratio)):
                    h_timer = 0; y = random.randint(0, sh - ENEMY_H); speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + bonus) * 0.7
                    if random.choice([True, False]): enemies.append({"rect": pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H), "exact_x": float(-ENEMY_W), "exact_y": float(y), "speed_x": speed, "speed_y": 0, "score_value": 1.0 / h_ratio, "image": random.choice(lava_images) if lava_images else None})
                    else: enemies.append({"rect": pygame.Rect(sw, y, ENEMY_W, ENEMY_H), "exact_x": float(sw), "exact_y": float(y), "speed_x": -speed, "speed_y": 0, "score_value": 1.0 / h_ratio, "image": random.choice(lava_images) if lava_images else None})
            if current_phase >= 3:
                b_timer += time_mult
                if b_timer >= max(1, int(level_cfg["spawn"] * 2 / w_ratio)):
                    b_timer = 0; x = random.randint(0, sw - ENEMY_W); speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + bonus) * 0.6
                    enemies.append({"rect": pygame.Rect(x, sh, ENEMY_W, ENEMY_H), "exact_x": float(x), "exact_y": float(sh), "speed_x": 0, "speed_y": -speed, "score_value": 1.0 / w_ratio, "image": random.choice(lava_images) if lava_images else None})
            if current_phase >= 1:
                laser_timer += time_mult
                if laser_timer >= level_cfg["laser_interval"] and len(lasers) < MAX_ACTIVE_LASERS:
                    laser_timer = 0; laser_img = random.choice(lava_images) if lava_images else None
                    if random.choice([True, False]):
                        ly = random.randint(0, sh - LASER_THICKNESS)
                        lasers.append({"state": "WARNING", "rect": pygame.Rect(-500, ly, 3000, LASER_THICKNESS), "timer": LASER_WARNING_DURATION, "duration": level_cfg["laser_duration"], "origin": random.choice(["left", "right"]), "image": laser_img, "offset": 0.0})
                    else:
                        lx = random.randint(0, sw - LASER_THICKNESS)
                        lasers.append({"state": "WARNING", "rect": pygame.Rect(lx, -500, LASER_THICKNESS, 3000), "timer": LASER_WARNING_DURATION, "duration": level_cfg["laser_duration"], "origin": random.choice(["top", "bottom"]), "image": laser_img, "offset": 0.0})

        for e in enemies:
            e["exact_x"] += e["speed_x"] * time_mult; e["exact_y"] += e["speed_y"] * time_mult
            e["rect"].topleft = (int(e["exact_x"]), int(e["exact_y"]))

        updated_lasers = []
        for l in lasers:
            l["timer"] -= time_mult
            if l["state"] == "WARNING" and l["timer"] <= 0: l["state"] = "ACTIVE"; l["timer"] = l["duration"]
            if l["state"] == "ACTIVE":
                r = l["rect"]; is_horiz = r.width > r.height; origin = l.get("origin", "left")
                flow_speed = 75 * time_mult
                l["offset"] = l.get("offset", 0.0) + (flow_speed if origin in ("left", "top") else -flow_speed)
                for _ in range(random.randint(2, 4)):
                    if is_horiz: px = 0 if origin == "left" else sw; py = random.uniform(r.top, r.bottom); pvx = random.uniform(3, 8) if origin == "left" else random.uniform(-8, -3); pvy = random.uniform(-2.5, 2.5)
                    else: px = random.uniform(r.left, r.right); py = 0 if origin == "top" else sh; pvx = random.uniform(-2.5, 2.5); pvy = random.uniform(3, 8) if origin == "top" else random.uniform(-8, -3)
                    particles.append({"exact_x": px, "exact_y": py, "speed_x": pvx, "speed_y": pvy, "life": random.randint(15, 30), "start_life": 0})
                    particles[-1]["start_life"] = particles[-1]["life"]
            if l["timer"] > 0: updated_lasers.append(l)
        lasers = updated_lasers
        
        active_p = []
        for p in particles:
            p["exact_x"] += p["speed_x"] * time_mult; p["exact_y"] += p["speed_y"] * time_mult; p["life"] -= 1.0 * time_mult
            if p["life"] > 0: active_p.append(p)
        particles = active_p

        if invincible > 0: invincible -= 1
        elif shake_timer <= 0:
            if any(player.colliderect(e["rect"]) for e in enemies) or any(l["state"] == "ACTIVE" and player.colliderect(l["rect"]) for l in lasers):
                lives -= 1; invincible = INVINCIBLE_FRAMES; enemies.clear(); lasers.clear(); particles.clear()
                slow_gauge = float(MAX_SLOW_GAUGE); is_slow_overheated = False
                if lives <= 0: return game_over_screen(display_score)

        survived = []
        for e in enemies:
            if -ENEMY_W <= e["rect"].x <= sw and -ENEMY_H <= e["rect"].y <= sh: survived.append(e)
            else: score += e["score_value"]
        enemies = survived

        canvas = pygame.Surface((sw, sh)); canvas.fill(GRAY)
        for l in lasers:
            if l["state"] == "WARNING":
                pygame.draw.rect(canvas, RED if (int(l["timer"]) // 5) % 2 == 0 else YELLOW, l["rect"], 3)
            else:
                if l.get("image"):
                    is_horiz, img_w, img_h = l["rect"].width > l["rect"].height, l["image"].get_width(), l["image"].get_height()
                    offset = int(l.get("offset", 0))
                    if is_horiz:
                        tile = pygame.transform.scale(l["image"], (img_w, l["rect"].height))
                        for x in range(l["rect"].left + (offset % img_w) - img_w, l["rect"].right, img_w): canvas.blit(tile, (x, l["rect"].top))
                    else:
                        tile = pygame.transform.scale(l["image"], (l["rect"].width, img_h))
                        # ERROR FIX: l["top"] -> l["rect"].top
                        for y in range(l["rect"].top + (offset % img_h) - img_h, l["rect"].bottom, img_h): canvas.blit(tile, (l["rect"].left, y))
                else: pygame.draw.rect(canvas, RED, l["rect"])

        p_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for p in particles:
            size = max(1, int(36 * (p["life"] / p["start_life"])))
            pygame.draw.rect(p_surf, (*random.choice([RED, ORANGE]), 150), (int(p["exact_x"]) - size//2, int(p["exact_y"]) - size//2, size, size))
        canvas.blit(p_surf, (0, 0))

        if not (invincible > 0 and (invincible // 10) % 2 == 1):
            if player_img: canvas.blit(player_img, player.topleft)
            else: pygame.draw.rect(canvas, BLUE, player)

        if shift_held or slow_gauge < MAX_SLOW_GAUGE or is_slow_overheated:
            g_rect = pygame.Rect(player.centerx-40, player.centery-40, 80, 80)
            pygame.draw.arc(canvas, WHITE, g_rect, -math.pi/2, 3*math.pi/2, 2)
            pygame.draw.arc(canvas, CYAN if not is_slow_overheated else ORANGE, g_rect, -math.pi/2, -math.pi/2 + (slow_gauge/MAX_SLOW_GAUGE)*(2*math.pi), 6)

        for e in enemies:
            if e.get("image"): canvas.blit(e["image"], e["rect"].topleft)
            else: pygame.draw.rect(canvas, RED, e["rect"])
        if is_slow_active:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA); overlay.fill((0, 100, 200, 40)); canvas.blit(overlay, (0, 0))

        draw_hud(canvas, int(score), level_cfg, lives, current_phase)
        if shake_timer > 0:
            screen.fill(BLACK); screen.blit(canvas, (random.randint(-int(shake_magnitude), int(shake_magnitude)), random.randint(-int(shake_magnitude), int(shake_magnitude))))
            shake_timer -= 1; shake_magnitude = max(0, shake_magnitude - 0.5)
        else: screen.blit(canvas, (0, 0))
        pygame.display.flip()

if __name__ == "__main__":
    state = "MENU"
    while state != "QUIT":
        if state == "MENU":
            res = main_menu()
            state = "PLAY" if res == "START" else "QUIT"
        elif state == "PLAY":
            res = main()
            state = "MENU" if res == "MENU" else "PLAY" if res == "RESTART" else "QUIT"
    pygame.quit()