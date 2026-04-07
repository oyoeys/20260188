import pygame
import random
import sys
import math

pygame.init()

def get_korean_font(size):
    candidates = ["malgungothic", "applegothic", "nanumgothic", "notosanscjk"]
    for name in candidates:
        font = pygame.font.SysFont(name, size)
        if font.get_ascent() > 0:
            return font
    return pygame.font.SysFont(None, size)

# 기본 해상도 기준점
DEFAULT_WIDTH, DEFAULT_HEIGHT = 800, 600
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
FPS = 60

# --- 게임 상수 ---
PLAYER_SPEED = 5
INVINCIBLE_FRAMES = 90
SCORE_PER_LEVEL = 20

# --- 레이저 설정 ---
LASER_SCORE_THRESHOLD = 50
LASER_WARNING_DURATION = 60
LASER_ACTIVE_DURATION = 10
MAX_ACTIVE_LASERS = 3
LASER_THICKNESS = 30        
LASER_SPAWN_INTERVAL = 180

# --- 실드 게이지 설정 ---
MAX_SHIELD_GAUGE = 180
SHIELD_CONSUME_RATE = 1
SHIELD_RECHARGE_RATE = 0.5

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
GRAY   = (40,  40,  40)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Lava Drops")
clock = pygame.time.Clock()
font = get_korean_font(36)
font_big = get_korean_font(72)

LEVELS = [
    {"min_speed": 3, "max_speed": 5,  "spawn": 40, "label": "Lv.1"},
    {"min_speed": 5, "max_speed": 8,  "spawn": 25, "label": "Lv.2"},
    {"min_speed": 7, "max_speed": 12, "spawn": 15, "label": "Lv.3"},
]

PLAYER_W, PLAYER_H = 40, 40
ENEMY_W,  ENEMY_H  = 30, 30

# --- 메인 메뉴 화면 ---
def main_menu():
    global screen
    screen.fill(GRAY)
    
    cx = screen.get_width() // 2
    cy = screen.get_height() // 2
    
    title_text = font_big.render("LAVA DROPS", True, RED)
    start_text = font.render("Press SPACE to Start", True, YELLOW)
    quit_text = font.render("Press Q to Quit", True, WHITE)
    
    screen.blit(title_text, title_text.get_rect(center=(cx, cy - 60)))
    screen.blit(start_text, start_text.get_rect(center=(cx, cy + 30)))
    screen.blit(quit_text, quit_text.get_rect(center=(cx, cy + 80)))
    
    pygame.display.flip()
    
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "QUIT"
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
                return main_menu() 
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return "START" 
                if e.key == pygame.K_q:
                    return "QUIT" 

def draw_hud(surface, display_score, level_cfg, lives, current_phase):
    surface.blit(font.render(f"Score: {display_score}", True, WHITE), (10, 10))
    
    phase_text = ""
    if current_phase == 4:
        phase_text = " [ENDLESS]"
    elif current_phase == 3:
        phase_text = " [LAST PHASE]"
    elif current_phase == 2:
        phase_text = " [LATE PHASE]"
    elif current_phase == 1:
        phase_text = " [MID PHASE]"

    surface.blit(font.render(f"{level_cfg['label']}{phase_text}", True, YELLOW), (10, 40))
    
    lives_text = font.render(f"Lives: {'♥ ' * lives}", True, RED)
    lives_rect = lives_text.get_rect(topright=(surface.get_width() - 20, 10))
    surface.blit(lives_text, lives_rect)

def game_over_screen(display_score):
    global screen
    screen.fill(GRAY)
    
    cx = screen.get_width() // 2
    cy = screen.get_height() // 2
    
    go_text = font_big.render("GAME OVER", True, RED)
    score_text = font.render(f"Score: {display_score}", True, WHITE)
    # 텍스트 변경: Q를 누르면 메인 메뉴로
    restart_text = font.render("R: Restart   Q: Main Menu", True, WHITE) 
    
    screen.blit(go_text, go_text.get_rect(center=(cx, cy - 60)))
    screen.blit(score_text, score_text.get_rect(center=(cx, cy + 10)))
    screen.blit(restart_text, restart_text.get_rect(center=(cx, cy + 60)))
    pygame.display.flip()
    
    while True:
        clock.tick(FPS)  
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "QUIT"
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
                return game_over_screen(display_score)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return "RESTART"
                if e.key == pygame.K_q: return "MENU" # Q 누르면 메뉴 상태로 반환

def main():
    global screen
    player_x = float(screen.get_width() // 2 - PLAYER_W // 2)
    player_y = float(screen.get_height() - 60)
    player = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
    
    enemies = []
    score = 0.0 
    lives = 3
    level_idx = 0
    level_cfg = LEVELS[level_idx]
    invincible = 0
    last_phase = 0 

    v_spawn_timer = 0
    h_spawn_timer = 0
    b_spawn_timer = 0 

    lasers = []
    laser_spawn_timer = 0

    shield_gauge = float(MAX_SHIELD_GAUGE)
    is_shield_overheated = False

    shake_timer = 0
    shake_magnitude = 0

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "QUIT"
            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)

        sw, sh = screen.get_width(), screen.get_height()
        display_score = int(score) 

        width_ratio = max(0.1, sw / DEFAULT_WIDTH)
        height_ratio = max(0.1, sh / DEFAULT_HEIGHT)

        level_idx = min(display_score // SCORE_PER_LEVEL, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        current_phase = 0
        if display_score >= PHASE_ENDLESS_THRESHOLD:
            current_phase = 4
        elif display_score >= PHASE_LAST_THRESHOLD:
            current_phase = 3
        elif display_score >= PHASE_LATE_THRESHOLD:
            current_phase = 2
        elif display_score >= PHASE_MID_THRESHOLD:
            current_phase = 1

        if current_phase > last_phase:
            last_phase = current_phase
            enemies.clear() 
            lasers.clear()  
            shake_timer = 60 
            shake_magnitude = 30 

        is_phase_mid = current_phase >= 1
        is_phase_late = current_phase >= 2
        is_phase_last = current_phase >= 3
        is_phase_endless = current_phase >= 4

        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        mouse_left = mouse_pressed[0]
        mouse_right = mouse_pressed[2]

        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or mouse_right
        is_shield_active = False
        
        if shift_held and not is_shield_overheated and shield_gauge > 0:
            is_shield_active = True
            shield_gauge -= SHIELD_CONSUME_RATE
            if shield_gauge <= 0:
                shield_gauge = 0
                is_shield_overheated = True
        else:
            shield_gauge = min(MAX_SHIELD_GAUGE, shield_gauge + SHIELD_RECHARGE_RATE)
            if is_shield_overheated and shield_gauge >= MAX_SHIELD_GAUGE:
                is_shield_overheated = False
        
        if mouse_left:
            mx, my = pygame.mouse.get_pos()
            px_center = player_x + PLAYER_W / 2
            py_center = player_y + PLAYER_H / 2
            dx = mx - px_center
            dy = my - py_center
            dist = math.hypot(dx, dy)
            
            if dist > PLAYER_SPEED:
                player_x += (dx / dist) * PLAYER_SPEED
                player_y += (dy / dist) * PLAYER_SPEED
            else:
                player_x = mx - PLAYER_W / 2
                player_y = my - PLAYER_H / 2
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:  player_x -= PLAYER_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: player_x += PLAYER_SPEED
            if keys[pygame.K_UP] or keys[pygame.K_w]:    player_y -= PLAYER_SPEED
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:  player_y += PLAYER_SPEED

        player_x = max(0, min(sw - PLAYER_W, player_x))
        player_y = max(0, min(sh - PLAYER_H, player_y))

        player.x = int(player_x)
        player.y = int(player_y)

        endless_speed_bonus = (display_score - PHASE_ENDLESS_THRESHOLD) * 0.05 if is_phase_endless else 0

        if shake_timer <= 0:
            v_spawn_timer += 1
            base_v_spawn = level_cfg["spawn"]
            if is_phase_last:
                base_v_spawn *= 4 
            elif is_phase_late:
                base_v_spawn *= 2 
                
            target_v_spawn = max(1, int(base_v_spawn / width_ratio))
            
            if v_spawn_timer >= target_v_spawn:
                v_spawn_timer = 0
                x = random.randint(0, sw - ENEMY_W)
                speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus 
                if is_phase_late: speed = max(1, int(speed * 0.5))
                
                enemies.append({
                    "rect": pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H), 
                    "speed_x": 0, "speed_y": speed,
                    "score_value": 1.0 / width_ratio 
                })

            if is_phase_late:
                h_spawn_timer += 1
                base_h_spawn = level_cfg["spawn"] * 2
                target_h_spawn = max(1, int(base_h_spawn / height_ratio))
                
                if h_spawn_timer >= target_h_spawn:
                    h_spawn_timer = 0
                    y = random.randint(0, sh - ENEMY_H)
                    speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus 
                    speed = max(1, int(speed * 0.7)) 
                    
                    if random.choice([True, False]):
                        enemies.append({"rect": pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H), "speed_x": speed, "speed_y": 0, "score_value": 1.0 / height_ratio})
                    else:
                        enemies.append({"rect": pygame.Rect(sw, y, ENEMY_W, ENEMY_H), "speed_x": -speed, "speed_y": 0, "score_value": 1.0 / height_ratio})

            if is_phase_last:
                b_spawn_timer += 1
                base_b_spawn = level_cfg["spawn"] * 2
                target_b_spawn = max(1, int(base_b_spawn / width_ratio))
                
                if b_spawn_timer >= target_b_spawn:
                    b_spawn_timer = 0
                    x = random.randint(0, sw - ENEMY_W)
                    speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus 
                    speed = max(1, int(speed * 0.6))
                    
                    enemies.append({"rect": pygame.Rect(x, sh, ENEMY_W, ENEMY_H), "speed_x": 0, "speed_y": -speed, "score_value": 1.0 / width_ratio})

            if is_phase_mid:
                laser_spawn_timer += 1
                if laser_spawn_timer >= LASER_SPAWN_INTERVAL and len(lasers) < MAX_ACTIVE_LASERS:
                    laser_spawn_timer = 0
                    is_horizontal = random.choice([True, False])
                    if is_horizontal:
                        laser_y = random.randint(0, sh - LASER_THICKNESS)
                        laser_rect = pygame.Rect(-500, laser_y, 3000, LASER_THICKNESS)
                    else:
                        laser_x = random.randint(0, sw - LASER_THICKNESS)
                        laser_rect = pygame.Rect(laser_x, -500, LASER_THICKNESS, 3000)

                    lasers.append({"state": "WARNING", "rect": laser_rect, "timer": LASER_WARNING_DURATION})

        for enemy in enemies:
            enemy["rect"].x += enemy["speed_x"]
            enemy["rect"].y += enemy["speed_y"]

        updated_lasers = []
        for laser in lasers:
            laser["timer"] -= 1
            if laser["state"] == "WARNING":
                if laser["timer"] <= 0:
                    laser["state"] = "ACTIVE"
                    laser["timer"] = LASER_ACTIVE_DURATION
                updated_lasers.append(laser)
            elif laser["state"] == "ACTIVE":
                if laser["timer"] > 0:
                    updated_lasers.append(laser)
        lasers = updated_lasers

        if invincible > 0:
            invincible -= 1
        elif not is_shield_active and shake_timer <= 0: 
            for enemy in enemies:
                if player.colliderect(enemy["rect"]):
                    lives -= 1
                    invincible = INVINCIBLE_FRAMES
                    enemies.clear()
                    lasers.clear()
                    shield_gauge = float(MAX_SHIELD_GAUGE)
                    is_shield_overheated = False
                    if lives <= 0:
                        # 게임 오버 화면에서 누른 버튼(상태)를 그대로 바깥으로 전달
                        return game_over_screen(display_score) 
                    break
            
            if invincible == 0:
                for laser in lasers:
                    if laser["state"] == "ACTIVE" and player.colliderect(laser["rect"]):
                        lives -= 1
                        invincible = INVINCIBLE_FRAMES
                        enemies.clear()
                        lasers.clear()
                        shield_gauge = float(MAX_SHIELD_GAUGE)
                        is_shield_overheated = False
                        if lives <= 0:
                            return game_over_screen(display_score)
                        break

        survived = []
        for enemy in enemies:
            is_out_of_bounds = False
            
            if enemy["speed_y"] > 0 and enemy["rect"].top >= sh: 
                is_out_of_bounds = True
            elif enemy["speed_y"] < 0 and enemy["rect"].bottom <= 0: 
                is_out_of_bounds = True
            elif enemy["speed_x"] > 0 and enemy["rect"].left >= sw: 
                is_out_of_bounds = True
            elif enemy["speed_x"] < 0 and enemy["rect"].right <= 0: 
                is_out_of_bounds = True

            if not is_out_of_bounds:
                survived.append(enemy) 
            else:
                score += enemy["score_value"] 
                
        enemies = survived 

        canvas = pygame.Surface((sw, sh))
        canvas.fill(GRAY)

        for laser in lasers:
            if laser["state"] == "WARNING":
                pygame.draw.rect(canvas, RED, laser["rect"], 3)
                warn_text = font.render('!', True, RED)
                text_rect = warn_text.get_rect(center=laser["rect"].center)
                canvas.blit(warn_text, text_rect)
            elif laser["state"] == "ACTIVE":
                pygame.draw.rect(canvas, RED, laser["rect"])

        if is_shield_active:
            pygame.draw.rect(canvas, YELLOW, player) 
        else:
            blink = (invincible // 10) % 2 == 0
            if blink:
                pygame.draw.rect(canvas, BLUE, player) 

        if shift_held or shield_gauge < MAX_SHIELD_GAUGE or is_shield_overheated:
            gauge_radius = 40 
            gauge_center = (player.centerx, player.centery) 
            gauge_color = YELLOW if not is_shield_overheated else (255, 128, 0)
            gauge_ratio = shield_gauge / MAX_SHIELD_GAUGE
            
            start_angle = -math.pi / 2
            sweep_angle = gauge_ratio * (2 * math.pi)
            end_angle = start_angle + sweep_angle
            
            gauge_rect = pygame.Rect(gauge_center[0] - gauge_radius, gauge_center[1] - gauge_radius, gauge_radius * 2, gauge_radius * 2)
            
            pygame.draw.arc(canvas, WHITE, gauge_rect, -math.pi / 2, 3 * math.pi / 2, 2)
            pygame.draw.arc(canvas, gauge_color, gauge_rect, start_angle, end_angle, 6)

        for enemy in enemies:
            pygame.draw.rect(canvas, RED, enemy["rect"])

        draw_hud(canvas, display_score, level_cfg, lives, current_phase)

        if shake_timer > 0:
            dx = random.randint(-int(shake_magnitude), int(shake_magnitude))
            dy = random.randint(-int(shake_magnitude), int(shake_magnitude))
            
            screen.fill(BLACK) 
            screen.blit(canvas, (dx, dy))
            
            shake_timer -= 1
            shake_magnitude = max(0, shake_magnitude - 0.5) 
        else:
            screen.blit(canvas, (0, 0)) 

        pygame.display.flip()

# --- 실행 흐름 제어 (상태 머신) ---
if __name__ == "__main__":
    state = "MENU" # 초기 상태는 메인 메뉴
    
    while True:
        if state == "MENU":
            action = main_menu()
            if action == "QUIT": 
                break # Q를 누르거나 X버튼을 누르면 루프 탈출 (게임 종료)
            elif action == "START": 
                state = "PLAY" # 스페이스를 누르면 게임 시작 상태로 전환
                
        elif state == "PLAY":
            action = main()
            if action == "QUIT": 
                break 
            elif action == "MENU": 
                state = "MENU" # 게임오버 창에서 Q를 누르면 다시 메뉴 상태로!
            elif action == "RESTART": 
                state = "PLAY" # 게임오버 창에서 R을 누르면 다시 게임 시작
                
    pygame.quit()
    sys.exit()