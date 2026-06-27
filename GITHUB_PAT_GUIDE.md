# 🔑 GitHub PAT (Personal Access Token) 발급 가이드

GitHub Personal Access Token은 명령줄에서 GitHub 계정으로 인증할 때 사용하는 보안 토큰입니다.

---

## 📱 발급 단계별 가이드

### **Step 1: GitHub 로그인**
1. [GitHub](https://github.com) 접속
2. 우측 상단 프로필 아이콘 클릭
3. **Settings** 클릭

```
프로필 아이콘 ▼
├── Your repositories
├── Your projects
├── Your stars
├── Settings ← 여기 클릭
└── ...
```

---

### **Step 2: Developer settings 이동**
Settings 페이지 좌측 메뉴 하단에서:
1. **Developer settings** 클릭
2. 펼쳐진 메뉴에서 **Personal access tokens** 클릭
3. **Tokens (classic)** 선택

```
좌측 메뉴
├── Account
├── Security
├── Notifications
├── ...
└── Developer settings ← 클릭
   └── Personal access tokens
      ├── Tokens (classic) ← 선택
      └── Fine-grained tokens
```

---

### **Step 3: 새 토큰 생성**
1. **Generate new token** 버튼 클릭
2. **Generate new token (classic)** 선택

```
[Generate new token] 드롭다운 ▼
├── Generate new token (classic) ← 여기
└── Generate new token (fine-grained)
```

---

### **Step 4: 토큰 정보 입력**

| 항목 | 입력값 | 설명 |
|------|--------|------|
| **Note** | `travel-content-ai` | 토큰 이름 (무엇에 사용하는지 표시) |
| **Expiration** | 90 days | 만료 기간 (기본값: 90일) |

```
Note (필수):
  [____________________]  ← "travel-content-ai" 입력

Expiration (필수):
  [90 days ▼]  ← 기간 선택
    - 7 days
    - 30 days
    - 60 days
    - 90 days ← 권장
    - 1 year
    - No expiration (비권장)
```

---

### **Step 5: 권한(Scopes) 선택** ⭐ **중요**

아래 체크박스 중 **`repo`** 만 선택:

```
☑ repo ← 반드시 체크 (전체 저장소 접근)
  ├── ☑ repo:status
  ├── ☑ repo_deployment
  ├── ☑ public_repo
  ├── ☑ repo:invite
  ├── ☑ security_events
  └── ... (자동으로 세부 권한 활성화)

□ workflow
□ write:packages
□ read:packages
□ delete:packages
□ (나머지는 체크 안 함)
```

**왜 `repo`만?**
- `repo`: GitHub 저장소에 대한 모든 접근 권한
- 이 프로젝트는 저장소에 파일을 push하기만 하므로 충분

---

### **Step 6: 토큰 생성**
1. 페이지 하단 **[Generate token]** 버튼 클릭
2. GitHub 비밀번호 입력 (2FA 사용 시 추가 인증)
3. 토큰이 생성됨

```
✅ Personal access token created!

ghp_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r ← 토큰 표시
```

---

### **Step 7: 토큰 복사 & 저장** ⚠️ **중요**

```
┌─────────────────────────────────────────────────┐
│ ghp_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r       │
│                                        [복사 아이콘] │
└─────────────────────────────────────────────────┘
```

**⚠️ 주의:**
- 토큰은 이 페이지를 벗어나면 **다시 볼 수 없습니다!**
- 반드시 복사해서 안전한 곳에 저장하세요
- 브라우저 탭을 닫기 전에 복사!

---

## 💾 토큰 저장하기

### 옵션 1️⃣: 메모장에 임시 저장
```
1. 메모장 열기
2. 토큰 붙여넣기
3. config.json에 입력 후 삭제
```

### 옵션 2️⃣: 직접 config.json에 입력
```json
{
  "git_pat": "ghp_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r",
  ...
}
```

---

## ✅ 확인 체크리스트

- [ ] PAT가 `ghp_`로 시작하는가?
- [ ] `repo` 권한만 체크했는가?
- [ ] 토큰을 config.json에 입력했는가?
- [ ] **config.json을 git에 올리지 않겠다고 약속했는가?** 🔒

---

## 🔄 토큰 재발급 (잃어버렸을 경우)

1. GitHub Settings → Developer settings → Personal access tokens
2. 기존 토큰 옆 **[Delete]** 클릭
3. 위의 Step 3부터 다시 시작

---

## 🛡️ 보안 주의사항

✅ **해야 할 것:**
- 토큰을 정기적으로 갱신 (90일마다)
- 토큰을 GitHub에 올리지 않기
- 불필요한 권한은 체크하지 않기
- 사용하지 않는 토큰은 삭제하기

❌ **하지 말아야 할 것:**
- 토큰을 이메일로 전송
- 토큰을 채팅/메신저로 공유
- 토큰을 공개 저장소에 업로드
- 토큰을 만료 없음으로 설정
- 불필요한 권한 부여

---

## 📝 config.json 최종 입력

PAT를 발급받은 후:

```json
{
  "gemini_api_key": "AIzaSy...",
  "gemini_model": "gemini-2.5-flash",
  "git_repo_url": "https://github.com/username/repo.git",
  "git_pat": "ghp_발급받은_토큰_입력_여기",
  "git_work_dir": "./git_workspace",
  "output_dir": ".",
  "temperature": 0.3
}
```

✅ 모든 준비 완료!

---

## 🆘 트러블슈팅

### "401 Unauthorized" 에러
→ PAT가 올바른지 확인  
→ git_repo_url이 정확한지 확인

### "token has expired" 에러
→ 새로운 PAT 발급

### "permission denied" 에러
→ PAT의 `repo` 권한이 체크되었는지 확인  
→ 저장소의 권한 설정 확인

---

## 📚 참고자료

- [GitHub 공식 문서 - Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub 공식 문서 - Creating a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
