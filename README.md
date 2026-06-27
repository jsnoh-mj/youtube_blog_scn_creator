# 🏔️ YouTube Blog Scene Creator v4.0

**완벽하게 명확한 구조**

instructions.md (App 전체) | 자동 Knowledge 업데이트 | 여행별 독립 관리

---

## 🎯 명확한 구조

### 📋 instructions.md (App 전체 단위)
```
Local:    main.py 위치에 instructions.md
Git:      git_workspace/instructions.md

User이 수정하는 위치: 로컬 또는 GitHub
```

**구조:**
```markdown
## Current feedback and request
(User가 여기에 새로운 요청 입력)

## Previous - 1 feedback and request
(이전 1회차 - 참조용)

## Previous - 2 feedback and request
(이전 2회차 - 참조용)

## Previous - 3 feedback and request
(이전 3회차 - 참조용)
```

### 📚 knowledge.md (App 전체 단위)
```
Git:      git_workspace/knowledge.md

특징:     자동 업데이트 (User 편집 불가)
목적:     모든 여행의 누적 방법론
```

### 📁 여행별 프로젝트
```
Local:    projects/{여행명}/
Git:      (동기화 안 함, 로컬만 관리)

특징:     각 여행마다 독립적인 filelist, iteration_log
```

---

## 🚀 사용 방법

### Step 1️⃣: instructions.md 수정

**로컬:**
```bash
# main.py와 같은 위치
instructions.md
```

**또는 GitHub:**
```
https://github.com/username/repo/blob/main/instructions.md
```

**수정 내용:**
```markdown
## Current feedback and request

요청: DJI 카메라 정보를 knowledge에 추가하세요
- DJI가 붙은 것 → Action6로 촬영
- VID가 붙은 것 → Insta360 계열
- 정보 없으면 → 휴대폰 촬영

추가 가이드:
- 블로그: 사진 20~40장
- 유튜브: 주제 1~2개
```

### Step 2️⃣: 실행

```bash
python main.py

📁 여행 미디어 폴더 입력: D:\여행\태백산
```

### Step 3️⃣: 자동 처리

```
[1] Git에서 instructions.md pull (최신 feedback 반영)
[2] "Current feedback and request" 추출
[3] AI가 feedback 반영하여 콘텐츠 생성
[4] knowledge.md 자동 업데이트 (AI 협업)
[5] instructions.md 피드백 로테이션 (feedback 있었을 때만)
[6] Git에 업로드 (knowledge.md + instructions.md)
```

---

## 📊 파일 구조

```
로컬:
  .
  ├── main.py
  ├── config.json
  ├── instructions.md              ← ⭐ User가 수정 (App 전체)
  │
  ├── projects/
  │   ├── 태백산_절골/
  │   │   ├── filelist.md
  │   │   ├── iteration_log.md
  │   │   └── 태백산____20260627-143025.md
  │   └── 설악산_대청봉/
  │       ├── filelist.md
  │       ├── iteration_log.md
  │       └── ...
  │
  └── git_workspace/
      ├── instructions.md          (Git 사본)
      ├── knowledge.md             (자동 업데이트)
      ├── main.py                  (선택)
      └── 결과 파일들

GitHub:
  repository/
  ├── instructions.md              ← ⭐ User가 수정 (또는 로컬)
  ├── knowledge.md                 (자동 동기화)
  └── main.py                      (선택)
```

---

## 🔄 워크플로우 예제

### 회차 1 (첫 실행, feedback 있음)

```
1. instructions.md 수정 (로컬 또는 GitHub)
   Current feedback: "DJI 카메라 구분 정보 추가"
   
2. python main.py 실행
   
3. App 처리:
   - Git에서 instructions.md pull
   - Current feedback 추출
   - AI 반영
   - knowledge.md 업데이트
   - Current → Previous 1로 로테이션
   - Git에 업로드
```

### 회차 2 (feedback 있음)

```
1. instructions.md 수정
   Current feedback: "블로그 글자 크기 더 크게"
   Previous 1: (회차 1 내용 - 참조용, 처리 안 함)
   
2. python main.py 실행
   
3. App 처리:
   - "블로그 글자 크기" 만 처리
   - knowledge.md 업데이트
   - Current → Previous 1
   - Previous 1 → Previous 2
   - Git에 업로드
```

### 회차 3 (feedback 없음)

```
1. instructions.md 비워둠
   Current feedback: (비어있음)
   
2. python main.py 실행
   
3. App 처리:
   - feedback 없으므로 기본 방식
   - knowledge.md 업데이트
   - instructions.md 로테이션 스킵 (feedback 없었으므로)
   - Git에는 instructions.md 업로드하지 않음 (knowledge.md만)
```

---

## 💡 핵심 규칙

| 상황 | 동작 |
|------|------|
| **Current feedback 있음** | 로테이션 실행 + instructions.md push |
| **Current feedback 없음** | 로테이션 스킵 + instructions.md push 안 함 |
| **Previous 1/2/3** | 참조용만 (처리하지 않음) |
| **knowledge.md** | 항상 자동 업데이트 + push |

---

## ✨ 특징

✅ **명확함** - instructions.md는 로컬 main.py 위치 또는 GitHub  
✅ **App 전체** - 여행별 아님, 앱 전체 피드백 관리  
✅ **자동화** - feedback 로테이션 자동, 최대 3개 이력  
✅ **선택적** - feedback 없으면 로테이션 스킵  
✅ **누적** - knowledge.md가 모든 여행의 경험 축적  

---

## 🎯 User Checklist

- [ ] GitHub에서 project_instructions.md 삭제 (이미 하셨을 것 같음)
- [ ] instructions.md가 로컬/Git에 있는가?
- [ ] config.json 설정 완료?
- [ ] python main.py 실행 시작!

---

## 🚀 다음 단계

1. `instructions.md` 수정 (로컬 또는 GitHub)
2. `python main.py 실행`
3. 완료!
4. 반복...

---

**완벽하게 명확한 구조입니다!** 🎯
