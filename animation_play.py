import base64, io
import pygame

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  스프라이트 시트 Base64 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHEET_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAA1VJREFUeJztWjGLGkEU/jQaiNgErG7hQhBOuE4QgtiktLEwGNOfcL8ghXBphRT3CwKJtTm4LfwDaSwCBylShSCHAbsrFwNn7kxhZjM7+2Z23Ylkh50PDryZ9733buZ5O9/bATKOHDVYcZyNOHazXJK2pvMLFPHqsB4ybACbqERM5PsLUHGczdVhHW6xBKxXeP3goW90fneLs2oL3fUKDWBDJWEqv8CTeZzf3YZWEdiurujEZH5BNOiuV9tVJMbjwDR+aAF2CaZKYlewpLvr1d7iUwuTl026xZL/E+VENR7Xrjcdo93xIv0kje8WS2h3PPSm48C4XwFi6bQ73l/ytAzebkQEkJUeZUfx68dHmE/6aONbIF5cflT8dsfDQbOG6vFRYNxfALdY8kvn54t7lE8vAkk9usz7dhR4vgpRi3TQrKF7+X1nflT8x80aOU5WwEnTAb6+CST1Ybr07fZRATxUfpLGP5GMkxUgC6xKTrcC5pM+AGAwXEgfYTrxB8MF3r99gvmkj+qrj/44WQEzzpiRW9x/6X1UwGC4AAC08gW4efLhpBW/xcXgIT1MiCcphsaPL+RxlDqMUEgbP+CInaXPqq0QcTSfAYh3FjeJn3k1mKcGswQrh3myiXJWl2/lsGhgmpzV5Vs5LJu0ctjKYSuHA0lZOWzlsJXDANInZ3X5Vg6rHPFIq5zdBz9TyHwFBOQw+6zS0zJnpvJDcjhKTzNnMjlqGr8ge3yoDiO8pjadb/sBQPgYKToRyZREFvkqyCQ24+2zHyHGLjCCOCGTw8x+JPwetx9A8XvTMbx3L+FOy4n0xC46pN3xUD69wOiPLCYrQCWHdRKQ8eP2AhiSbgDVEyArQCWHdRKQ8fk4ql4AQ9INoHoCZAVQ4Of/dQXEneNzSbIBVE+ArACVHNZJQMaP2wtgSLoBVE8gB9BSUiaHgbCkjCtFKX7FcTbPnz4DsO0FxEF3vfJ9BF6IxMDs/hcA4NP1Z9wsl7nAH8E+q+QkEH0U3ZWvs4C6/NSIIZWWZ1D1BJLyU6eRqcVjiLMJuvzMITVfgf/Ft/cDeLKJ7/d1+fZ+gGhgmp7X5dv7AbJJez/A3g+w9wMCSdn7AfZ+gL0fACB97/d1+fZ+gMoRj7SquX3wM4XfV50la/h33BEAAAAASUVORK5CYII="

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN_W, SCREEN_H = 480, 320
FRAME_W, FRAME_H   = 16, 16
COLS               = 4
FRAME_DELAY        = 150   # ms
DISPLAY_SCALE      = 4     # 화면 확대 배율

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Sprite Animation Demo")
clock = pygame.time.Clock()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  시트 로드 → 프레임 리스트
#  인덱스 0 ~ 15 (총 16개)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
sheet_bytes = base64.b64decode(SHEET_B64)
player_sheet = pygame.image.load(io.BytesIO(sheet_bytes)).convert_alpha()

player_frames = []
for i in range(16):
    row, col = divmod(i, COLS)
    rect = pygame.Rect(col * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H)
    player_frames.append(player_sheet.subsurface(rect))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  walk_frames: 선택한 프레임 순서
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
walk_frames = [player_frames[i] for i in [0, 1, 2, 3, 4, 5, 6, 7]]

frame_index = 0
frame_timer = 0
x = SCREEN_W // 2 - (FRAME_W * DISPLAY_SCALE) // 2
y = SCREEN_H // 2 - (FRAME_H * DISPLAY_SCALE) // 2

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  게임 루프
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
running = True
while running:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    frame_timer += dt
    if frame_timer >= FRAME_DELAY:
        frame_index = (frame_index + 1) % len(walk_frames)
        frame_timer = 0

    screen.fill((30, 30, 40))
    frame_img = pygame.transform.scale(
        walk_frames[frame_index],
        (FRAME_W * DISPLAY_SCALE, FRAME_H * DISPLAY_SCALE)
    )
    screen.blit(frame_img, (x, y))
    pygame.display.flip()

pygame.quit()
