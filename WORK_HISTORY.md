# Joystick Control Project - Work History

## 세션 요약 (2025-11-11)

### 완료된 작업

#### 1. 빌드 에러 수정
**문제:**
- `developer_panel.cc` 파일 첫 줄에 한글 문자 'ㅇ' 포함
- 변수 shadowing 에러 (presetDefault, presetSoft, etc.)
- `refresh()` private 메서드 호출 에러
- `get_bool` → `getBool` 메서드명 오류

**해결:**
```bash
커밋: e3bf246 - Fix: Remove invalid character from developer_panel.cc
커밋: d9a8a91 - Fix: Remove variable shadowing and private method calls
커밋: 1907e6e - Fix: Use getBool instead of get_bool
```

#### 2. UI 개선 - 프리셋 버튼 색상 표시
**기능:**
- 선택된 프리셋 버튼을 초록색으로 표시
- 값 변경 시 UI 즉시 업데이트
- `JoystickPreset` 파라미터로 현재 프리셋 저장

**구현:**
```cpp
void DeveloperPanel::updatePresetButtons() {
  // 활성 프리셋: #33Ab4C (초록색)
  // 비활성 프리셋: #393939 (회색)
}

void DeveloperPanel::updateValueControls() {
  // hide/show로 강제 UI 리프레시
}
```

```bash
커밋: c1cf1ae - Add: Preset button color highlight and instant UI update
```

#### 3. 프로세스 실행 조건 수정
**문제:**
- 조이스틱 디버그 모드 활성화 후 크루즈 인게이지 시 "프로세스가 실행되지 않았습니다 joystickd" 에러
- `started` 조건 때문에 크루즈 인게이지 전에 joystickd가 실행되지 않음

**해결:**
```python
# Before
def joystick(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started and params.get_bool("JoystickDebugMode")

# After
def joystick(started: bool, params: Params, CP: car.CarParams) -> bool:
  return params.get_bool("JoystickDebugMode")
```

```bash
커밋: 8560838 - Fix: Allow joystickd to run before cruise engage
```

#### 4. 프로세스 상태 표시 UI 추가
**기능:**
- joystickd 프로세스 상태 실시간 표시
- joystick_control 프로세스 상태 실시간 표시
- 1초마다 자동 업데이트
- 색상 인디케이터 (🟢 ON / 🔴 OFF)

**구현:**
```cpp
// 두 개의 개별 상태 표시
joystickdStatus = new LabelControl(tr("  joystickd"), tr("OFF"), ...);
joystickControlStatus = new LabelControl(tr("  joystick_control"), tr("OFF"), ...);

// 1초마다 업데이트
statusTimer = new QTimer(this);
statusTimer->start(1000);
```

```bash
커밋: 940fdfb - Add: Joystick process status indicator in developer panel
커밋: 83b70eb - Improve: Show individual process status with colored indicators
```

---

## 기술적 결정 사항

### 1. 프로세스 실행 타이밍
**결정:** joystickd를 차량 연결 시 즉시 실행 (크루즈 인게이지 전)  
**이유:** 크루즈 인게이지 시 joystickd가 준비되어 있어야 타이밍 문제 없음

### 2. UI 업데이트 방식
**결정:** hide/show 방식으로 강제 리프레시  
**이유:** CValueControl의 refresh() 메서드가 private이라 직접 호출 불가

### 3. 프로세스 상태 확인 방법
**결정:** ManagerState 파라미터 파싱  
**이유:** 실시간으로 모든 프로세스 상태를 확인할 수 있는 가장 간단한 방법

### 4. 프리셋 저장 방식
**결정:** JoystickPreset 파라미터에 문자열로 저장  
**이유:** 재부팅 후에도 선택된 프리셋 유지 가능

---

## 발견된 이슈 및 해결

### 이슈 1: numpy 모듈 없음
**발견:** SSH로 joystickd.py 실행 시 "ModuleNotFoundError: No module named 'numpy'"  
**상태:** 오진단 - 실제로는 numpy 없이 이미 구현되어 있었음  
**교훈:** 기기에서 직접 테스트하기 전에 코드 먼저 확인

### 이슈 2: SSH 연결 실패
**원인:** IP 주소 변경 (192.168.137.47 → 172.30.1.39)  
**해결:** ssh_key.pem 사용하여 연결  
**명령:** `ssh -i ssh_key.pem comma@172.30.1.39`

### 이슈 3: ADB 연결 불가
**원인:** 기기 재부팅 중 또는 USB 연결 끊김  
**해결:** SSH로 대체 사용

---

## 코드 변경 요약

### 수정된 파일
```
openpilot/selfdrive/ui/qt/offroad/developer_panel.cc
openpilot/selfdrive/ui/qt/offroad/developer_panel.h
openpilot/system/manager/process_config.py
openpilot/tools/joystick/joystickd.py (numpy 제거 - 이미 완료됨)
```

### 추가된 기능
1. 프리셋 버튼 색상 표시
2. UI 즉시 업데이트
3. 프로세스 상태 실시간 모니터링
4. 개별 프로세스 상태 표시

### 수정된 버그
1. 빌드 에러 (문자 인코딩, 변수 shadowing, 메서드명)
2. 프로세스 실행 타이밍 문제
3. UI 업데이트 지연 문제

---

## 테스트 체크리스트

### 기본 기능
- [x] 조이스틱 모드 토글 동작
- [x] 민감도 설정 토글 동작
- [x] 프리셋 버튼 클릭 시 값 적용
- [x] 프리셋 버튼 색상 변경
- [x] 슬라이더 값 변경 시 즉시 반영
- [ ] 차량 연결 시 joystickd 자동 실행
- [ ] 크루즈 인게이지 시 조이스틱 제어 동작

### UI 표시
- [x] 프로세스 상태 표시 (joystickd)
- [x] 프로세스 상태 표시 (joystick_control)
- [x] 1초마다 자동 업데이트
- [x] 색상 인디케이터 표시

### 빌드 및 배포
- [x] 로컬 빌드 성공
- [x] 기기 빌드 성공
- [x] Git 커밋 및 푸시
- [x] 기기에 자동 배포

---

## 알려진 제한사항

1. **프로세스 상태 확인 정확도**
   - ManagerState 문자열 파싱 방식이라 100% 정확하지 않을 수 있음
   - 개선 방안: managerState 메시지를 직접 파싱

2. **UI 업데이트 방식**
   - hide/show 방식이 약간 비효율적
   - 개선 방안: CValueControl에 public refresh() 메서드 추가

3. **조이스틱 하드웨어 연결 상태**
   - 현재는 프로세스 실행 여부만 확인
   - 개선 방안: 실제 조이스틱 디바이스 연결 상태 확인

---

## 다음 세션 작업 제안

### 우선순위 1: WebRTC 스트리밍
**목표:** 안드로이드 앱에서 comma 전방 화면 실시간 표시  
**요구사항:**
- 저지연 (100-200ms)
- 저화질 옵션 (640x480 @ 30fps)
- 발열 최소화
- 적응형 비트레이트

**작업 항목:**
1. webrtcd 프로세스 활성화 및 설정
2. 카메라 스트림 WebRTC로 전송
3. 안드로이드 WebRTC 클라이언트 구현
4. 지연시간 최적화
5. 발열 모니터링 및 자동 조절

### 우선순위 2: 조이스틱 기능 개선
1. 조이스틱 하드웨어 연결 상태 표시
2. 조이스틱 입력 캘리브레이션 UI
3. 커스텀 버튼 매핑 기능
4. 조이스틱 입력 시각화 (디버깅용)

### 우선순위 3: 안정성 개선
1. 프로세스 크래시 자동 복구
2. 네트워크 끊김 시 안전 모드
3. 로그 수집 및 디버깅 도구
4. 에러 메시지 개선

---

## 참고 명령어

### 기기 접속
```bash
# SSH
ssh -i ssh_key.pem comma@172.30.1.39

# ADB
adb shell
```

### 코드 배포
```bash
# 로컬에서 푸시
git push origin j-st-s

# 기기에서 업데이트
ssh -i ssh_key.pem comma@172.30.1.39 "cd /data/openpilot && git fetch origin && git reset --hard origin/j-st-s && sudo reboot"
```

### 디버깅
```bash
# 빌드 에러 확인
ssh -i ssh_key.pem comma@172.30.1.39 "ps aux | grep -i build"

# 프로세스 확인
ssh -i ssh_key.pem comma@172.30.1.39 "ps aux | grep joystick"

# 로그 확인
ssh -i ssh_key.pem comma@172.30.1.39 "journalctl -u comma -n 100 --no-pager"
```

---

## 커밋 히스토리

```
83b70eb - Improve: Show individual process status with colored indicators
1907e6e - Fix: Use getBool instead of get_bool
940fdfb - Add: Joystick process status indicator in developer panel
8560838 - Fix: Allow joystickd to run before cruise engage
c1cf1ae - Add: Preset button color highlight and instant UI update
d9a8a91 - Fix: Remove variable shadowing and private method calls
e3bf246 - Fix: Remove invalid character from developer_panel.cc
```

---

*Session Date: 2025-11-11*  
*Total Commits: 7*  
*Files Modified: 3*  
*Lines Changed: ~200*
