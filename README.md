# 🏔️ 여행 콘텐츠 AI 오케스트레이터 v2.0

여행의 사진/영상에서 **유튜브 시나리오**와 **네이버 블로그 초안**을 자동으로 생성합니다.

**여행별 독립 관리** | **누적 방법론** | **완벽한 Charset 처리**

---

## 🎯 v2.0 주요 개선사항

### 1️⃣ **여행별 독립 관리**
```
projects/
├── 태백산_절골/              ← 여행 1
│   ├── filelist.md
│   ├── project_instructions.md
│   ├── iteration_log.md
│   ├── 태백산____20260627-143025.md
│   └── ...
│
└── 설악산_대청봉/            ← 여행 2 (독립)
    ├── filelist.md
    ├── project_instructions.md
    └── ...
```

**특징:**
- media directory 변경 → 새로운 여행 프로젝트 자동 시작
- 이전 여행 데이터는 자동으로 격리 (삭제 안 함)
- 여행별 독립적인 반복 개선 가능

### 2️⃣ **누적된 제작 방법론 (Knowledge.md)**
```
git_workspace/knowledge.md  ← 모든 여행에서 학습한 방법론
```

- 여행 1 완료 → 발견사항을 knowledge.md에 추가
- 여행 2 시작 → AI가 이전 경험을 자동 반영
- 계속 누적 → AI 품질 향상

### 3️⃣ **완벽한 Charset 처리** ✅
```python
# UTF-8 명시 (Windows ↔ Mac/Linux 호환)
with open(file, "r", encoding="utf-8") as f: ...
subprocess.run(..., encoding="utf-8")
```

해결된 문제:
- ❌ UnicodeDecodeError
- ❌ Korean character encoding error  
- ❌ App thread crash

---

## 📋 빠른 시작

### 1️⃣ 필수 준비
```bash
# Google Gemini API 키 발급
# → GEMINI_API_GUIDE.md 참고

# GitHub PAT 발급  
# → GITHUB_PAT_GUIDE.md 참고

# config.json 설정
# → 발급받은 키/PAT 입력
```

### 2️⃣ 실행
```bash
python main.py

📁 여행 미디어 폴더의 전체 경로를 입력하세요
D:\여행사진\태백산  ← 입력

✅ 결과 생성!
```

### 3️⃣ 반복 개선
```bash
# 1. project_instructions.md 수정 (피드백 추가)
# 2. python main.py 다시 실행
# 3. 2회차 결과 확인
```

---

## ⚙️ config.json 설정

```json
{
  "gemini_api_key": "AIzaSy_실제_키",
  "git_repo_url": "https://github.com/username/repo.git",
  "git_pat": "ghp_실제_PAT",
  "git_work_dir": "./git_workspace",
  "projects_dir": "./projects",
  "temperature": 0.3
}
```

---

## 📁 폴더 구조

```
.
├── main.py                 # 메인 스크립트
├── config.json             # 설정 (Git 제외) 🔒
├── projects/               # 여행별 프로젝트 (Git 제외)
│   ├── 태백산_절골/
│   │   ├── filelist.md
│   │   ├── project_instructions.md
│   │   ├── 태백산____20260627-143025.md
│   │   └── ...
│   └── 설악산_대청봉/
│
└── git_workspace/          # Git 저장소
    ├── knowledge.md        # 누적 방법론 (Git 동기화) ⭐
    ├── main.py             # (선택) Git 동기화
    └── 태백산____*.md      # (선택) 결과 파일
```

---

## 🔄 워크플로우

### 같은 여행 반복 개선
```
1회차 결과 검토
    ↓
project_instructions.md 피드백 추가
    ↓
python main.py 재실행 (같은 폴더)
    ↓
2회차 결과 생성
```

### 다른 여행 시작
```
python main.py 실행
    ↓
다른 media directory 입력
    ↓
새 프로젝트 자동 생성
    ↓
이전 여행 정보는 격리 (안전)
    ↓
knowledge.md는 계속 누적 (AI 학습)
```

---

## 📚 Knowledge.md 관리

### 자동 생성 (첫 clone 시)
```
git_workspace/knowledge.md
├── 유튜브 시나리오 제작 팁
├── 네이버 블로그 제작 팁
├── 여행지 특수 사항
└── 피해야 할 방법들
```

### 사용자 수정
```markdown
## 산/협곡/높은 곳
- 상승 장면은 숨 고르는 컷으로 자르기
- 정상 도착 장면은 3초 이상 홀드
- 하강 장면은 빠르게 편집 (엔드러시 효과)
```

### 다음 여행에 자동 반영
- AI가 knowledge.md를 읽고 반영
- 여행이 거듭될수록 품질 향상

---

## 🛡️ 보안 (완벽히 해결됨)

### Git 제외 (안전함)
- ✅ config.json (API 키 보호)
- ✅ projects/ (개인 여행 데이터)

### Git 동기화
- ⭐ knowledge.md (누적 경험)
- (선택) main.py
- (선택) 결과 파일

---

## 📊 실행 예시

```
🏔️ 여행 콘텐츠 AI 오케스트레이터 v2.0

[0/4] 프로젝트 디렉토리 초기화 중...
    → 새 프로젝트 폴더 생성: ./projects/태백산_절골/

[1/4] 미디어 스캔 중...
    → 12개 파일 스캔 완료

[2/4] 프로젝트 지침 파일 확인 중...
    → 템플릿 생성됨 (내용 입력 필요)
    → 현재 1회차 실행

[3/4] Gemini AI 호출 중... (1~2분)

[4/4] 결과 저장 중...
    → projects/태백산_절골/태백산____20260627-143025.md

[5/4] Git 업로드 중...
    main.py도 함께 push? (y/n): y
    → Push 완료 ✅

✅ 1회차 완료!
📁 프로젝트: ./projects/태백산_절골
📄 결과: 태백산____20260627-143025.md
📚 방법론: knowledge.md (자동 동기화)
🔁 개선: project_instructions.md 수정 → 재실행
```

---

## 🔧 트러블슈팅

### Charset 에러 (해결됨!)
```
v2.0에서 모든 파일 I/O에 encoding="utf-8" 명시
Windows ↔ Mac/Linux 완벽 호환 ✅
```

### "Git에 projects가 올라갔다"
```bash
git rm -r --cached projects/
git commit -m "Remove projects"
git push
```

### knowledge.md 동기화 안 됨
```bash
cd git_workspace
git add knowledge.md
git commit -m "Update knowledge"
git push
```

---

## 📚 가이드

- [Gemini API 발급](./GEMINI_API_GUIDE.md)
- [GitHub PAT 발급](./GITHUB_PAT_GUIDE.md)

---

## ✨ v1.0 vs v2.0

| 기능 | v1.0 | v2.0 |
|------|------|------|
| 여행별 독립 관리 | ❌ | ✅ |
| 누적 방법론 (Knowledge) | ❌ | ✅ |
| 여행 변경 시 정보 격리 | ❌ | ✅ |
| Charset 완벽 처리 | ⚠️ | ✅ |
| 반복 개선 | ✅ | ✅ |
| Git 자동화 | ✅ | ✅ |

---

## 🎯 주요 특징

✅ **여행별 완전 격리** - 잘못된 정보 제거 자동화  
✅ **누적 경험 관리** - Knowledge.md로 AI 성장  
✅ **완벽한 Charset** - 모든 OS에서 안정적  
✅ **Git 안전성** - 민감 정보 자동 제외  
✅ **반복 개선** - 무한정 개선 가능  

---

**Happy Content Creation! 🎬📸**
