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

WIDTH, HEIGHT = 800, 600
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

# --- 페이즈 구간 설정 (기획서 반영 ⭐) ---
PHASE_MID_THRESHOLD = 50      # 중반: 레이저 추가
PHASE_LATE_THRESHOLD = 100    # 후반: 좌우 적 추가
PHASE_LAST_THRESHOLD = 200    # 라스트: 하단 역류 적 추가
PHASE_ENDLESS_THRESHOLD = 400 # 엔드리스: 무한 속도 증가

WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
BLUE   = (50,  120, 220)
RED    = (220, 50,  50)
YELLOW = (240, 200, 0)
GRAY   = (40,  40,  40)

# pygame.RESIZABLE 옵션을 추가하여 화면 크기 조절 허용
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

# 캐릭터를 40x40 정사각형으로 변경
PLAYER_W, PLAYER_H = 40, 40
ENEMY_W,  ENEMY_H  = 30, 30

def draw_hud(score, level_cfg, lives):
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))
    
    # 점수에 따른 페이즈 텍스트 변경
    phase_text = ""
    if score >= PHASE_ENDLESS_THRESHOLD:
        phase_text = " [ENDLESS]"
    elif score >= PHASE_LAST_THRESHOLD:
        phase_text = " [LAST PHASE]"
    elif score >= PHASE_LATE_THRESHOLD:
        phase_text = " [LATE PHASE]"
    elif score >= PHASE_MID_THRESHOLD:
        phase_text = " [MID PHASE]"

    screen.blit(font.render(f"{level_cfg['label']}{phase_text}", True, YELLOW), (10, 40))
    
    # 우측 상단 모서리에 딱 맞게 동적 정렬
    lives_text = font.render(f"Lives: {'♥ ' * lives}", True, RED)
    lives_rect = lives_text.get_rect(topright=(screen.get_width() - 20, 10))
    screen.blit(lives_text, lives_rect)

def game_over_screen(score):
    global screen
    screen.fill(GRAY)
    
    # 창 크기에 상관없이 항상 화면 중앙에 오도록 설정
    cx = screen.get_width() // 2
    cy = screen.get_height() // 2
    
    go_text = font_big.render("GAME OVER", True, RED)
    score_text = font.render(f"Score: {score}", True, WHITE)
    restart_text = font.render("R: Restart   Q: Quit", True, WHITE)
    
    screen.blit(go_text, go_text.get_rect(center=(cx, cy - 60)))
    screen.blit(score_text, score_text.get_rect(center=(cx, cy + 10)))
    screen.blit(restart_text, restart_text.get_rect(center=(cx, cy + 60)))
    pygame.display.flip()
    
    while True:
        clock.tick(FPS)  
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            # 게임 오버 상태에서도 창 크기 조절이 가능하도록 유지
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
                return game_over_screen(score)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return True
                if e.key == pygame.K_q: return False

def main():
    global screen
    player_x = float(screen.get_width() // 2 - PLAYER_W // 2)
    player_y = float(screen.get_height() - 60)
    player = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
    
    enemies = []
    score = 0
    lives = 3
    level_idx = 0
    level_cfg = LEVELS[level_idx]
    invincible = 0

    v_spawn_timer = 0
    h_spawn_timer = 0
    b_spawn_timer = 0 # 하단 역류 스폰 타이머 추가

    lasers = []
    laser_spawn_timer = 0

    shield_gauge = float(MAX_SHIELD_GAUGE)
    is_shield_overheated = False

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            # 창 크기 조절 이벤트 처리
            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)

        sw, sh = screen.get_width(), screen.get_height()

        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        mouse_left = mouse_pressed[0]
        mouse_right = mouse_pressed[2]

        # 회피: 키보드 Shift 또는 마우스 우클릭
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
        
        # 이동: 마우스 좌클릭 시 마우스 방향으로 이동, 아니면 키보드 이동
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

        # 창 크기에 맞게 플레이어 이동 제한
        player_x = max(0, min(sw - PLAYER_W, player_x))
        player_y = max(0, min(sh - PLAYER_H, player_y))

        player.x = int(player_x)
        player.y = int(player_y)

        # --- 기획서 기반 적 스폰 로직 ---
        is_phase_mid = score >= PHASE_MID_THRESHOLD
        is_phase_late = score >= PHASE_LATE_THRESHOLD
        is_phase_last = score >= PHASE_LAST_THRESHOLD
        is_phase_endless = score >= PHASE_ENDLESS_THRESHOLD

        # 엔드리스 구간: 400점을 초과할 때마다 무한 속도 증가 보너스
        endless_speed_bonus = (score - PHASE_ENDLESS_THRESHOLD) * 0.05 if is_phase_endless else 0

        # 1. 상단 스폰 (수직 하강)
        v_spawn_timer += 1
        if is_phase_last:
            target_v_spawn = level_cfg["spawn"] * 4 # 후반보다 2배 더 감소 (초반의 1/4)
        elif is_phase_late:
            target_v_spawn = level_cfg["spawn"] * 2 # 초반의 절반으로 감소
        else:
            target_v_spawn = level_cfg["spawn"]
        
        if v_spawn_timer >= target_v_spawn:
            v_spawn_timer = 0
            x = random.randint(0, sw - ENEMY_W)
            speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"])
            speed += endless_speed_bonus # 엔드리스 보너스
            
            if is_phase_late:
                speed = max(1, int(speed * 0.5))
            
            enemies.append({"rect": pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H), "speed_x": 0, "speed_y": speed})

        # 2. 좌우 스폰 (후반 페이즈 추가)
        if is_phase_late:
            h_spawn_timer += 1
            target_h_spawn = level_cfg["spawn"] * 2
            
            if h_spawn_timer >= target_h_spawn:
                h_spawn_timer = 0
                y = random.randint(0, sh - ENEMY_H)
                speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"])
                speed += endless_speed_bonus # 엔드리스 보너스
                speed = max(1, int(speed * 0.7)) 
                
                if random.choice([True, False]):
                    enemies.append({"rect": pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H), "speed_x": speed, "speed_y": 0})
                else:
                    enemies.append({"rect": pygame.Rect(sw, y, ENEMY_W, ENEMY_H), "speed_x": -speed, "speed_y": 0})

        # 3. 하단 역류 스폰 (라스트 페이즈 추가)
        if is_phase_last:
            b_spawn_timer += 1
            target_b_spawn = level_cfg["spawn"] * 2
            
            if b_spawn_timer >= target_b_spawn:
                b_spawn_timer = 0
                x = random.randint(0, sw - ENEMY_W)
                speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"])
                speed += endless_speed_bonus # 엔드리스 보너스
                speed = max(1, int(speed * 0.6))
                
                # 아래에서 위로(speed_y가 마이너스)
                enemies.append({"rect": pygame.Rect(x, sh, ENEMY_W, ENEMY_H), "speed_x": 0, "speed_y": -speed})

        # --- 레이저 스폰 로직 (중반 페이즈) ---
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

        # 적 위치 업데이트
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

        # 충돌 검사
        if invincible > 0:
            invincible -= 1
        elif not is_shield_active: 
            for enemy in enemies:
                if player.colliderect(enemy["rect"]):
                    lives -= 1
                    invincible = INVINCIBLE_FRAMES
                    enemies.clear()
                    lasers.clear()
                    shield_gauge = float(MAX_SHIELD_GAUGE)
                    is_shield_overheated = False
                    if lives <= 0:
                        if game_over_screen(score):
                            return True
                        return False
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
                            if game_over_screen(score):
                                return True
                            return False
                        break

        # 화면 밖으로 나간 적 점수 처리 (하단 역류 체크 추가)
        survived = []
        for enemy in enemies:
            is_out_of_bounds = False
            
            if enemy["speed_y"] > 0 and enemy["rect"].top >= sh: # 위에서 아래로
                is_out_of_bounds = True
            elif enemy["speed_y"] < 0 and enemy["rect"].bottom <= 0: # 아래에서 위로 (추가됨)
                is_out_of_bounds = True
            elif enemy["speed_x"] > 0 and enemy["rect"].left >= sw: # 왼쪽에서 오른쪽
                is_out_of_bounds = True
            elif enemy["speed_x"] < 0 and enemy["rect"].right <= 0: # 오른쪽에서 왼쪽
                is_out_of_bounds = True

            if not is_out_of_bounds:
                survived.append(enemy)
            else:
                score += 1
        enemies = survived

        level_idx = min(score // SCORE_PER_LEVEL, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        screen.fill(GRAY)

        for laser in lasers:
            if laser["state"] == "WARNING":
                pygame.draw.rect(screen, RED, laser["rect"], 3)
                warn_text = font.render('!', True, RED)
                text_rect = warn_text.get_rect(center=laser["rect"].center)
                screen.blit(warn_text, text_rect)
            elif laser["state"] == "ACTIVE":
                pygame.draw.rect(screen, RED, laser["rect"])

        if is_shield_active:
            pygame.draw.rect(screen, YELLOW, player) 
        else:
            blink = (invincible // 10) % 2 == 0
            if blink:
                pygame.draw.rect(screen, BLUE, player) 

        # 실드 게이지 렌더링
        if shift_held or shield_gauge < MAX_SHIELD_GAUGE or is_shield_overheated:
            gauge_radius = 40 
            gauge_center = (player.centerx, player.centery) 
            gauge_color = YELLOW if not is_shield_overheated else (255, 128, 0)
            gauge_ratio = shield_gauge / MAX_SHIELD_GAUGE
            
            start_angle = -math.pi / 2
            sweep_angle = gauge_ratio * (2 * math.pi)
            end_angle = start_angle + sweep_angle
            
            gauge_rect = pygame.Rect(gauge_center[0] - gauge_radius, gauge_center[1] - gauge_radius, gauge_radius * 2, gauge_radius * 2)
            
            pygame.draw.arc(screen, WHITE, gauge_rect, -math.pi / 2, 3 * math.pi / 2, 2)
            pygame.draw.arc(screen, gauge_color, gauge_rect, start_angle, end_angle, 6)

        for enemy in enemies:
            pygame.draw.rect(screen, RED, enemy["rect"])

        draw_hud(score, level_cfg, lives)
        pygame.display.flip()

if __name__ == "__main__":
    while True:
        restart = main()
        if not restart:  
            break
    pygame.quit()
    sys.exit()