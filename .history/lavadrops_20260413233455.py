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

# 전역 변수로 개발자 모드 상태 관리
dev_mode = False

# 기본 해상도 기준점
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
MAX_SLOW_GAUGE = 135  # 기존 90에서 50% 증가
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
ORANGE = (255, 165, 0) # 파티클 효과 기본 색상
GRAY   = (40,  40,  40)
CYAN   = (0,   255, 255) 
GREEN  = (0,   255, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Lava Drops - Dev Edition")
clock = pygame.time.Clock()

font = get_korean_font(36)
font_big = get_korean_font(72)
font_small = get_korean_font(28) 

# 레벨별로 레이저 스폰 간격(interval)과 지속시간(duration)을 개별 설정
LEVELS = [
    {"min_speed": 3, "max_speed": 5,  "spawn": 40, "label": "Lv.1",   "laser_interval": 240, "laser_duration": 300},
    {"min_speed": 5, "max_speed": 8,  "spawn": 25, "label": "Lv.2",   "laser_interval": 180, "laser_duration": 240},
    {"min_speed": 7, "max_speed": 12, "spawn": 15, "label": "Lv.3",   "laser_interval": 120, "laser_duration": 180},
    {"min_speed": 9, "max_speed": 14, "spawn": 10, "label": "Lv.4",   "laser_interval": 90,  "laser_duration": 120},
    {"min_speed": 10,"max_speed": 16, "spawn": 8,  "label": "Lv.Max", "laser_interval": 60,  "laser_duration": 60},
]

PLAYER_W, PLAYER_H = 40, 40
ENEMY_W,  ENEMY_H  = 32, 32  # 용암 이미지 크기(32x32)에 맞춰 30에서 32로 변경

# --- 용암 이미지 로딩 (10001.png ~ 10045.png) ---
lava_images = []
for i in range(1, 46):
    filename = f"{10000 + i}.png"
    try:
        # 이미지를 불러오고 투명도를 처리
        img = pygame.image.load(filename).convert_alpha()
        # 혹시 몰라서 크기를 32x32로 확실히 스케일링
        img = pygame.transform.scale(img, (ENEMY_W, ENEMY_H))
        lava_images.append(img)
    except Exception as e:
        # 파일이 없거나 불러오기 실패할 경우 무시 (나중에 빨간 네모로 대체됨)
        pass

# --- 메인 메뉴 화면 ---
def main_menu():
    global screen, dev_mode
    input_seq = ""  
    secret_code = "whtjdals"
    
    while True:
        screen.fill(GRAY)
        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        
        title_text = font_big.render("LAVA DROPS", True, RED)
        start_text = font.render("Press SPACE to Start", True, YELLOW)
        quit_text = font.render("Press Q to Quit", True, WHITE)
        
        move_text = font_small.render("이동기 : 상 하 좌 우  or  WASD", True, WHITE)
        dodge_text = font_small.render("시간 감속 : SHIFT", True, CYAN)
        
        screen.blit(title_text, title_text.get_rect(center=(cx, cy - 120)))
        screen.blit(start_text, start_text.get_rect(center=(cx, cy - 20)))
        screen.blit(quit_text, quit_text.get_rect(center=(cx, cy + 30)))
        screen.blit(move_text, move_text.get_rect(center=(cx, cy + 100)))
        screen.blit(dodge_text, dodge_text.get_rect(center=(cx, cy + 140)))

        if dev_mode:
            dev_hint = font_small.render("[DEV MODE ACTIVE]", True, GREEN)
            screen.blit(dev_hint, (10, screen.get_height() - 40))
        
        pygame.display.flip()
        clock.tick(FPS)
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "QUIT"
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN:
                char = e.unicode.lower()
                if char in secret_code:
                    input_seq += char
                    if secret_code in input_seq:
                        dev_mode = True
                        input_seq = "" 
                else:
                    input_seq = ""

                if e.key == pygame.K_SPACE:
                    return "START" 
                if e.key == pygame.K_q:
                    return "QUIT" 

def draw_hud(surface, display_score, level_cfg, lives, current_phase):
    surface.blit(font.render(f"Score: {display_score}", True, WHITE), (10, 10))
    
    phase_text = ""
    if current_phase == 4: phase_text = " [ENDLESS]"
    elif current_phase == 3: phase_text = " [FINAL PHASE]" 
    elif current_phase == 2: phase_text = " [LAST PHASE]"  
    elif current_phase == 1: phase_text = " [MID PHASE]"

    surface.blit(font.render(f"{level_cfg['label']}{phase_text}", True, YELLOW), (10, 40))
    
    if dev_mode:
        dev_txt = font_small.render("DEV", True, GREEN)
        surface.blit(dev_txt, (10, 80))

    lives_text = font.render(f"Lives: {'♥ ' * lives}", True, RED)
    lives_rect = lives_text.get_rect(topright=(surface.get_width() - 20, 10))
    surface.blit(lives_text, lives_rect)

def game_over_screen(display_score):
    global screen
    while True:
        screen.fill(GRAY)
        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        
        go_text = font_big.render("GAME OVER", True, RED)
        score_text = font.render(f"Score: {display_score}", True, WHITE)
        restart_text = font.render("R: Restart   Q: Main Menu", True, WHITE) 
        
        screen.blit(go_text, go_text.get_rect(center=(cx, cy - 60)))
        score_text_rect = score_text.get_rect(center=(cx, cy + 10))
        screen.blit(score_text, score_text_rect)
        screen.blit(restart_text, restart_text.get_rect(center=(cx, cy + 60)))
        pygame.display.flip()
        clock.tick(FPS)  

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "QUIT"
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return "RESTART"
                if e.key == pygame.K_q: return "MENU"

def main():
    global screen, dev_mode
    player_x = float(screen.get_width() // 2 - PLAYER_W // 2)
    player_y = float(screen.get_height() - 60)
    player = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
    
    enemies = []
    particles = [] # 불꽃 파티클 리스트
    score = 0.0 
    lives = 3
    level_idx = 0
    level_cfg = LEVELS[level_idx]
    invincible = 0
    last_phase = 0 

    v_spawn_timer = 0.0
    h_spawn_timer = 0.0
    b_spawn_timer = 0.0 

    lasers = []
    laser_spawn_timer = 0.0

    slow_gauge = float(MAX_SLOW_GAUGE)
    is_slow_overheated = False

    shake_timer = 0
    shake_magnitude = 0

    while True:
        clock.tick(FPS)
        sw, sh = screen.get_width(), screen.get_height()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "QUIT"
            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            if e.type == pygame.KEYDOWN:
                if dev_mode and e.key == pygame.K_1:
                    score += 20

        display_score = int(score) 
        width_ratio = max(0.1, sw / DEFAULT_WIDTH)
        height_ratio = max(0.1, sh / DEFAULT_HEIGHT)

        level_idx = min(display_score // SCORE_PER_LEVEL, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        current_phase = 0
        if display_score >= PHASE_ENDLESS_THRESHOLD: current_phase = 4
        elif display_score >= PHASE_LAST_THRESHOLD: current_phase = 3
        elif display_score >= PHASE_LATE_THRESHOLD: current_phase = 2
        elif display_score >= PHASE_MID_THRESHOLD: current_phase = 1

        if current_phase > last_phase:
            last_phase = current_phase
            enemies.clear() 
            lasers.clear()  
            particles.clear() 
            shake_timer = 60 
            shake_magnitude = 30 

        is_phase_mid = current_phase >= 1
        is_phase_late = current_phase >= 2
        is_phase_last = current_phase >= 3
        is_phase_endless = current_phase >= 4

        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or pygame.mouse.get_pressed()[2]
        is_slow_active = False
        
        if shift_held and not is_slow_overheated and slow_gauge > 0:
            is_slow_active = True
            slow_gauge -= SLOW_CONSUME_RATE
            if slow_gauge <= 0:
                slow_gauge = 0
                is_slow_overheated = True
        else:
            slow_gauge = min(MAX_SLOW_GAUGE, slow_gauge + SLOW_RECHARGE_RATE)
            if is_slow_overheated and slow_gauge >= MAX_SLOW_GAUGE:
                is_slow_overheated = False
                
        time_mult = SLOW_TIME_MULTIPLIER if is_slow_active else 1.0
        
        # 플레이어 이동
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

        endless_speed_bonus = (display_score - PHASE_ENDLESS_THRESHOLD) * 0.05 if is_phase_endless else 0

        # 스폰 로직
        if shake_timer <= 0:
            v_spawn_timer += time_mult
            base_v_spawn = level_cfg["spawn"]
            if is_phase_last: base_v_spawn *= 4 
            elif is_phase_late: base_v_spawn *= 2 
            target_v_spawn = max(1, int(base_v_spawn / width_ratio))
            
            if v_spawn_timer >= target_v_spawn:
                v_spawn_timer = 0
                x = random.randint(0, sw - ENEMY_W)
                speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus)
                if is_phase_late: speed *= 0.5
                img = random.choice(lava_images) if lava_images else None
                enemies.append({"rect": pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H), "exact_x": float(x), "exact_y": float(-ENEMY_H), "speed_x": 0, "speed_y": speed, "score_value": 1.0 / width_ratio, "image": img})

            if is_phase_late:
                h_spawn_timer += time_mult
                target_h_spawn = max(1, int(level_cfg["spawn"] * 2 / height_ratio))
                if h_spawn_timer >= target_h_spawn:
                    h_spawn_timer = 0
                    y = random.randint(0, sh - ENEMY_H)
                    speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus) * 0.7
                    img = random.choice(lava_images) if lava_images else None
                    if random.choice([True, False]):
                        enemies.append({"rect": pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H), "exact_x": float(-ENEMY_W), "exact_y": float(y), "speed_x": speed, "speed_y": 0, "score_value": 1.0 / height_ratio, "image": img})
                    else:
                        enemies.append({"rect": pygame.Rect(sw, y, ENEMY_W, ENEMY_H), "exact_x": float(sw), "exact_y": float(y), "speed_x": -speed, "speed_y": 0, "score_value": 1.0 / height_ratio, "image": img})

            if is_phase_last:
                b_spawn_timer += time_mult
                target_b_spawn = max(1, int(level_cfg["spawn"] * 2 / width_ratio))
                if b_spawn_timer >= target_b_spawn:
                    b_spawn_timer = 0
                    x = random.randint(0, sw - ENEMY_W)
                    speed = (random.randint(level_cfg["min_speed"], level_cfg["max_speed"]) + endless_speed_bonus) * 0.6
                    img = random.choice(lava_images) if lava_images else None
                    enemies.append({"rect": pygame.Rect(x, sh, ENEMY_W, ENEMY_H), "exact_x": float(x), "exact_y": float(sh), "speed_x": 0, "speed_y": -speed, "score_value": 1.0 / width_ratio, "image": img})

            if is_phase_mid:
                laser_spawn_timer += time_mult
                if laser_spawn_timer >= level_cfg["laser_interval"] and len(lasers) < MAX_ACTIVE_LASERS:
                    laser_spawn_timer = 0
                    if random.choice([True, False]):
                        ly = random.randint(0, sh - LASER_THICKNESS)
                        lasers.append({"state": "WARNING", "rect": pygame.Rect(-500, ly, 3000, LASER_THICKNESS), "timer": LASER_WARNING_DURATION, "duration": level_cfg["laser_duration"], "origin": random.choice(["left", "right"])})
                    else:
                        lx = random.randint(0, sw - LASER_THICKNESS)
                        lasers.append({"state": "WARNING", "rect": pygame.Rect(lx, -500, LASER_THICKNESS, 3000), "timer": LASER_WARNING_DURATION, "duration": level_cfg["laser_duration"], "origin": random.choice(["top", "bottom"])})

        # 적 이동
        for enemy in enemies:
            enemy["exact_x"] += enemy["speed_x"] * time_mult
            enemy["exact_y"] += enemy["speed_y"] * time_mult
            enemy["rect"].topleft = (int(enemy["exact_x"]), int(enemy["exact_y"]))

        # 레이저 갱신 및 파티클(불꽃) 생성
        updated_lasers = []
        for laser in lasers:
            laser["timer"] -= time_mult
            if laser["state"] == "WARNING" and laser["timer"] <= 0:
                laser["state"] = "ACTIVE"
                laser["timer"] = laser["duration"]
            
            # --- 레이저가 정해진 한쪽 벽에서 불꽃이 터지는 효과 ---
            if laser["state"] == "ACTIVE":
                r = laser["rect"]
                is_horizontal = r.width > r.height
                origin = laser.get("origin", "left") 
                
                # 파티클 2~4개 생성
                for _ in range(random.randint(2, 4)): 
                    if is_horizontal:
                        if origin == "left":
                            px = 0
                            py = random.uniform(r.top, r.bottom)
                            pvx = random.uniform(3, 8)       
                            pvy = random.uniform(-2.5, 2.5)  
                        else: # origin == "right"
                            px = sw
                            py = random.uniform(r.top, r.bottom)
                            pvx = random.uniform(-8, -3)     
                            pvy = random.uniform(-2.5, 2.5)
                    else:
                        if origin == "top":
                            py = 0
                            px = random.uniform(r.left, r.right)
                            pvy = random.uniform(3, 8)       
                            pvx = random.uniform(-2.5, 2.5)
                        else: # origin == "bottom"
                            py = sh
                            px = random.uniform(r.left, r.right)
                            pvy = random.uniform(-8, -3)     
                            pvx = random.uniform(-2.5, 2.5)

                    particles.append({
                        "exact_x": px, "exact_y": py,
                        "speed_x": pvx, "speed_y": pvy,
                        "life": random.randint(15, 30),
                        "start_life": 0 
                    })
                    particles[-1]["start_life"] = particles[-1]["life"]

            if laser["timer"] > 0: 
                updated_lasers.append(laser)
        lasers = updated_lasers
        
        # --- 파티클(점) 이동 및 수명 갱신 ---
        active_particles = []
        for p in particles:
            p["exact_x"] += p["speed_x"] * time_mult
            p["exact_y"] += p["speed_y"] * time_mult
            p["life"] -= 1.0 * time_mult
            if p["life"] > 0:
                active_particles.append(p)
        particles = active_particles

        if invincible > 0: invincible -= 1
        elif shake_timer <= 0:
            collision = any(player.colliderect(e["rect"]) for e in enemies) or \
                        any(l["state"] == "ACTIVE" and player.colliderect(l["rect"]) for l in lasers)
            if collision:
                lives -= 1; invincible = INVINCIBLE_FRAMES
                enemies.clear(); lasers.clear(); particles.clear() 
                slow_gauge = float(MAX_SLOW_GAUGE); is_slow_overheated = False
                if lives <= 0: return game_over_screen(display_score)

        # 화면 밖 적 제거 및 점수 획득
        survived = []
        for e in enemies:
            if 0 <= e["rect"].x <= sw and -ENEMY_H <= e["rect"].y <= sh: survived.append(e)
            else: score += e["score_value"]
        enemies = survived

        canvas = pygame.Surface((sw, sh)); canvas.fill(GRAY)
        
        # --- 그리기 로직 ---
        for l in lasers:
            if l["state"] == "WARNING":
                blink_color = RED if (int(l["timer"]) // 5) % 2 == 0 else YELLOW
                pygame.draw.rect(canvas, blink_color, l["rect"], 3)
            else: 
                pygame.draw.rect(canvas, RED, l["rect"])
        
        # --- 크고 투명한 불꽃(파티클) 그리기 ---
        particle_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        particle_surf.fill((0, 0, 0, 0)) 

        for p in particles:
            life_ratio = p["life"] / p["start_life"]
            base_color = random.choice([RED, ORANGE])
            color_with_alpha = (*base_color, 150) 
            
            size = max(1, int(36 * life_ratio)) 
            offset = size // 2
            pygame.draw.rect(particle_surf, color_with_alpha, (int(p["exact_x"]) - offset, int(p["exact_y"]) - offset, size, size))
        
        canvas.blit(particle_surf, (0, 0))
        
        if (invincible // 10) % 2 == 0: pygame.draw.rect(canvas, BLUE, player)
        
        if shift_held or slow_gauge < MAX_SLOW_GAUGE or is_slow_overheated:
            g_color = CYAN if not is_slow_overheated else (255, 128, 0)
            g_rect = pygame.Rect(player.centerx-40, player.centery-40, 80, 80)
            pygame.draw.arc(canvas, WHITE, g_rect, -math.pi/2, 3*math.pi/2, 2)
            pygame.draw.arc(canvas, g_color, g_rect, -math.pi/2, -math.pi/2 + (slow_gauge/MAX_SLOW_GAUGE)*(2*math.pi), 6)

        # --- 장애물(적) 그리기 ---
        for e in enemies:
            if e.get("image"):
                # 불러온 용암 이미지가 있으면 그 이미지를 그립니다.
                canvas.blit(e["image"], e["rect"].topleft)
            else:
                # 이미지가 없을 경우를 대비해 예전처럼 빨간 네모를 그립니다.
                pygame.draw.rect(canvas, RED, e["rect"])
                
        if is_slow_active:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA); overlay.fill((0, 100, 200, 40))
            canvas.blit(overlay, (0, 0))

        draw_hud(canvas, int(score), level_cfg, lives, current_phase)
        if shake_timer > 0:
            screen.fill(BLACK)
            screen.blit(canvas, (random.randint(-int(shake_magnitude), int(shake_magnitude)), random.randint(-int(shake_magnitude), int(shake_magnitude))))
            shake_timer -= 1; shake_magnitude = max(0, shake_magnitude - 0.5)
        else: screen.blit(canvas, (0, 0))
        pygame.display.flip()

if __name__ == "__main__":
    state = "MENU" 
    while True:
        if state == "MENU":
            action = main_menu()
            if action == "QUIT": break 
            state = "PLAY" 
        elif state == "PLAY":
            action = main()
            if action == "QUIT": break 
            state = "MENU" if action == "MENU" else "PLAY"
    pygame.quit()