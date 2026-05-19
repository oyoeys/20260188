import pygame
import random
from collections import deque

# =====================
SCREEN_WIDTH  = 1200
SCREEN_HEIGHT = 800
TILE_SIZE     = 45   
COLS          = 15   
ROWS          = 15   
MAP_OFFSET_X  = 40
MAP_OFFSET_Y  = 50

MAX_ROOMS     = 65   

# 방 상태/타입 상수
START        = 1
NORMAL       = 2
EXIT_ROOM    = 3

# 테마 색상
COLOR_BG       = (10, 10, 12)    
COLOR_GRID     = (20, 20, 25)    
COLOR_START    = (200, 200, 220) 
COLOR_NORMAL   = (40, 60, 80)    
COLOR_EXIT     = (40, 180, 100)  
COLOR_TRAP     = (180, 40, 40)   
COLOR_UNKNOWN  = (10, 10, 12)    
COLOR_TEXT     = (240, 240, 255)

# 게임 단계
PHASE_SPREAD   = 0
PHASE_SETUP    = 1
PHASE_PLAY     = 2
PHASE_WARNING  = 3  # 🛠️ 함정 인터페이스를 띄워놓고 0.4초간 인지시키는 경고 대기 단계
PHASE_MINIGAME = 4  # 실제 타이머가 깎이고 조작이 시작되는 단계
# =====================

def get_neighbors(x, y):
    neighbors = []
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            neighbors.append((nx, ny))
    return neighbors

class CubeRoom:
    def __init__(self, r_type):
        self.type = r_type
        self.visited = False
        self.is_trap = False
        self.trap_triggered = False
        self.scanned = False 
        
        self.code = [random.randint(0, 9) for _ in range(3)]
        
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 27]
        if sum(self.code) in primes and self.type == NORMAL:
            self.is_trap = True

    def get_code_str(self):
        return f"{self.code[0]}{self.code[1]}{self.code[2]}"

class CubeGenerator:
    def __init__(self, seed):
        random.seed(seed)
        self.seed = seed
        self.rooms = {} 
        
        self.start_pos = (COLS // 2, ROWS // 2)
        self.rooms[self.start_pos] = CubeRoom(START)
        self.rooms[self.start_pos].visited = True
        
        self.phase = PHASE_SPREAD
        self.player_pos = self.start_pos
        self.shoes = 3 
        self.game_over = False
        self.game_clear = False
        self.log_message = "큐브가 확장 파티션을 정렬하고 있습니다. 구조 분석 중..."

        self.valid_hatches = set()

        # 경고등 연출용 타이머 (밀리초 단위)
        self.warning_timer = 0
        self.warning_duration = 400  # 0.4초간 입력 동결 및 인지 시간 보장

        # 미니게임 변수
        self.minigame_timer = 0
        self.minigame_max_time = 1200 
        self.trap_pos = None
        self.minigame_type = 0       
        
        self.minigame_keys = []      
        self.minigame_keys_str = []  
        self.minigame_idx = 0        
        
        self.minigame_space_count = 0
        self.minigame_space_target = 6  

    def step(self):
        if self.phase == PHASE_SPREAD:
            if len(self.rooms) < MAX_ROOMS:
                candidates = []
                for (rx, ry) in self.rooms.keys():
                    for nx, ny in get_neighbors(rx, ry):
                        if (nx, ny) not in self.rooms:
                            candidates.append((nx, ny))
                if candidates:
                    new_pos = random.choice(candidates)
                    self.rooms[new_pos] = CubeRoom(NORMAL)
            else:
                self.phase = PHASE_SETUP

        elif self.phase == PHASE_SETUP:
            all_edges = []
            room_list = list(self.rooms.keys())
            for i, p1 in enumerate(room_list):
                for p2 in room_list[i+1:]:
                    if abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) == 1:
                        all_edges.append((p1, p2))
            
            potential_extra_edges = list(all_edges)
            random.shuffle(all_edges)
            
            parent = {p: p for p in room_list}
            def find(p):
                if parent[p] == p: return p
                parent[p] = find(parent[p])
                return parent[p]
            def union(p1, p2):
                root1 = find(p1)
                root2 = find(p2)
                if root1 != root2: parent[root1] = root2; return True
                return False

            for u, v in all_edges:
                if union(u, v):
                    self.valid_hatches.add((u, v))
                    self.valid_hatches.add((v, u)) 

            for u, v in potential_extra_edges:
                if (u, v) not in self.valid_hatches and random.random() < 0.45:
                    self.valid_hatches.add((u, v))
                    self.valid_hatches.add((v, u))

            exit_pos, safe_path = self.find_farthest_room_bfs()
            self.rooms[exit_pos].type = EXIT_ROOM
            self.rooms[exit_pos].is_trap = False

            primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 27]
            for pos in safe_path:
                room = self.rooms[pos]
                if room.is_trap:
                    while sum(room.code) in primes:
                        room.code = [random.randint(0, 9) for _ in range(3)]
                    room.is_trap = False

            normal_rooms = [p for p, r in self.rooms.items() if r.type == NORMAL and p != exit_pos and p not in safe_path]
            num_extra_traps = int(len(normal_rooms) * 0.25)
            extra_trap_positions = random.sample(normal_rooms, min(num_extra_traps, len(normal_rooms)))
            
            for pos in extra_trap_positions:
                self.rooms[pos].is_trap = True
                self.rooms[pos].code = [3, 3, 5]  

            self.phase = PHASE_PLAY
            self.log_message = f"💥 초대형 미궁 생성 완료 ({MAX_ROOMS}개의 방). 어둠을 헤치고 나아가십시오."

    def find_farthest_room_bfs(self):
        queue = deque([(self.start_pos, [self.start_pos])])
        visited = {self.start_pos}
        farthest_room = self.start_pos
        max_dist = 0
        best_path = [self.start_pos]

        while queue:
            curr, path = queue.popleft()
            if (len(path) - 1) > max_dist:
                max_dist = len(path) - 1
                farthest_room = curr
                best_path = path
            for nx, ny in get_neighbors(curr[0], curr[1]):
                next_pos = (nx, ny)
                if (curr, next_pos) in self.valid_hatches and next_pos not in visited:
                    visited.add(next_pos)
                    queue.append((next_pos, path + [next_pos]))
        return farthest_room, best_path

    def move_player(self, dx, dy):
        if self.phase != PHASE_PLAY or self.game_over or self.game_clear: return
        
        curr = self.player_pos
        target = (curr[0] + dx, curr[1] + dy)
        
        if target in self.rooms:
            if (curr, target) in self.valid_hatches:
                self.player_pos = target
                room = self.rooms[target]
                room.visited = True
                
                if room.type == EXIT_ROOM:
                    self.game_clear = True
                    self.log_message = "축하합니다! 거대한 암흑 미궁을 파훼하고 탈출구에 도달했습니다!"
                elif room.is_trap:
                    # 🛠️ [수정] 진입 즉시 미니게임 종류를 먼저 결정하여 인터페이스를 미리 셋업합니다.
                    self.trap_pos = target
                    self.minigame_type = random.choice([0, 1])
                    
                    if self.minigame_type == 0:
                        self.minigame_idx = 0  
                        arrow_map = {
                            pygame.K_UP: "↑", pygame.K_DOWN: "↓", 
                            pygame.K_LEFT: "←", pygame.K_RIGHT: "→"
                        }
                        arrow_keys = list(arrow_map.keys())
                        self.minigame_keys = [random.choice(arrow_keys) for _ in range(4)]
                        self.minigame_keys_str = [arrow_map[k] for k in self.minigame_keys]
                    else:
                        self.minigame_space_count = 0
                    
                    # 🛠️ 인터페이스를 띄운 채 0.4초간 대기하는 '경고 단계'로 먼저 진입
                    self.phase = PHASE_WARNING
                    self.warning_timer = self.warning_duration
                    self.log_message = "🚨 트랩 시스템 감지! 함정 인터페이스 전개 중... (0.4초 후 가동)"
                else:
                    self.log_message = f"방 진입 성공. 암호 코드: {room.get_code_str()}"
            else:
                self.log_message = "방향은 맞지만 해치가 용접되어 막혀있습니다."
        else:
            self.log_message = "벽 너머는 허공입니다."

    # 🛠️ 경고 대기 단계 업데이트 (인터페이스를 보여준 상태로 0.4초 홀딩)
    def update_warning(self, dt):
        if self.phase != PHASE_WARNING: return
        self.warning_timer -= dt
        if self.warning_timer <= 0:
            # 인지 시간이 끝나면 실제 타이머 작동 및 조작 허용 페이즈로 이동
            self.phase = PHASE_MINIGAME
            self.minigame_timer = self.minigame_max_time
            if self.minigame_type == 0:
                self.log_message = "⚠️ 카운트다운 시작! 커맨드를 정확하게 입력하세요!"
            else:
                self.log_message = f"⚠️ 카운트다운 시작! [SPACEBAR]를 연타하여 게이지를 채우세요!"

    def update_minigame(self, dt):
        if self.phase != PHASE_MINIGAME: return
        self.minigame_timer -= dt
        if self.minigame_timer <= 0:
            self.game_over = True
            self.phase = PHASE_PLAY
            self.rooms[self.trap_pos].trap_triggered = True
            self.log_message = "시간 초과로 사망했습니다. 기가 미궁의 전모가 드러납니다."

    def throw_shoe(self, dx, dy):
        if self.phase != PHASE_PLAY or self.game_over or self.game_clear: return
        if self.shoes <= 0:
            self.log_message = "던질 신발이 소진되었습니다."
            return
            
        curr = self.player_pos
        target = (curr[0] + dx, curr[1] + dy)
        
        if target in self.rooms and (curr, target) in self.valid_hatches:
            self.shoes -= 1
            target_room = self.rooms[target]
            target_room.scanned = True
            
            if target_room.is_trap:
                self.log_message = f"💥 깡통 소리! ({target_room.get_code_str()}) 함정 확정! (신발 -1)"
            else:
                self.log_message = f"조용합니다... ({target_room.get_code_str()}) 안전 확인. (신발 -1)"
        else:
            self.log_message = "해치가 막혀있거나 벽이라 신발을 던질 수 없습니다."

def draw(screen, gen, font_lg, font_sm):
    if gen.phase == PHASE_WARNING:
        screen.fill((30, 5, 5))  # 경고 대기 상태일 때는 맵 배경을 어둡고 붉게 처리
    else:
        screen.fill(COLOR_BG)
    
    for x in range(COLS + 1):
        grid_color = (60, 20, 20) if gen.phase == PHASE_WARNING else COLOR_GRID
        pygame.draw.line(screen, grid_color, (MAP_OFFSET_X + x*TILE_SIZE, MAP_OFFSET_Y), (MAP_OFFSET_X + x*TILE_SIZE, MAP_OFFSET_Y + ROWS*TILE_SIZE))
    for y in range(ROWS + 1):
        grid_color = (60, 20, 20) if gen.phase == PHASE_WARNING else COLOR_GRID
        pygame.draw.line(screen, grid_color, (MAP_OFFSET_X, MAP_OFFSET_Y + y*TILE_SIZE), (MAP_OFFSET_X + COLS*TILE_SIZE, MAP_OFFSET_Y + y*TILE_SIZE))

    reveal_all = gen.game_over or gen.game_clear
    pad = 3

    for (x, y), room in gen.rooms.items():
        px = MAP_OFFSET_X + x * TILE_SIZE + pad
        py = MAP_OFFSET_Y + y * TILE_SIZE + pad
        w = TILE_SIZE - pad*2
        h = TILE_SIZE - pad*2
        
        if reveal_all:
            if room.type == START: color = COLOR_START
            elif room.type == EXIT_ROOM: color = COLOR_EXIT
            elif room.is_trap or room.trap_triggered: color = COLOR_TRAP
            else: color = COLOR_NORMAL
        else:
            if room.visited:
                if (gen.phase == PHASE_WARNING or gen.phase == PHASE_MINIGAME) and (x, y) == gen.trap_pos:
                    color = COLOR_TRAP
                else:
                    if room.type == START: color = COLOR_START
                    elif room.type == EXIT_ROOM: color = COLOR_EXIT
                    elif room.trap_triggered: color = COLOR_TRAP
                    else: color = COLOR_NORMAL
            elif room.scanned:
                color = COLOR_TRAP if room.is_trap else COLOR_NORMAL
            else:
                continue 
            
        pygame.draw.rect(screen, color, (px, py, w, h))
        
        # 통로선
        for nx, ny in get_neighbors(x, y):
            if ((x, y), (nx, ny)) in gen.valid_hatches:
                neighbor_room = gen.rooms.get((nx, ny))
                if neighbor_room and (reveal_all or room.visited or room.scanned or neighbor_room.visited or neighbor_room.scanned):
                    dc = (140, 160, 200) if (room.visited or neighbor_room.visited or reveal_all) else (60, 70, 90)
                    if gen.phase == PHASE_WARNING: dc = (200, 80, 80)
                    if nx > x: pygame.draw.rect(screen, dc, (px + w, py + h//2 - 2, 4, 4))
                    if nx < x: pygame.draw.rect(screen, dc, (px - 4, py + h//2 - 2, 4, 4))
                    if ny > y: pygame.draw.rect(screen, dc, (px + w//2 - 2, py + h, 4, 4))
                    if ny < y: pygame.draw.rect(screen, dc, (px + w//2 - 2, py - 4, 4, 4))

        if reveal_all or room.visited or room.scanned:
            is_bright = room.visited or reveal_all
            txt_color = (255, 255, 255) if is_bright else (180, 180, 180)
            if (gen.phase == PHASE_WARNING or gen.phase == PHASE_MINIGAME) and (x, y) == gen.trap_pos: txt_color = (255, 220, 220)
            txt = font_sm.render(room.get_code_str(), True, txt_color)
            screen.blit(txt, (px + w//2 - txt.get_width()//2, py + h//2 - txt.get_height()//2))

    if gen.phase >= PHASE_PLAY:
        ppx = MAP_OFFSET_X + gen.player_pos[0] * TILE_SIZE + TILE_SIZE//2
        ppy = MAP_OFFSET_Y + gen.player_pos[1] * TILE_SIZE + TILE_SIZE//2
        p_color = (255, 100, 0) if gen.phase == PHASE_WARNING else (255, 255, 0)
        pygame.draw.circle(screen, p_color, (ppx, ppy), 7)

    # UI 우측 레이아웃
    ui_x = MAP_OFFSET_X + COLS * TILE_SIZE + 40
    screen.blit(font_lg.render("THE CUBE: 기가 미궁 버전", True, (255, 80, 80)), (ui_x, 50))
    
    state_str = "⌛ 큐브 증설 중..." if gen.phase < PHASE_PLAY else "🏃 거대 미로 탐색 중"
    if gen.phase == PHASE_WARNING: state_str = "🚨 WARNING: 함정 인지 시간 (0.4초)"
    elif gen.phase == PHASE_MINIGAME: state_str = "⚠️ 함정 QTE 가동!"
    if gen.game_over: state_str = "💀 SYSTEM FAILURE (사망)"
    elif gen.game_clear: state_str = "🎉 SYSTEM CLEARED (탈출)"
        
    screen.blit(font_sm.render(f"미궁 규모: 대형 그리드 ({COLS}x{ROWS})", True, (160, 160, 160)), (ui_x, 90))
    screen.blit(font_sm.render(f"생성된 방 개수: {len(gen.rooms)} / {MAX_ROOMS}", True, (160, 160, 160)), (ui_x, 115))
    
    state_color = (255, 50, 50) if gen.phase in [PHASE_WARNING, PHASE_MINIGAME] else (230, 230, 230)
    screen.blit(font_sm.render(f"시스템 상태: {state_str}", True, state_color), (ui_x, 145))
    screen.blit(font_sm.render(f"남은 신발 개수: 👟 x {gen.shoes}", True, (100, 200, 255)), (ui_x, 175))
    
    pygame.draw.rect(screen, (30, 30, 40), (ui_x, 230, 400, 180))
    screen.blit(font_sm.render("[하드코어 기가 미궁 생존 가이드]", True, (255, 200, 100)), (ui_x + 15, 245))
    screen.blit(font_sm.render("- 이동: W, A, S, D 키", True, COLOR_TEXT), (ui_x + 15, 275))
    screen.blit(font_sm.render("- 신발 던지기: 방향키 (↑, ↓, ←, →)", True, COLOR_TEXT), (ui_x + 15, 305))
    screen.blit(font_sm.render("- 방이 65개로 증가하여 길찾기가 훨씬 복잡합니다.", True, (200, 200, 200)), (ui_x + 15, 335))
    screen.blit(font_sm.render("- 리셋(새로운 미궁 생성): N 키", True, COLOR_TEXT), (ui_x + 15, 365))

    # 🛠️ [핵심 변경] PHASE_WARNING과 PHASE_MINIGAME 둘 다 함정 인터페이스 팝업을 띄웁니다.
    if gen.phase in [PHASE_WARNING, PHASE_MINIGAME]:
        ov_w, ov_h = 420, 200
        ov_x = (SCREEN_WIDTH - ov_w) // 2
        ov_y = (SCREEN_HEIGHT - ov_h) // 2
        
        # 경고 대기 모드일 때는 테두리와 팝업 배경을 격렬하게 오렌지/레드로 블렌딩해서 강조
        box_bg = (50, 10, 10) if gen.phase == PHASE_WARNING else (40, 10, 10)
        border_color = (255, 120, 0) if gen.phase == PHASE_WARNING else COLOR_TRAP
        
        pygame.draw.rect(screen, box_bg, (ov_x, ov_y, ov_w, ov_h))
        pygame.draw.rect(screen, border_color, (ov_x, ov_y, ov_w, ov_h), 3)
        
        if gen.minigame_type == 0:
            title_text = "🚨 [경고] 와이어 트랩 배치 확인! 🚨" if gen.phase == PHASE_WARNING else "⚠️ 살인 와이어 가동! 회피 커맨드! ⚠️"
            title_txt = font_lg.render(title_text, True, (255, 80, 80))
            screen.blit(title_txt, (ov_x + ov_w//2 - title_txt.get_width()//2, ov_y + 25))
            
            start_x = ov_x + ov_w // 2 - 75
            for i in range(4):
                symbol = gen.minigame_keys_str[i]
                if i < gen.minigame_idx:     color = (80, 255, 120)     
                elif i == gen.minigame_idx:  color = (255, 230, 50) if gen.phase == PHASE_MINIGAME else (200, 200, 200)    
                else:                        color = (130, 130, 140)    
                    
                sym_txt = font_lg.render(symbol, True, color)
                screen.blit(sym_txt, (start_x + i * 45, ov_y + 75))
                
            progress_str = "잠시 후 카운트다운 시작..." if gen.phase == PHASE_WARNING else f"진행도: ({gen.minigame_idx} / 4)"
            progress_txt = font_sm.render(progress_str, True, (255, 255, 100) if gen.phase == PHASE_WARNING else (200, 200, 200))
            screen.blit(progress_txt, (ov_x + ov_w//2 - progress_txt.get_width()//2, ov_y + 115))
            
        else:
            title_text = "🚨 [경고] 압착 함정 작동 감지! 🚨" if gen.phase == PHASE_WARNING else "⚠️ 압착 벽 작동! 탈출 장치 해치 개방! ⚠️"
            title_txt = font_lg.render(title_text, True, (255, 80, 80))
            screen.blit(title_txt, (ov_x + ov_w//2 - title_txt.get_width()//2, ov_y + 25))
            
            prompt_str = "⏱️ 함정 구조 파악 중 (조작 대기)..." if gen.phase == PHASE_WARNING else "🔥 [SPACEBAR] 격렬하게 연타!!! 🔥"
            prompt_txt = font_lg.render(prompt_str, True, (255, 150, 100) if gen.phase == PHASE_WARNING else (255, 255, 255))
            screen.blit(prompt_txt, (ov_x + ov_w//2 - prompt_txt.get_width()//2, ov_y + 70))
            
            g_w, g_h = 320, 20
            g_x, g_y = ov_x + (ov_w - g_w) // 2, ov_y + 105
            pygame.draw.rect(screen, (30, 40, 35), (g_x, g_y, g_w, g_h))
            space_ratio = min(1.0, gen.minigame_space_count / gen.minigame_space_target)
            pygame.draw.rect(screen, (80, 255, 120), (g_x, g_y, int(g_w * space_ratio), g_h))
            
            count_str = "대기 모드" if gen.phase == PHASE_WARNING else f"파워 게이지: {int(space_ratio * 100)}% ({gen.minigame_space_count}/{gen.minigame_space_target})"
            count_txt = font_sm.render(count_str, True, (220, 255, 220))
            screen.blit(count_txt, (ov_x + ov_w//2 - count_txt.get_width()//2, g_y + 2))
            
        # 하단 진행 바 연출
        bar_w, bar_h = 320, 10
        bar_x, bar_y = ov_x + (ov_w - bar_w) // 2, ov_y + 155
        pygame.draw.rect(screen, (80, 40, 40), (bar_x, bar_y, bar_w, bar_h))
        
        if gen.phase == PHASE_WARNING:
            # 0.4초 경고 중에는 타이머 게이지가 풀(100%) 상태로 가만히 채워져 있음
            pygame.draw.rect(screen, (255, 120, 0), (bar_x, bar_y, bar_w, bar_h))
        else:
            ratio = max(0.0, gen.minigame_timer / gen.minigame_max_time)
            pygame.draw.rect(screen, (255, 200, 50), (bar_x, bar_y, int(bar_w * ratio), bar_h))
    
    log_color = (255, 80, 80) if (gen.game_over or gen.phase == PHASE_WARNING) else ((100, 255, 100) if gen.game_clear else (220, 220, 220))
    pygame.draw.rect(screen, (20, 20, 30), (MAP_OFFSET_X, SCREEN_HEIGHT - 65, SCREEN_WIDTH - MAP_OFFSET_X*2, 45))
    screen.blit(font_sm.render(f"LOG: {gen.log_message}", True, log_color), (MAP_OFFSET_X + 15, SCREEN_HEIGHT - 55))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("더 큐브(The Cube) - 함정 UI 선노출 패치")
    
    font_lg = pygame.font.SysFont(["malgungothic", "applegothic", "nanumgothic", None], 24, bold=True)
    font_sm = pygame.font.SysFont(["malgungothic", "applegothic", "nanumgothic", None], 15)
    clock = pygame.time.Clock()

    gen = CubeGenerator(random.randint(0, 99999))
    auto_generate = True 

    running = True
    while running:
        dt = clock.tick(60)

        if gen.phase == PHASE_WARNING:
            gen.update_warning(dt)
        elif gen.phase == PHASE_MINIGAME:
            gen.update_minigame(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    gen = CubeGenerator(random.randint(0, 99999))
                
                elif gen.phase == PHASE_PLAY:
                    if event.key == pygame.K_w: gen.move_player(0, -1)
                    if event.key == pygame.K_s: gen.move_player(0, 1)
                    if event.key == pygame.K_a: gen.move_player(-1, 0)
                    if event.key == pygame.K_d: gen.move_player(1, 0)
                    
                    if event.key == pygame.K_UP:    gen.throw_shoe(0, -1)
                    if event.key == pygame.K_DOWN:  gen.throw_shoe(0, 1)
                    if event.key == pygame.K_LEFT:  gen.throw_shoe(-1, 0)
                    if event.key == pygame.K_RIGHT: gen.throw_shoe(1, 0)
                
                # 🛠️ PHASE_MINIGAME 일때만 입력을 받음 (PHASE_WARNING 모드일때는 키 조작이 무시됨)
                elif gen.phase == PHASE_MINIGAME:
                    if gen.minigame_type == 0:
                        if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                            target_key = gen.minigame_keys[gen.minigame_idx]
                            if event.key == target_key:
                                gen.minigame_idx += 1
                                if gen.minigame_idx >= 4:
                                    room = gen.rooms[gen.trap_pos]
                                    room.is_trap = False 
                                    gen.phase = PHASE_PLAY
                                    gen.log_message = "⚡ 회피 완벽 성공! 연속 커맨드로 살인 트랩 메커니즘을 붕괴시켰습니다."
                            else:
                                gen.game_over = True
                                gen.phase = PHASE_PLAY
                                gen.rooms[gen.trap_pos].trap_triggered = True
                                gen.log_message = "❌ 커맨드 미스! 엉뚱한 방향으로 움직여 트랩에 치였습니다. 미궁이 드러납니다."
                                
                    else:
                        if event.key == pygame.K_SPACE:
                            gen.minigame_space_count += 1
                            if gen.minigame_space_count >= gen.minigame_space_target:
                                room = gen.rooms[gen.trap_pos]
                                room.is_trap = False
                                gen.phase = PHASE_PLAY
                                gen.log_message = "⚡ 탈출 성공! 초인적인 무력 연타로 막힌 문을 강제로 뜯어냈습니다!"

        if auto_generate and gen.phase < PHASE_PLAY:
            gen.step()

        draw(screen, gen, font_lg, font_sm)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()