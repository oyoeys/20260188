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

# --- 페이즈 2 (150점) 설정 ⭐ ---
PHASE2_THRESHOLD = 150

WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
BLUE   = (50,  120, 220)
RED    = (220, 50,  50)
YELLOW = (240, 200, 0)
GRAY   = (40,  40,  40)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dodger - Phase 2: Crossfire")
clock = pygame.time.Clock()
font = get_korean_font(36)
font_big = get_korean_font(72)

LEVELS = [
    {"min_speed": 3, "max_speed": 5,  "spawn": 40, "label": "Lv.1"},
    {"min_speed": 5, "max_speed": 8,  "spawn": 25, "label": "Lv.2"},
    {"min_speed": 7, "max_speed": 12, "spawn": 15, "label": "Lv.3"},
]

PLAYER_W, PLAYER_H = 50, 30
ENEMY_W,  ENEMY_H  = 30, 30

def draw_hud(score, level_cfg, lives):
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))
    # 150점 이상이면 페이즈2 경고 표시 추가
    phase_text = " [PHASE 2]" if score >= PHASE2_THRESHOLD else ""
    screen.blit(font.render(f"{level_cfg['label']}{phase_text}", True, YELLOW), (10, 40))
    screen.blit(font.render(f"Lives: {'♥ ' * lives}", True, RED), (WIDTH - 180, 10))

def game_over_screen(score):
    screen.fill(GRAY)
    screen.blit(font_big.render("GAME OVER", True, RED), (220, 220))
    screen.blit(font.render(f"Score: {score}", True, WHITE), (350, 310))
    screen.blit(font.render("R: Restart   Q: Quit", True, WHITE), (270, 360))
    pygame.display.flip()
    
    while True:
        clock.tick(FPS)  
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return True
                if e.key == pygame.K_q: return False

def main():
    player_x = float(WIDTH // 2 - PLAYER_W // 2)
    player_y = float(HEIGHT - 60)
    player = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
    
    enemies = []
    score = 0
    lives = 3
    level_idx = 0
    level_cfg = LEVELS[level_idx]
    invincible = 0

    v_spawn_timer = 0 # 위에서 떨어지는 적 타이머
    h_spawn_timer = 0 # 좌우에서 날아오는 적 타이머

    lasers = []
    laser_spawn_timer = 0

    shield_gauge = float(MAX_SHIELD_GAUGE)
    is_shield_overheated = False

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False

        keys = pygame.key.get_pressed()
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
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
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  player_x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: player_x += PLAYER_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:    player_y -= PLAYER_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  player_y += PLAYER_SPEED

        player_x = max(0, min(WIDTH - PLAYER_W, player_x))
        player_y = max(0, min(HEIGHT - PLAYER_H, player_y))

        player.x = int(player_x)
        player.y = int(player_y)

        # --- 적 스폰 로직 (페이즈 2 적용 ⭐) ---
        is_phase2 = score >= PHASE2_THRESHOLD
        
        v_spawn_timer += 1
        # 150점 이상이면 스폰 타이머 목표치를 2배로 늘려서 스폰량 50% 감소
        target_v_spawn = level_cfg["spawn"] * 2 if is_phase2 else level_cfg["spawn"]
        
        if v_spawn_timer >= target_v_spawn:
            v_spawn_timer = 0
            x = random.randint(0, WIDTH - ENEMY_W)
            speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"])
            # 속도 50% 감소 (최소 속도 1 보장)
            if is_phase2:
                speed = max(1, int(speed * 0.5))
            
            enemies.append({
                "rect": pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H),
                "speed_x": 0,
                "speed_y": speed
            })

        # 150점 이상일 때만 좌우 적 스폰 활성화
        if is_phase2:
            h_spawn_timer += 1
            # 감소된 수직 스폰량만큼 수평 스폰 빈도 배정
            target_h_spawn = level_cfg["spawn"] * 2
            
            if h_spawn_timer >= target_h_spawn:
                h_spawn_timer = 0
                y = random.randint(0, HEIGHT - ENEMY_H)
                speed = random.randint(level_cfg["min_speed"], level_cfg["max_speed"])
                # 가로로도 너무 빠르면 피하기 힘드니 속도 보정
                speed = max(1, int(speed * 0.7)) 
                
                # 왼쪽에서 출발할지 오른쪽에서 출발할지 랜덤
                if random.choice([True, False]):
                    # 왼쪽 -> 오른쪽
                    enemies.append({
                        "rect": pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H),
                        "speed_x": speed,
                        "speed_y": 0
                    })
                else:
                    # 오른쪽 -> 왼쪽
                    enemies.append({
                        "rect": pygame.Rect(WIDTH, y, ENEMY_W, ENEMY_H),
                        "speed_x": -speed,
                        "speed_y": 0
                    })
        # ----------------------------------------

        if score >= LASER_SCORE_THRESHOLD:
            laser_spawn_timer += 1
            if laser_spawn_timer >= LASER_SPAWN_INTERVAL and len(lasers) < MAX_ACTIVE_LASERS:
                laser_spawn_timer = 0
                is_horizontal = random.choice([True, False])
                if is_horizontal:
                    laser_y = random.randint(0, HEIGHT - LASER_THICKNESS)
                    laser_rect = pygame.Rect(0, laser_y, WIDTH, LASER_THICKNESS)
                else:
                    laser_x = random.randint(0, WIDTH - LASER_THICKNESS)
                    laser_rect = pygame.Rect(laser_x, 0, LASER_THICKNESS, HEIGHT)

                new_laser = {
                    "state": "WARNING",
                    "rect": laser_rect,
                    "timer": LASER_WARNING_DURATION
                }
                lasers.append(new_laser)

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

        # --- 화면 밖으로 나간 적 점수 처리 (사방팔방 지원 ⭐) ---
        survived = []
        for enemy in enemies:
            is_out_of_bounds = False
            
            if enemy["speed_y"] > 0 and enemy["rect"].top >= HEIGHT:
                is_out_of_bounds = True
            elif enemy["speed_x"] > 0 and enemy["rect"].left >= WIDTH:
                is_out_of_bounds = True
            elif enemy["speed_x"] < 0 and enemy["rect"].right <= 0:
                is_out_of_bounds = True

            if not is_out_of_bounds:
                survived.append(enemy)
            else:
                score += 1
        enemies = survived
        # ----------------------------------------------------

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