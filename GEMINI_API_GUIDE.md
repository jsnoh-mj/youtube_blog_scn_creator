# 🔑 Google Gemini API 키 발급 가이드

Google Gemini API는 Google의 최신 생성형 AI 모델로, 무료로 시작할 수 있습니다.

---

## 📱 발급 단계별 가이드

### **Step 1: Google AI Studio 접속**
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. Google 계정으로 로그인 (없으면 가입)

```
https://aistudio.google.com/app/apikey
```

---

### **Step 2: API 키 생성**

Google AI Studio 페이지에서:
1. 좌측 메뉴에서 **[API keys]** 클릭
2. 또는 페이지 우측에 **[Get API key]** 버튼 보임
3. **[Create API key]** 또는 **[Create API key in new project]** 클릭

```
┌─────────────────────────────────┐
│ API keys                         │
├─────────────────────────────────┤
│                                 │
│ [+ Create API key]              │
│    ↓                            │
│ [Create API key in new project] │
│                                 │
└─────────────────────────────────┘
```

---

### **Step 3: 프로젝트 선택** (처음인 경우)

```
Choose a project (or create a new one):

☐ Create new project ← 체크
  Project name: [________________]
         기본값: "My Project" (그대로 둘 수 있음)

[Create API key]
```

기존 프로젝트가 있다면:
```
☐ Select an existing project ← 체크
  
  Project: [My Project ▼]

[Create API key]
```

---

### **Step 4: API 키 확인**

```
✅ API key created successfully!

┌──────────────────────────────────┐
│ AIzaSy1a2b3c4d5e6f7g8h9i0j1k2l3  │
│                        [복사 아이콘] │
└──────────────────────────────────┘

Status: ✅ Active
Created: 2026-06-27 14:30:00 UTC
```

---

## 💾 API 키 복사 & 저장

```
┌──────────────────────────────────────────┐
│ AIzaSy1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7 │
│                              [복사 아이콘] │
└──────────────────────────────────────────┘
```

**⚠️ 주의:**
- API 키를 복사하면 안전한 곳에 저장하세요
- 다른 사람과 절대 공유하지 마세요
- GitHub에 올리지 마세요

---

## 📊 사용 한도 확인

Google AI Studio에서 **[Usage]** 탭 클릭:

```
Month: June 2026
Total requests: 10 / 1,500
Quota remaining: 1,490

사용량
├── Requests: 10
├── Input tokens: 1,234
├── Output tokens: 567
└── Status: ✅ Under limit
```

**무료 한도:**
- 월 1,500 요청까지 무료
- 분당 요청 수 제한 있음 (충분함)

---

## 💾 config.json에 입력

API 키를 발급받은 후:

```json
{
  "gemini_api_key": "AIzaSy1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7",
  "gemini_model": "gemini-2.5-flash",
  "git_repo_url": "https://github.com/username/repo.git",
  "git_pat": "ghp_...",
  "git_work_dir": "./git_workspace",
  "output_dir": ".",
  "temperature": 0.3
}
```

---

## ✅ API 키 확인 체크리스트

- [ ] API 키가 `AIzaSy`로 시작하는가?
- [ ] API 키를 config.json에 입력했는가?
- [ ] config.json을 git에 올리지 않기로 약속했는가? 🔒
- [ ] Usage에서 요청이 정상 작동하는가?

---

## 📈 모델 정보

현재 사용 모델: **`gemini-2.5-flash`**

```
모델명        | 특징          | 용도
─────────────────────────────────────────
gemini-2.5    | 고품질        | 복잡한 작업
gemini-2-flash| 빠르고 저렴   | 일반 작업 (현재)
gemini-1.5    | 이전 버전     | (권장 안 함)
```

**왜 gemini-2.5-flash?**
- ⚡ 빠른 응답 (1~2분)
- 💰 무료 한도에서 충분한 성능
- 🎯 여행 콘텐츠 생성에 최적화

---

## 🛡️ 보안 주의사항

✅ **해야 할 것:**
- API 키를 안전한 파일에만 저장
- config.json은 .gitignore에 추가
- 정기적으로 key rotation (필요시)
- Usage를 주기적으로 확인

❌ **하지 말아야 할 것:**
- API 키를 이메일/채팅으로 전송
- 공개 저장소에 키 업로드
- 소스 코드에 하드코딩
- 다른 사람과 키 공유

---

## 🔄 API 키 재발급 (잃어버렸을 경우)

1. [Google AI Studio - API Keys](https://aistudio.google.com/app/apikey) 접속
2. 기존 API 키 찾기
3. 오른쪽 메뉴에서 **[Delete]** 클릭
4. 위의 Step 2부터 다시 시작

---

## 🆘 트러블슈팅

### "400 Bad Request" 에러
→ API 키가 올바른지 확인  
→ API 키가 활성화되었는지 확인

### "429 Too Many Requests" 에러
→ 분당 요청 수가 초과됨
→ 몇 초 기다린 후 재시도

### "Quota exceeded" 에러
→ 월간 1,500 요청 초과
→ 다음 달을 기다리거나 유료 전환

### "Invalid API key" 에러
→ 복사-붙여넣기 시 공백이 있는지 확인
→ API 키가 완전히 입력되었는지 확인

---

## 📚 참고자료

- [Google AI Studio](https://aistudio.google.com)
- [Gemini API 문서](https://ai.google.dev/)
- [API 요금제](https://ai.google.dev/pricing)

---

## 💡 팁

### 여러 프로젝트 관리 시
- 프로젝트마다 별도의 API 키 생성 가능
- API 키 이름으로 용도 표시
  - `travel-content-ai`
  - `blog-generator`
  - 등등

### 개발 & 운영 분리
- 개발용 API 키
- 운영용 API 키
- 각각 따로 관리 (보안 강화)

---

## 🎯 다음 단계

1. ✅ API 키 발급 완료
2. ✅ config.json에 입력
3. ✅ GitHub PAT도 발급받기
4. ✅ main.py 실행 준비 완료!
