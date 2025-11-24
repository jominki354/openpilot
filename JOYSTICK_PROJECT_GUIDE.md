# Joystick Control Project - Development Guide

## 프로젝트 개요
comma 3x 기기에서 조이스틱을 사용한 차량 제어 시스템 개발

**브랜치:** `j-st-s`
**GitHub:** https://github.com/jominki354/openpilot.git

---

## 주요 구성 요소

### 1. 프로세스 구조
```
joystickd (tools/joystick/joystickd.py)
├─ 역할: 조이스틱 입력을 차량 제어 명령으로 변환
├─ 입력: testJoystick 메시지
├─ 출력: carControl, controlsState 메시지
└─ 실행 조건: JoystickDebugMode = True

joystick_control (tools/joystick/joystick_control.py)
├─ 역할: 실제 조이스틱 하드웨어에서 입력 읽기
├─ 출력: testJoystick 메시지
└─ 실행 조건: JoystickDebugMode = True AND iscar
```

### 2. 설정 파일 위치
```
openpilot/system/manager/process_config.py
├─ 프로세스 실행 조건 정의
└─ joystick, joystickd 프로세스 설정

openpilot/selfdrive/ui/qt/offroad/developer_panel.cc/h
├─ UI 설정 패널
├─ 조이스틱 모드 토글
├─ 민감도 설정 (프리셋 + 세부 조정)
└─ 프로세스 상태 표시
```

### 3. 파라미터 (Params)
```
JoystickDebugMode: bool - 조이스틱 모드 활성화
JoystickSmoothingEnabled: bool - 민감도 필터링 활성화
JoystickSteeringSensitivity: int (10-100) - 조향 반응 속도
JoystickSteeringGain: int (50-400) - 조향 반응 강도
JoystickAccelSensitivity: int (10-100) - 액셀 반응 속도
JoystickAccelGain: int (50-400) - 액셀 반응 강도
JoystickDeadzone: int (0-20) - 입력 무시 범위
JoystickPreset: string - 현재 프리셋 ("기본값", "부드럽게", "보통", "강하게")
```

---

## 개발 환경 설정

### 로컬 개발
```bash
# 저장소 클론
git clone https://github.com/jominki354/openpilot.git
cd openpilot
git checkout j-st-s
```

### comma 기기 접속
```bash
# SSH (WiFi 연결 시)
ssh -i ssh_key.pem comma@<IP_ADDRESS>

# ADB (USB 연결 시)
adb shell
```

### 기기에 코드 적용
```bash
# SSH로
ssh -i ssh_key.pem comma@<IP> "cd /data/openpilot && git fetch origin && git reset --hard origin/j-st-s && sudo reboot"

# ADB로
adb shell "cd /data/openpilot && git fetch origin && git reset --hard origin/j-st-s && sudo reboot"
```

---

## 중요 개발 규칙

### 1. C++ 코드 (UI)
```cpp
// ❌ 잘못된 예
params.get_bool("Key")  // Python 스타일
auto presetDefault = new ButtonControl(...)  // 멤버 변수와 shadowing

// ✅ 올바른 예
params.getBool("Key")  // C++ 스타일
presetDefault = new ButtonControl(...)  // 헤더에 선언된 멤버 변수 사용
```

### 2. 프로세스 실행 조건
```python
# ❌ 잘못된 예 - started 필요 시 크루즈 인게이지 전에 실행 안 됨
def joystick(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started and params.get_bool("JoystickDebugMode")

# ✅ 올바른 예 - 차량 연결 시 바로 실행
def joystick(started: bool, params: Params, CP: car.CarParams) -> bool:
  return params.get_bool("JoystickDebugMode")
```

### 3. 빌드 에러 디버깅
```bash
# 기기에서 빌드 로그 확인
ssh -i ssh_key.pem comma@<IP> "ps aux | grep -i build"

# 에러 메시지 확인
ssh -i ssh_key.pem comma@<IP> "ps aux | grep '_text'"
```

### 4. 파일 수정 후 항상 진단 체크
```bash
# 로컬에서 getDiagnostics 사용
# 커밋 전에 반드시 확인
```

---

## UI 개발 가이드

### Developer Panel 구조
```
조이스틱 모드 (토글)
├─ joystickd (상태: 🟢 ON / 🔴 OFF)
├─ joystick_control (상태: 🟢 ON / 🔴 OFF)
├─ 조이스틱 민감도 (토글)
│   ├─ 프리셋: 기본값 (버튼)
│   ├─ 프리셋: 부드럽게 (버튼)
│   ├─ 프리셋: 보통 (버튼)
│   ├─ 프리셋: 강하게 (버튼)
│   ├─ 조향 반응 속도 (슬라이더)
│   ├─ 조향 반응 강도 (슬라이더)
│   ├─ 액셀 반응 속도 (슬라이더)
│   ├─ 액셀 반응 강도 (슬라이더)
│   └─ 입력 무시 범위 (슬라이더)
```

### 프리셋 색상 표시
```cpp
// 활성 프리셋: 초록색 배경 (#33Ab4C)
// 비활성 프리셋: 회색 배경 (#393939)
updatePresetButtons();  // 프리셋 변경 시 호출
```

### UI 즉시 업데이트
```cpp
// 값 변경 후 UI 강제 업데이트
updateValueControls();  // hide/show로 강제 리프레시
```

---

## 프로세스 상태 모니터링

### ManagerState 파싱
```cpp
auto manager_state = params.get("ManagerState");
bool joystickd_running = manager_state.find("joystickd") != std::string::npos;
bool joystick_running = manager_state.find("\"joystick\"") != std::string::npos;
```

### 상태 표시
- **🟢 ON**: 프로세스 실행 중
- **🔴 OFF**: 프로세스 중지됨
- **대기중...**: 시스템 초기화 중

---

## 트러블슈팅

### 문제: "프로세스가 실행되지 않았습니다 joystickd"
**원인:** `started` 조건 때문에 크루즈 인게이지 전에 joystickd가 실행되지 않음
**해결:** process_config.py에서 `started` 조건 제거

### 문제: 빌드 에러 - "no member named 'get_bool'"
**원인:** Python 스타일 메서드명 사용
**해결:** `get_bool` → `getBool` 변경

### 문제: 변수 shadowing 에러
**원인:** 헤더에 선언된 멤버 변수를 함수 내에서 `auto`로 재선언
**해결:** `auto` 키워드 제거, 멤버 변수 직접 사용

### 문제: UI 값이 즉시 업데이트 안 됨
**원인:** Qt 위젯이 자동으로 리프레시되지 않음
**해결:** `updateValueControls()` 함수로 강제 리프레시

---

## 커밋 메시지 규칙

```
Fix: 버그 수정
Add: 새 기능 추가
Improve: 기능 개선
Refactor: 코드 리팩토링
Docs: 문서 수정
```

**예시:**
```
Fix: Remove variable shadowing and private method calls
Add: Joystick process status indicator in developer panel
Improve: Show individual process status with colored indicators
```

---

## 다음 작업 계획

### 1. WebRTC 실시간 스트리밍 (우선순위: 높음)
- [ ] comma 기기에서 카메라 스트림 WebRTC로 전송
- [ ] 안드로이드 앱에서 WebRTC 수신 및 표시
- [ ] 저지연 최적화 (목표: 100-200ms)
- [ ] 발열 모니터링 및 자동 화질 조절

### 2. 조이스틱 기능 개선
- [ ] 조이스틱 하드웨어 연결 상태 표시
- [ ] 조이스틱 입력 캘리브레이션 UI
- [ ] 커스텀 버튼 매핑 기능

### 3. 안정성 개선
- [ ] 프로세스 크래시 자동 복구
- [ ] 네트워크 끊김 시 안전 모드
- [ ] 로그 수집 및 디버깅 도구

---

## 참고 문서

- [JOYSTICK_CONTROLS.md](./JOYSTICK_CONTROLS.md) - 조이스틱 제어 사용 가이드
- [JOYSTICK_SMOOTHING.md](./JOYSTICK_SMOOTHING.md) - 민감도 설정 가이드
- [openpilot 공식 문서](https://github.com/commaai/openpilot)

---

## 연락처 및 지원

**GitHub Issues:** https://github.com/jominki354/openpilot/issues
**브랜치:** j-st-s

---

*Last Updated: 2025-11-11*
*Version: 1.0*
