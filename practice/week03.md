# 실습실 컴퓨터내 크롬이 게스트였기에 복기하여 작성하기에 정확성이 낮음
# Q.        rem = []
#        for sq in squares:
#            dist = math.sqrt((circle_x-sq[0])**2 + (circle_y-sq[1])**2)
#            if dist < 100:
#                score += 1
#                last_eat_time = current_time
#            elif current_time - sq[2] < 500:
#                rem.append(sq)
#        squares = rem                      ||| 이 코드는 무슨 역할을 하는 코드야?
# A. 
# --- 사각형 처리 로직 시작 ---
#        rem = []  # 화면에 계속 남겨둘 사각형들을 담을 임시 리스트
        
#        for sq in squares:
#            # 1. 플레이어(원)와 사각형 사이의 거리 계산 (피타고라스 정리)
#            # sq[0]: 사각형 x좌표, sq[1]: 사각형 y좌표
#            dist = math.sqrt((circle_x - sq[0])**2 + (circle_y - sq[1])**2)
            
#            # 2. 충돌 판정: 거리가 100보다 작으면 '먹은 것'으로 간주
#           if dist < 100:
#                score += 1                 # 점수 1점 증가
#                last_eat_time = current_time # 마지막으로 먹은 시간 갱신 (생존 시간 연장)
#                # 'rem'에 추가하지 않으므로 이 사각형은 리스트에서 제외(삭제)됨
                
#            # 3. 사라짐 판정: 아직 먹지 못한 사각형 중 태어난 지 0.5초(500ms) 미만인 것만 유지
#            # sq[2]: 사각형이 생성된 시점의 시간
#            elif current_time - sq[2] < 500:
#                rem.append(sq)             # 아직 유효한 사각형이므로 다음 프레임에도 유지
#        
#        # 4. 최종적으로 필터링된(먹혔거나 시간이 지난 것 제외) 리스트로 업데이트
#        squares = rem
#        # --- 사각형 처리 로직 끝 ---
# TL;DR: 0.5초 안에 사각형을 먹어 점수를 올리고 생존 시간을 연장하는 핵심 로직입니다.
