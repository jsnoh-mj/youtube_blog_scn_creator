import os
import sys
import json
import datetime
import subprocess
import shutil
import re
import cv2
from pathlib import Path
from google import genai
from google.genai import types


# ─────────────────────────────────────────────
#  설정 로더
# ─────────────────────────────────────────────
def load_config(config_path: str = "config.json") -> dict:
    """config.json을 읽어 설정값을 반환합니다."""
    if not os.path.exists(config_path):
        template = {
            "gemini_api_key": "여기에_실제_AIzaSy_API_키를_입력하세요",
            "gemini_model": "gemini-1.5-flash",
            "git_repo_url": "https://github.com/username/repo.git",
            "git_pat": "ghp_여기에_실제_GitHub_PAT_토큰을_입력하세요",
            "git_work_dir": "./git_workspace",
            "projects_dir": "./projects",
            "output_dir": ".",
            "temperature": 0.3
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        print(f"[!] '{config_path}' 파일이 없어 템플릿을 생성했습니다.")
        sys.exit(0)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    required_keys = ["gemini_api_key", "git_repo_url", "git_pat", "git_work_dir"]
    for key in required_keys:
        if key not in cfg or not cfg[key]:
            print(f"[오류] config.json에 '{key}' 값이 없습니다.")
            sys.exit(1)

    if "AIzaSy" not in cfg["gemini_api_key"] and cfg["gemini_api_key"].startswith("여기에"):
        print("[오류] config.json의 gemini_api_key를 실제 키로 교체해 주세요.")
        sys.exit(1)

    if cfg["git_pat"].startswith("ghp_여기에") or cfg["git_pat"].startswith("여기에"):
        print("[오류] config.json의 git_pat를 실제 GitHub PAT로 교체해 주세요.")
        sys.exit(1)

    if "github.com" not in cfg["git_repo_url"]:
        print("[오류] config.json의 git_repo_url이 유효하지 않습니다.")
        sys.exit(1)

    return cfg


def input_target_dir() -> str:
    """사용자로부터 타겟 폴더 경로를 입력받습니다."""
    while True:
        target = input("\n📁 여행 미디어 폴더의 전체 경로를 입력하세요\n   (예: D:\\여행사진\\태백산): ").strip()
        target = target.strip('"').strip("'")
        
        if not target:
            print("   [경고] 경로를 입력해 주세요.")
            continue
        if not os.path.exists(target):
            print(f"   [경고] 해당 경로가 없습니다: {target}")
            continue
        if not os.path.isdir(target):
            print(f"   [경고] 파일이 아닌 폴더 경로를 입력해 주세요.")
            continue
        
        return target


# ─────────────────────────────────────────────
#  여행 콘텐츠 오케스트레이터 v4.1 최종
# ─────────────────────────────────────────────
class TravelContentOrchestrator:
    def __init__(self, cfg: dict, target_dir: str):
        self.cfg = cfg
        self.target_dir = target_dir
        self.projects_dir = cfg.get("projects_dir", "./projects")
        self.model_name = cfg.get("gemini_model", "gemini-1.5-flash")
        self.temperature = cfg.get("temperature", 0.3)
        
        self.git_repo_url = cfg.get("git_repo_url")
        self.git_pat = cfg.get("git_pat")
        self.git_work_dir = cfg.get("git_work_dir", "./git_workspace")

        self.folder_name = os.path.basename(self.target_dir.rstrip(os.sep))
        self.project_dir = os.path.join(self.projects_dir, self.folder_name)
        
        # App 전체 단위 파일 (local)
        self.instructions_path = "instructions.md"
        
        # Git 저장소의 instructions.md
        self.git_instructions_path = os.path.join(self.git_work_dir, "instructions.md")
        
        # 여행별 파일
        self.filelist_path = os.path.join(self.project_dir, "filelist.md")
        self.iteration_log_path = os.path.join(self.project_dir, "iteration_log.md")
        
        # 글로벌 Knowledge
        self.knowledge_path = os.path.join(self.git_work_dir, "knowledge.md")

        self.client = genai.Client(api_key=cfg["gemini_api_key"])

    # ── Git 저장소 초기화 & 동기화 ───────────────
    def init_git_repo(self) -> bool:
        """Git 저장소 초기화 및 동기화"""
        print(f"\n[Git] 저장소 동기화 중...")
        
        is_valid_git_repo = False
        if os.path.exists(self.git_work_dir):
            git_check = subprocess.run(
                ["git", "-C", self.git_work_dir, "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8"
            )
            is_valid_git_repo = (git_check.returncode == 0)
        
        if not is_valid_git_repo:
            if os.path.exists(self.git_work_dir):
                print(f"    → 손상된 Git 폴더 정리 중...")
                shutil.rmtree(self.git_work_dir)
            
            print(f"    → 저장소 복제 중...")
            auth_url = self.git_repo_url.replace("https://", f"https://{self.git_pat}@")
            result = subprocess.run(
                ["git", "clone", auth_url, self.git_work_dir],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode != 0:
                print(f"[Git Clone 실패]")
                print(f"  → URL: {self.git_repo_url}")
                print(f"  → 오류: {result.stderr}")
                return False
            print(f"    → 저장소 복제 완료")
            self._setup_gitignore()
            self._init_knowledge()
        else:
            print(f"    → 저장소 업데이트 중...")
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "pull"],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode != 0:
                print(f"[Git Pull 실패] {result.stderr}")
                return False
            print(f"    → 저장소 업데이트 완료")
        
        return True

    # ── Git에서 instructions.md pull ──────────
    def pull_instructions_from_git(self) -> bool:
        """Git에서 instructions.md를 다운로드 (App 전체 단위)"""
        print(f"\n[Git] instructions.md 동기화 중...")
        
        if not os.path.exists(self.git_instructions_path):
            print(f"    → Git에 instructions.md가 없습니다.")
            return True
        
        # Git 파일을 로컬로 복사
        shutil.copy2(self.git_instructions_path, self.instructions_path)
        print(f"    → 'instructions.md' 업데이트됨")
        
        return True

    # ── "Current feedback" 추출 ─────────────────
    def extract_current_feedback(self) -> str:
        """instructions.md에서 'Current feedback' 섹션만 추출"""
        if not os.path.exists(self.instructions_path):
            return ""
        
        with open(self.instructions_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # "## Current feedback" ~ "## Previous" 사이 추출
        pattern = r"## Current feedback.*?\n(.*?)\n## Previous"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            feedback = match.group(1).strip()
            if feedback and not feedback.startswith("("):
                return feedback
        
        return ""

    # ── 프로젝트 디렉토리 초기화 ────────────────
    def init_project_dir(self) -> bool:
        """여행 프로젝트 디렉토리를 초기화합니다."""
        if os.path.exists(self.project_dir):
            print(f"\n[0/4] 기존 프로젝트 폴더 사용: {self.project_dir}")
            return True
        
        print(f"\n[0/4] 새 프로젝트 폴더 생성: {self.project_dir}")
        try:
            os.makedirs(self.project_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"    [오류] 폴더 생성 실패: {e}")
            return False

    # ── 출력 파일명 생성 ────────────────────────
    def get_output_path(self) -> str:
        """형식: projects/{여행명}/{여행명}____YYYYMMDD-HHMMSS.md"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{self.folder_name}____{timestamp}.md"
        return os.path.join(self.project_dir, filename)

    # ── 영상 길이 추출 ──────────────────────────
    def get_video_duration(self, file_path: str) -> str:
        try:
            video = cv2.VideoCapture(file_path)
            fps = video.get(cv2.CAP_PROP_FPS)
            frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
            video.release()
            if fps > 0:
                secs = round(frames / fps, 1)
                mins = int(secs // 60)
                return f"{mins}분 {secs % 60:.0f}초" if mins > 0 else f"{secs}초"
            return "-"
        except Exception:
            return "-"

    # ── 파일명에서 설명 추출 ─────────────────────
    @staticmethod
    def extract_description(filename: str) -> str:
        """파일명에서 설명 추출"""
        name = os.path.splitext(filename)[0]
        parts = name.split("_")
        if len(parts) > 2:
            return "_".join(parts[2:])
        return name

    # ── 미디어 파일 스캔 → filelist.md ──────────
    def generate_filelist(self) -> bool:
        print(f"\n[1/4] '{self.target_dir}' 미디어 스캔 중...")
        if not os.path.exists(self.target_dir):
            print(f"[오류] 경로가 존재하지 않습니다: {self.target_dir}")
            return False

        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
        image_exts = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp"}

        all_files = sorted(
            f for f in os.listdir(self.target_dir)
            if os.path.isfile(os.path.join(self.target_dir, f)) and not f.startswith(".")
        )

        media_files = [
            f for f in all_files
            if os.path.splitext(f)[1].lower() in video_exts | image_exts
        ]

        if not media_files:
            print("[경고] 인식 가능한 미디어 파일이 없습니다.")
            return False

        md = "# 📷 여행 미디어 마스터 타임라인\n\n"
        md += f"> 스캔 경로: `{self.target_dir}`  \n"
        md += f"> 스캔 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        md += "| 순번 | 파일명 | 유형 | 재생시간 | 자동 추출 설명 |\n"
        md += "| :---: | :--- | :---: | :---: | :--- |\n"

        for idx, filename in enumerate(media_files, 1):
            full_path = os.path.join(self.target_dir, filename)
            ext = os.path.splitext(filename)[1].lower()
            f_type = "🎬 영상" if ext in video_exts else "📸 사진"
            duration = self.get_video_duration(full_path) if ext in video_exts else "-"
            desc = self.extract_description(filename)
            md += f"| {idx} | `{filename}` | {f_type} | {duration} | {desc} |\n"

        os.makedirs(self.project_dir, exist_ok=True)
        with open(self.filelist_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"    → {len(media_files)}개 파일 스캔 완료.")
        return True

    # ── 반복 회차 카운터 ─────────────────────────
    def get_iteration_count(self) -> int:
        if not os.path.exists(self.iteration_log_path):
            return 1
        with open(self.iteration_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count("## 회차")
        return count + 1

    def log_iteration(self, iteration: int, output_path: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## 회차 {iteration}\n- 실행 일시: {timestamp}\n- 출력 파일: {os.path.basename(output_path)}\n"
        with open(self.iteration_log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    # ── Gemini API 호출 ──────────────────────────
    def call_gemini(self, iteration: int, current_feedback: str) -> str | None:
        print(f"\n[3/4] Gemini AI 호출 중... (회차: {iteration})")

        with open(self.filelist_path, "r", encoding="utf-8") as f:
            filelist_content = f.read()

        knowledge_content = ""
        if os.path.exists(self.knowledge_path):
            with open(self.knowledge_path, "r", encoding="utf-8") as f:
                knowledge_content = f.read()

        system_instruction = f"""
당신의 역할:
- 경험 많은 유튜브 채널 운영자 (100만+ 구독자 수준의 전문성)
- 네이버 블로그 SEO 최적화 전문가
- 여행/등산 콘텐츠 제작 경험 10년 이상

작성 원칙:
1. 구체성: 추상적인 표현 금지. 파일명, 시간, 구체적 장면 명시
2. 실행성: 실제로 촬영된 미디어를 기반으로만 제안
3. 효과성: 각 제안마다 "왜 이렇게 하는가" 설명 포함
4. 창의성: 단순 설명이 아닌 예능적 재미 + 시청자 심리 고려

유튜브 시나리오 작성 시:
- 3초 훅은 가장 임팩트 있는 장면으로 시작
- 타임라인은 분 단위로 정확히, 어떤 파일인지 명시
- 썸네일은 실제 촬영분의 특정 장면 지정
- 각 구간의 "왜" 설명 포함 (시청자 심리 고려)

네이버 블로그 작성 시:
- 제목은 검색 최적화 + 클릭 욕구 동시 고려
- 키워드는 실제 검색량 기반 추천
- 본문은 정보성 + 감성 6:4 비율
- 소제목으로 스캔 가능한 구조 제공

[누적된 제작 방법론]
{knowledge_content if knowledge_content else "아직 누적된 방법이 없습니다. 기본 원칙을 따르세요."}

[{iteration}회차 사용자 추가 요청]
{current_feedback if current_feedback else "특별한 요청이 없습니다. 위의 원칙에 따라 전문성 있게 진행하세요."}

[분석할 미디어 타임라인]
{filelist_content}
"""

        user_prompt = f"""
당신은 경험 많은 유튜브 콘텐츠 크리에이터이자 블로그 최적화 전문가입니다.
아래 미디어 타임라인을 철저히 분석하여 구체적이고 실행 가능한 초안을 작성해주세요.

위의 미디어 타임라인을 보면서 다음 두 섹션을 상세히 작성해주세요:

===========================================================
## [SECTION 1] 📹 유튜브 시나리오 초안 (구체적, 실행 가능)
===========================================================

### 제목 후보 (클릭률 최적화)
1. 
2. 
3. 

### 썸네일 컨셉 (명확한 지시사항)
- 대문 사진: (파일명 또는 장면 설명)
- 텍스트 오버레이: 
- 색상: 
- 레이아웃:

### 3초 훅 (시청자를 멈추게 하는 임팩트)
- 오프닝 장면: (구체적인 영상/사진)
- 대사/나레이션:
- 음악/효과음:

### 전체 타임라인 (분 단위, 시각/청각 분리)

| 시간 | 영상/사진 | 나레이션/자막 | 음악 |
|------|---------|-----------|------|
| 0:00-0:03 | (구체적 파일명) | (정확한 대사) | (음악 설명) |
| ... | ... | ... | ... |

### 하이라이트 장면 TOP3 (가장 임팩트 있는 장면)
1. 장면: (파일명/시간)
   이유: 
   
2. 장면: (파일명/시간)
   이유: 
   
3. 장면: (파일명/시간)
   이유: 

### 엔딩 CTA
- 멘트:
- 화면 구성:

===========================================================
## [SECTION 2] 📝 네이버 블로그 초안 (상위 노출 최적화)
===========================================================

### 제목 (네이버 검색 최적화, 30자 이내)
제목: 

### 키워드 전략
**대표 키워드 5개:**
1. 
2. 
3. 
4. 
5. 

**롱테일 키워드 5개:**
1. 
2. 
3. 
4. 
5. 

### 본문 (1500자 이상, 정보+감성 혼합)

[소제목 1]
(150~200자 본문)

[소제목 2]
(150~200자 본문)

[소제목 3]
(150~200자 본문)

[소제목 4]
(150~200자 본문)

### 대문 사진 배치
- 추천 위치: (1번째? 2번째?)
- 추천 파일: (구체적 파일명)
- 이유: (왜 이 위치/사진이 효과적인지)

### 태그 (최소 10개)
#해시태그1 #해시태그2 #해시태그3 #해시태그4 #해시태그5
#해시태그6 #해시태그7 #해시태그8 #해시태그9 #해시태그10

===========================================================

중요: 
- 모든 제안은 위의 미디어 타임라인에 있는 실제 파일을 기반으로 해야 합니다
- 추상적인 표현 대신 구체적인 파일명, 시간, 대사를 사용하세요
- 각 제안마다 "왜"를 설명해주세요
- 실행 가능하고 현실적인 제안만 포함하세요
"""

        try:
            print(f"    → 시스템 명령어 길이: {len(system_instruction)} 자")
            print(f"    → 사용자 프롬프트 길이: {len(user_prompt)} 자")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.temperature,
                    max_output_tokens=8192
                )
            )
            
            print(f"    → API 응답 길이: {len(response.text)} 자")
            
            # 응답이 완전한지 확인
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                finish_reason = response.candidates[0].finish_reason
                print(f"    → 완료 상태: {finish_reason}")
                
                if finish_reason == "MAX_TOKENS":
                    print(f"    [⚠️ 경고] 응답이 최대 길이에서 잘렸습니다!")
                    print(f"    → config.json의 temperature를 낮추거나 filelist.md의 파일 수를 줄려보세요")
            
            if len(response.text) < 500:
                print(f"    [경고] 응답이 너무 짧습니다 ({len(response.text)} 자)")
                print(f"    → 네트워크 문제 또는 API 한도 초과 가능성")
            
            return response.text
            
        except Exception as e:
            print(f"\n[API 오류] 상세 정보:")
            print(f"  → 오류 타입: {type(e).__name__}")
            print(f"  → 오류 메시지: {str(e)}")
            print(f"  → 모델: {self.model_name}")
            print(f"\n[해결 방법]")
            print(f"  1. https://ai.google.com/rate-limit 에서 사용량 확인")
            print(f"  2. API 한도 초과 시 내일 자정까지 대기")
            print(f"  3. 모델을 gemini-1.5-flash로 변경 시도")
            return None

    # ── Filelist 요약 생성 ──────────────────────
    def summarize_filelist(self) -> str:
        """filelist.md를 간단한 요약으로 변환"""
        
        if not os.path.exists(self.filelist_path):
            return ""
        
        with open(self.filelist_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 통계 추출
        lines = content.split("\n")
        
        video_count = content.count("🎬 영상")
        image_count = content.count("📸 사진")
        total_files = video_count + image_count
        
        # 영상 길이 합계
        total_duration_seconds = 0
        for line in lines:
            if "분" in line and "초" in line:
                try:
                    # "5분 30초" 형식 파싱
                    parts = line.split("|")
                    if len(parts) > 3:
                        duration_str = parts[3].strip()
                        if "분" in duration_str:
                            mins = int(duration_str.split("분")[0])
                            secs = int(duration_str.split("분")[1].split("초")[0].strip()) if "초" in duration_str else 0
                            total_duration_seconds += mins * 60 + secs
                except:
                    pass
        
        total_minutes = total_duration_seconds // 60
        remaining_seconds = total_duration_seconds % 60
        
        # 주요 장소 추출 (파일명에서)
        locations = []
        for line in lines:
            if "|" in line and "파일명" not in line:
                parts = line.split("|")
                if len(parts) > 2:
                    filename = parts[2].strip().strip("`")
                    # 파일명에서 장소 추출 (첫 번째 부분)
                    if filename and not filename.startswith("---"):
                        place = filename.split("_")[0]
                        if place and place not in locations and place != "순번":
                            locations.append(place)
        
        locations = locations[:3]  # 상위 3개만
        
        # 요약 생성
        summary = f"""## 📋 미디어 요약

**촬영 통계:**
- 총 파일: {total_files}개 (영상 {video_count}개, 사진 {image_count}개)
- 총 영상 길이: {total_minutes}분 {remaining_seconds}초
- 주요 장소: {', '.join(locations) if locations else '없음'}

*상세 파일 목록은 로컬 filelist.md 참고*
"""
        
        return summary

    # ── 결과 저장 ────────────────────────────────
    def save_output(self, content: str, iteration: int) -> str:
        """AI 결과를 저장"""
        output_path = self.get_output_path()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 요약된 filelist 생성
        filelist_summary = self.summarize_filelist()
        
        header = f"""# 🎬 AI 콘텐츠 초안 — 회차 {iteration}

> 생성 일시: {timestamp}  
> 모델: {self.model_name}  
> 여행: {self.folder_name}

---

{filelist_summary}

---

## 🎯 AI 생성 결과

"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + content)
        print(f"\n[4/4] 결과 저장 완료: {os.path.basename(output_path)}")
        return output_path

    # ── Knowledge.md 자동 업데이트 (AI 협업) ────
    def update_knowledge_with_ai(self, iteration: int, ai_response: str) -> bool:
        """AI와 협업하여 knowledge.md 업데이트"""
        print(f"\n[5/4] Knowledge.md 업데이트 중...")
        
        prompt = f"""
다음은 {iteration}회차 {self.folder_name} 여행의 AI 생성 콘텐츠입니다:

{ai_response}

위 결과에서 얻을 수 있는 통찰력, 패턴, 베스트 프랙티스를 정리하여 
다음과 같은 형식으로 knowledge.md 업데이트 내용을 생성해주세요:

### {self.folder_name} ({iteration}회차)

**유튜브 시나리오:**
- (발견사항 1)
- (발견사항 2)

**블로그 전략:**
- (발견사항)

**특수 노하우:**
- (발견사항)

짧고 명확하게 작성해주세요. (최대 10줄)
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1024
                )
            )
            
            new_content = response.text
            
            with open(self.knowledge_path, "a", encoding="utf-8") as f:
                f.write(f"\n{new_content}\n")
            
            print(f"    → knowledge.md 업데이트 완료")
            return True
        except Exception as e:
            print(f"    [경고] knowledge.md 업데이트 실패: {str(e)}")
            print(f"    → 계속 진행합니다...")
            return True

    # ── instructions.md 정리 (피드백 로테이션) ──
    def rotate_feedback_in_instructions(self, had_feedback: bool) -> bool:
        """Current feedback를 Previous로 로테이션"""
        
        if not had_feedback:
            print(f"\n[6/4] Current feedback이 비어있습니다. 정리 스킵.")
            return True
        
        print(f"\n[6/4] instructions.md 정리 중...")
        print(f"    → 파일 경로: {self.instructions_path}")
        
        if not os.path.exists(self.instructions_path):
            print(f"    [오류] instructions.md가 없습니다!")
            return False
        
        try:
            # 파일 읽기
            with open(self.instructions_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            print(f"    → 파일 크기: {len(content)} 자")
            
            # 1. Current feedback 내용 추출
            current_start = content.find("## Current feedback and request")
            current_end = content.find("## Previous - 1 feedback and request")
            
            print(f"    → Current 위치: {current_start} ~ {current_end}")
            
            if current_start == -1 or current_end == -1:
                print(f"    [오류] 형식이 맞지 않습니다!")
                print(f"    → '## Current feedback and request' 찾음: {current_start != -1}")
                print(f"    → '## Previous - 1 feedback' 찾음: {current_end != -1}")
                return False
            
            current_content = content[current_start + len("## Current feedback and request"):current_end].strip()
            print(f"    → Current 내용 길이: {len(current_content)} 자")
            
            # 2. Previous - 1 content 추출
            prev1_start = content.find("## Previous - 1 feedback and request")
            prev1_end = content.find("## Previous - 2 feedback and request")
            
            if prev1_start == -1:
                prev1_content = ""
            else:
                if prev1_end == -1:
                    prev1_content = content[prev1_start + len("## Previous - 1 feedback and request"):].strip()
                else:
                    prev1_content = content[prev1_start + len("## Previous - 1 feedback and request"):prev1_end].strip()
            
            print(f"    → Previous 1 내용 길이: {len(prev1_content)} 자")
            
            # 3. Previous - 2 content 추출
            prev2_start = content.find("## Previous - 2 feedback and request")
            prev2_end = content.find("## Previous - 3 feedback and request")
            
            if prev2_start == -1:
                prev2_content = ""
            else:
                if prev2_end == -1:
                    prev2_content = content[prev2_start + len("## Previous - 2 feedback and request"):].strip()
                else:
                    prev2_content = content[prev2_start + len("## Previous - 2 feedback and request"):prev2_end].strip()
            
            print(f"    → Previous 2 내용 길이: {len(prev2_content)} 자")
            
            # 4. 새로운 content 구성
            new_content = f"""## Current feedback and request
(이번 작업에 한정) 새로운 요청을 여기에 입력하세요.

## Previous - 1 feedback and request
{current_content}

## Previous - 2 feedback and request
{prev1_content}

## Previous - 3 feedback and request
{prev2_content}
"""
            
            # 5. 파일 저장
            with open(self.instructions_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            print(f"    ✅ 로테이션 완료:")
            print(f"      • Current → Previous 1로 이동 ({len(current_content)} 자)")
            print(f"      • Previous 1 → Previous 2로 이동 ({len(prev1_content)} 자)")
            print(f"      • Previous 2 → Previous 3로 이동 ({len(prev2_content)} 자)")
            
            return True
            
        except Exception as e:
            print(f"    [오류] 로테이션 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    # ── Git Push ─────────────────────────────────
    def push_to_git(self, output_path: str, had_feedback: bool) -> bool:
        """Knowledge.md와 instructions.md를 git에 push"""
        print(f"\n[Git] 최종 업로드 중...")
        
        # Push 전에 pull 실행 (remote 변경사항 가져오기)
        print(f"    → Git pull (최신 커밋 가져오기)...")
        result = subprocess.run(
            ["git", "-C", self.git_work_dir, "pull"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8"
        )
        if result.returncode != 0:
            print(f"[Git Pull 실패] {result.stderr}")
            return False
        print(f"    → Pull 완료")
        
        files_to_push = [os.path.basename(output_path)]
        
        # 결과 파일을 git_workspace로 복사
        dest_file = os.path.join(self.git_work_dir, os.path.basename(output_path))
        shutil.copy2(output_path, dest_file)
        print(f"    → 파일 복사: {os.path.basename(output_path)}")
        
        # instructions.md 복사 (feedback이 있었을 때만)
        if had_feedback:
            git_inst_path = os.path.join(self.git_work_dir, "instructions.md")
            shutil.copy2(self.instructions_path, git_inst_path)
            files_to_push.append("instructions.md")
            print(f"    → 파일 복사: instructions.md")
        
        # knowledge.md 복사
        files_to_push.append("knowledge.md")
        print(f"    → 파일 포함: knowledge.md")
        
        # main.py 포함 여부 질문
        while True:
            include_main = input(f"\n    main.py도 함께 push하시겠습니까? (y/n): ").strip().lower()
            if include_main in ['y', 'n']:
                break
        
        if include_main == 'y':
            if os.path.exists("main.py"):
                dest_main = os.path.join(self.git_work_dir, "main.py")
                shutil.copy2("main.py", dest_main)
                files_to_push.append("main.py")
                print(f"    → 파일 추가: main.py")
        
        # Git add
        for file in files_to_push:
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "add", file],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode != 0:
                print(f"[Git Add 실패] {result.stderr}")
                return False
        
        # Git commit
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"[{self.folder_name}] {timestamp} - {', '.join(files_to_push)}"
        result = subprocess.run(
            ["git", "-C", self.git_work_dir, "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8"
        )
        if result.returncode != 0 and "nothing to commit" not in result.stdout.lower():
            print(f"[Git Commit 실패] {result.stderr}")
            return False
        
        print(f"    → Commit: {commit_msg}")
        
        # Git push
        result = subprocess.run(
            ["git", "-C", self.git_work_dir, "push"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8"
        )
        if result.returncode != 0:
            print(f"[Git Push 실패] {result.stderr}")
            return False
        
        print(f"    → Push 완료 ✅")
        return True

    # ── .gitignore 설정 ────────────────────────────
    def _setup_gitignore(self):
        gitignore_path = os.path.join(self.git_work_dir, ".gitignore")
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "config.json" not in content:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\nconfig.json\nprojects/\n")
        else:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("""# 민감한 설정 파일
config.json
projects/
.env
.env.local

# IDE & 시스템
.vscode/
.idea/
__pycache__/
*.pyc
.DS_Store
Thumbs.db

# 로컬 작업
git_workspace/
""")

    # ── Knowledge.md 초기화 ────────────────────────
    def _init_knowledge(self):
        if os.path.exists(self.knowledge_path):
            return
        
        with open(self.knowledge_path, "w", encoding="utf-8") as f:
            f.write("""# 📚 YouTube Blog Scene Creator - Knowledge Base

> 이 파일은 모든 여행을 통해 축적된 제작 방법론을 기록합니다.
> 사용자는 직접 수정하지 않으며, AI와 협업으로 자동 업데이트됩니다.

---

## 축적된 인사이트

(여행별 발견사항이 자동으로 누적됩니다)

마지막 업데이트: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
""")

    # ── 전체 파이프라인 ──────────────────────────
    def run(self):
        print("=" * 70)
        print("  🏔️  YouTube Blog Scene Creator v4.1 (최종)")
        print("  instructions.md (App 전체) | 자동 Knowledge 업데이트")
        print("=" * 70)

        # 1. Git 동기화
        if not self.init_git_repo():
            return
        
        # 2. 프로젝트 디렉토리 초기화
        if not self.init_project_dir():
            return
        
        # 3. 미디어 스캔
        if not self.generate_filelist():
            return
        
        # 4. Instructions 동기화
        print(f"\n[2/4] instructions.md 동기화 중...")
        if not self.pull_instructions_from_git():
            return
        
        # 5. 회차 확인
        iteration = self.get_iteration_count()
        print(f"    → 현재 {iteration}회차 실행")
        
        # 6. Current feedback 추출
        current_feedback = self.extract_current_feedback()
        had_feedback = bool(current_feedback)
        
        if had_feedback:
            print(f"    → Current feedback 감지됨 (길이: {len(current_feedback)} 자)")
        else:
            print(f"    → Current feedback이 비어있습니다.")
        
        # 7. AI 호출
        ai_response = self.call_gemini(iteration, current_feedback)
        if not ai_response:
            return
        
        # 8. 결과 저장
        output_path = self.save_output(ai_response, iteration)
        self.log_iteration(iteration, output_path)
        
        # 9. Knowledge.md 업데이트
        self.update_knowledge_with_ai(iteration, ai_response)
        
        # 10. instructions.md 정리 (feedback이 있었을 때만)
        self.rotate_feedback_in_instructions(had_feedback)
        
        # 11. Git Push
        if not self.push_to_git(output_path, had_feedback):
            print("\n" + "=" * 70)
            print(f"  ❌ Git 업로드 실패!")
            print("=" * 70)
            sys.exit(1)
        
        print("\n" + "=" * 70)
        print(f"  ✅ {iteration}회차 완료!")
        print(f"  📁 프로젝트: {self.project_dir}")
        print(f"  📄 결과: {os.path.basename(output_path)}")
        print(f"  📚 Knowledge: 자동 업데이트됨")
        if had_feedback:
            print(f"  🔄 피드백: 로테이션 완료 (Current → Previous)")
        print(f"  🚀 다음 단계: instructions.md 수정 (로컬/Git) → main.py 실행")
        print("=" * 70)


# ─────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    cfg = load_config("config.json")
    target_dir = input_target_dir()
    orchestrator = TravelContentOrchestrator(cfg, target_dir)
    orchestrator.run()
