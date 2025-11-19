# 조이스틱 스무딩 기능

## 개요
조이스틱 제어의 부드러운 조작을 위한 필터링 기능입니다.

## 기능

### 1. 조이스틱 스무딩 활성화
- **기본값:** OFF (비활성화)
- **설명:** 스무딩을 켜면 조이스틱 입력이 부드럽게 필터링됩니다

### 2. 조향 민감도
- **기본값:** 50
- **범위:** 10~100 (단위: 10)
- **설명:** 값이 클수록 핸들이 빠르게 반응합니다
  - 10-30: 부드럽게 (주차장, 저속)
  - 40-60: 보통 (일반 주행)
  - 70-100: 빠르게 (고속, 긴급)

### 3. 액셀 민감도
- **기본값:** 50
- **범위:** 10~100 (단위: 10)
- **설명:** 값이 클수록 가속이 빠르게 반응합니다
  - 10-30: 부드럽게 (연비 주행)
  - 40-60: 보통 (일반 주행)
  - 70-100: 빠르게 (스포츠 주행)

### 4. 입력 무시 범위 (데드존)
- **기본값:** 5
- **범위:** 0~20 (단위: 1)
- **설명:** 스틱을 살짝 건드려도 반응하지 않는 범위
  - 0-2: 거의 없음 (정밀 제어)
  - 3-7: 적당함 (일반 사용)
  - 8-20: 큼 (떨림 방지)

## 사용 방법

### 설정 위치
```
설정 → 개발자 → 조이스틱 디버그 모드
```

### 설정 순서
1. "조이스틱 디버그 모드" 켜기
2. "조이스틱 스무딩 활성화" 켜기
3. 세부 설정 조정:
   - 조향 민감도
   - 액셀 민감도
   - 입력 무시 범위

### 비활성화 시
- 스무딩 OFF: 조이스틱 입력이 즉시 반영됩니다 (필터 없음)
- 현재 구현과 동일하게 동작

## 기술 세부사항

### 스무딩 알고리즘
```python
# 민감도에 따른 지수 이동 평균 (EMA)
output = prev_output * (1 - sensitivity) + input * sensitivity

# 예시:
# sensitivity = 1.0 (100%) → 즉시 반영
# sensitivity = 0.5 (50%)  → 이전값 50% + 새값 50%
# sensitivity = 0.1 (10%)  → 이전값 90% + 새값 10%
```

### 데드존 적용
```python
if abs(input) < deadzone:
    input = 0.0
```

## UI 구현 (C++ 패치 필요)

UI 코드는 C++로 작성되어 있어 별도 컴파일이 필요합니다.

### 패치 파일
- `developer_panel_joystick_smoothing.patch` - UI 코드
- `developer_panel_header.patch` - 헤더 선언

### 적용 방법
1. comma 디바이스에서 openpilot 재컴파일
2. 또는 prebuilt 바이너리 사용

## 파라미터

### Params 키
- `JoystickSmoothingEnabled` (bool) - 스무딩 활성화 여부
- `JoystickSteeringSensitivity` (int) - 조향 민감도 (10~100)
- `JoystickAccelSensitivity` (int) - 액셀 민감도 (10~100)
- `JoystickDeadzone` (int) - 데드존 (0~20)

### 기본값
```python
JoystickSmoothingEnabled = False
JoystickSteeringSensitivity = 50
JoystickAccelSensitivity = 50
JoystickDeadzone = 5
```

## 문제 해결

### 조향이 너무 떨려요
→ 조향 민감도를 낮추세요 (50 → 30)

### 반응이 너무 느려요
→ 민감도를 높이세요 (50 → 80)

### 스틱을 살짝만 건드려도 반응해요
→ 입력 무시 범위를 높이세요 (5 → 10)

### 설정이 저장되지 않아요
→ Params에 자동 저장됩니다. 재부팅 후에도 유지됩니다.

## 커밋 히스토리
- `d53a643` - Add joystick smoothing feature with configurable sensitivity and deadzone
- `9c855ed` - Add UI patch files for joystick smoothing controls
