import os
import sys
import json
import datetime
import subprocess
import shutil
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
        # 템플릿 자동 생성
        template = {
            "gemini_api_key": "여기에_실제_AIzaSy_API_키를_입력하세요",
            "gemini_model": "gemini-2.5-flash",
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
        print(f"    → gemini_api_key, git_repo_url, git_pat 를 직접 수정한 뒤 다시 실행하세요.")
        sys.exit(0)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 필수 항목 검증
    required_keys = ["gemini_api_key", "git_repo_url", "git_pat", "git_work_dir"]
    for key in required_keys:
        if key not in cfg or not cfg[key]:
            print(f"[오류] config.json에 '{key}' 값이 없습니다.")
            sys.exit(1)

    # Gemini API 키 검증
    if "AIzaSy" not in cfg["gemini_api_key"] and cfg["gemini_api_key"].startswith("여기에"):
        print("[오류] config.json의 gemini_api_key를 실제 키로 교체해 주세요.")
        sys.exit(1)

    # Git PAT 검증
    if cfg["git_pat"].startswith("ghp_여기에") or cfg["git_pat"].startswith("여기에"):
        print("[오류] config.json의 git_pat를 실제 GitHub PAT로 교체해 주세요.")
        sys.exit(1)

    # Git 저장소 URL 검증
    if "github.com" not in cfg["git_repo_url"]:
        print("[오류] config.json의 git_repo_url이 유효하지 않습니다. (GitHub URL 필요)")
        sys.exit(1)

    return cfg


def input_target_dir() -> str:
    """사용자로부터 타겟 폴더 경로를 입력받습니다."""
    while True:
        target = input("\n📁 여행 미디어 폴더의 전체 경로를 입력하세요\n   (예: D:\\여행사진\\태백산 또는 /Users/name/Documents/travel): ").strip()
        
        if not target:
            print("   [경고] 경로를 입력해 주세요.")
            continue
        
        # 윈도우 경로의 따옴표 제거
        target = target.strip('"').strip("'")
        
        if not os.path.exists(target):
            print(f"   [경고] 해당 경로가 없습니다: {target}")
            continue
        
        if not os.path.isdir(target):
            print(f"   [경고] 파일이 아닌 폴더 경로를 입력해 주세요.")
            continue
        
        return target


# ─────────────────────────────────────────────
#  여행 콘텐츠 오케스트레이터 v2.0
# ─────────────────────────────────────────────
class TravelContentOrchestrator:
    def __init__(self, cfg: dict, target_dir: str):
        self.cfg = cfg
        self.target_dir      = target_dir
        self.projects_dir    = cfg.get("projects_dir", "./projects")
        self.model_name      = cfg.get("gemini_model", "gemini-2.5-flash")
        self.temperature     = cfg.get("temperature", 0.3)
        
        # Git 설정
        self.git_repo_url    = cfg.get("git_repo_url")
        self.git_pat         = cfg.get("git_pat")
        self.git_work_dir    = cfg.get("git_work_dir", "./git_workspace")

        # 하위 폴더명 추출 (여행명)
        self.folder_name = os.path.basename(self.target_dir.rstrip(os.sep))
        
        # 여행 프로젝트 디렉토리 (여행별 독립)
        self.project_dir = os.path.join(self.projects_dir, self.folder_name)
        
        # 여행별 파일 경로 정의
        self.filelist_path      = os.path.join(self.project_dir, "filelist.md")
        self.instruction_path   = os.path.join(self.project_dir, "project_instructions.md")
        self.iteration_log_path = os.path.join(self.project_dir, "iteration_log.md")
        
        # 글로벌 Knowledge 파일 (git_workspace에서 관리)
        self.knowledge_path     = os.path.join(self.git_work_dir, "knowledge.md")

        self.client = genai.Client(api_key=cfg["gemini_api_key"])

    # ── 프로젝트 디렉토리 초기화 ────────────────
    def init_project_dir(self) -> bool:
        """여행 프로젝트 디렉토리를 초기화합니다 (첫 시도만)."""
        if os.path.exists(self.project_dir):
            print(f"    → 기존 프로젝트 폴더 사용: {self.project_dir}")
            return True
        
        print(f"    → 새 프로젝트 폴더 생성: {self.project_dir}")
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
            fps   = video.get(cv2.CAP_PROP_FPS)
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
        """파일명의 확장자를 제거하고 언더스코어 기준 3번째 이후를 설명으로 사용."""
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
            if os.path.isfile(os.path.join(self.target_dir, f))
            and not f.startswith(".")
        )

        media_files = [
            f for f in all_files
            if os.path.splitext(f)[1].lower() in video_exts | image_exts
        ]

        if not media_files:
            print("[경고] 인식 가능한 미디어 파일이 없습니다.")
            return False

        md  = "# 📷 여행 미디어 마스터 타임라인\n\n"
        md += f"> 스캔 경로: `{self.target_dir}`  \n"
        md += f"> 스캔 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        md += "| 순번 | 파일명 | 유형 | 재생시간 | 자동 추출 설명 |\n"
        md += "| :---: | :--- | :---: | :---: | :--- |\n"

        for idx, filename in enumerate(media_files, 1):
            full_path = os.path.join(self.target_dir, filename)
            ext       = os.path.splitext(filename)[1].lower()
            f_type    = "🎬 영상" if ext in video_exts else "📸 사진"
            duration  = self.get_video_duration(full_path) if ext in video_exts else "-"
            desc      = self.extract_description(filename)
            md += f"| {idx} | `{filename}` | {f_type} | {duration} | {desc} |\n"

        os.makedirs(self.project_dir, exist_ok=True)
        with open(self.filelist_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"    → {len(media_files)}개 파일 스캔 완료. '{self.filelist_path}' 저장됨.")
        return True

    # ── project_instructions.md 초기 템플릿 생성 ─
    def ensure_instruction_file(self):
        if os.path.exists(self.instruction_path):
            return  # 이미 있으면 건드리지 않음

        template = f"""# 🗒️ 프로젝트 누적 지침 - {self.folder_name}

## 여행 기본 정보
- 여행지: {self.folder_name}
- 날짜: (입력해주세요)
- 코스: (입력해주세요)
- 동행: (입력해주세요)
- 날씨: (입력해주세요)

## 유튜브 채널 정보
- 채널 이름: (입력해주세요)
- 채널 성격: (입력해주세요)
- 영상 스타일: (입력해주세요)
- 목표 영상 길이: (입력해주세요)

## 블로그 정보
- 플랫폼: 네이버 블로그
- 주요 타깃 키워드: (입력해주세요)
- 원하는 글 분위기: (입력해주세요)

## 피드백 / 이전 회차 수정 사항
- (AI 결과를 보고 마음에 안 드는 부분을 여기에 자유롭게 적어주세요)
"""
        with open(self.instruction_path, "w", encoding="utf-8") as f:
            f.write(template)
        print(f"    → '{self.instruction_path}' 초기 템플릿 생성됨. 내용을 채운 뒤 재실행하세요.")

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
    def call_gemini(self, iteration: int) -> str | None:
        print(f"\n[3/4] Gemini AI 호출 중... (회차: {iteration}, 약 1~2분 소요)")

        with open(self.filelist_path, "r", encoding="utf-8") as f:
            filelist_content = f.read()

        instruction_content = ""
        if os.path.exists(self.instruction_path):
            with open(self.instruction_path, "r", encoding="utf-8") as f:
                instruction_content = f.read()

        # Knowledge.md에서 누적된 방법론 읽기
        knowledge_content = ""
        if os.path.exists(self.knowledge_path):
            with open(self.knowledge_path, "r", encoding="utf-8") as f:
                knowledge_content = f.read()

        system_instruction = f"""
너는 전문 여행/등산 유튜버이자 네이버 상위 노출 최적화 블로거야.
사실에 기반하되 예능적 재미가 가득한 콘텐츠 초안을 작성해야 해.
이번은 {iteration}회차 작업이야.

[누적된 시나리오 제작 방법론]
{knowledge_content if knowledge_content else "아직 누적된 방법이 없습니다. 기본 방식으로 진행해주세요."}

[프로젝트 지침]
{instruction_content}

[미디어 타임라인]
{filelist_content}
"""

        user_prompt = f"""
위 타임라인과 지침을 완벽히 분석해서 아래 두 섹션으로 나누어 초안을 작성해줘.
각 섹션은 반드시 구분선(===)과 섹션 헤더로 명확히 분리해줘.

===========================================================
## [SECTION 1] 유튜브 시나리오 초안
===========================================================

- 제목 후보 3개 (클릭률 최적화, A/B 테스트용)
- 썸네일 컨셉 (대문 사진 선정 기준 + 흰 공백 레이아웃 배치 제안)
- 3초 훅 (오프닝 대사/장면 — 시청자가 스크롤 멈추게 하는 임팩트)
- 전체 타임라인 (시각/청각 분리 레이아웃: 왼쪽=영상 설명, 오른쪽=내레이션/자막)
- 하이라이트 장면 TOP3 선정 이유
- 엔딩 CTA (구독/좋아요 멘트)

===========================================================
## [SECTION 2] 네이버 블로그 초안
===========================================================

- 제목 (상위 노출 키워드 포함, 30자 이내)
- 대표 키워드 5개 + 롱테일 키워드 5개
- 본문 (최소 1500자, 소제목 포함, 정보+감성 혼합)
- 대문 사진 배치 가이드 (몇 번째 사진 권장, 이유)
- 태그 추천 10개

이번 {iteration}회차에서 이전과 달라진 점이 있다면 [변경사항] 섹션에 명시해줘.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.temperature
                )
            )
            return response.text
        except Exception as e:
            print(f"[API 오류] Gemini 호출 실패: {e}")
            return None

    # ── 결과 저장 ────────────────────────────────
    def save_output(self, content: str, iteration: int):
        output_path = self.get_output_path()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # filelist.md 내용 읽기
        filelist_content = ""
        if os.path.exists(self.filelist_path):
            with open(self.filelist_path, "r", encoding="utf-8") as f:
                filelist_content = f.read()
        
        header = f"""# 🎬 AI 콘텐츠 초안 — 회차 {iteration}

> 생성 일시: {timestamp}  
> 모델: {self.model_name}  
> 여행: {self.folder_name}
> 반복 개선: project_instructions.md 를 수정 후 재실행하면 다음 회차가 생성됩니다.

---

## 📋 미디어 타임라인

{filelist_content}

---

## 🎯 AI 생성 결과

"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + content)
        print(f"    → '{output_path}' 저장 완료 (filelist 포함).")
        return output_path

    # ── Git에 결과 파일 & Knowledge Push ─────────
    def push_to_git(self, output_path: str) -> bool:
        """결과 파일과 knowledge.md를 Git 저장소에 commit & push합니다."""
        print(f"\n[5/4] Git에 결과 업로드 중...")
        
        try:
            # git_work_dir이 유효한 git repo인지 확인
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
            
            # git repo가 없거나 유효하지 않으면 clone
            if not is_valid_git_repo:
                # 기존 폴더가 있으면 삭제 (손상된 상태)
                if os.path.exists(self.git_work_dir):
                    print(f"    → 손상된 Git 폴더 정리 중...")
                    shutil.rmtree(self.git_work_dir)
                
                print(f"    → Git 저장소 복제 중: {self.git_repo_url}")
                auth_url = self.git_repo_url.replace(
                    "https://", 
                    f"https://{self.git_pat}@"
                )
                result = subprocess.run(
                    ["git", "clone", auth_url, self.git_work_dir],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8"
                )
                if result.returncode != 0:
                    print(f"[Git Clone 실패]")
                    print(f"  → 저장소 URL: {self.git_repo_url}")
                    print(f"  → 오류: {result.stderr}")
                    print(f"  → 확인사항:")
                    print(f"     1. GitHub PAT가 유효한가?")
                    print(f"     2. 저장소 URL이 올바른가?")
                    print(f"     3. GitHub에서 저장소가 공개되어 있는가?")
                    return False
                print(f"    → 저장소 복제 완료")
                
                # .gitignore 생성
                self._setup_gitignore()
                
                # knowledge.md 템플릿 생성
                self._init_knowledge()
            else:
                # 기존 repo pull
                print(f"    → Git 저장소 업데이트 중")
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

            # 결과 파일을 git_work_dir로 복사
            dest_file = os.path.join(self.git_work_dir, os.path.basename(output_path))
            shutil.copy2(output_path, dest_file)
            print(f"    → 파일 복사: {os.path.basename(output_path)}")

            files_to_push = [os.path.basename(output_path)]

            # 사용자에게 main.py 포함 여부 질문
            while True:
                include_main = input(f"\n    main.py도 함께 push하시겠습니까? (y/n): ").strip().lower()
                if include_main in ['y', 'n']:
                    break
                print("    [경고] y 또는 n을 입력해주세요.")

            if include_main == 'y':
                main_py_path = "main.py"
                if os.path.exists(main_py_path):
                    dest_main = os.path.join(self.git_work_dir, "main.py")
                    shutil.copy2(main_py_path, dest_main)
                    files_to_push.append("main.py")
                    print(f"    → main.py 추가됨")

            # Knowledge.md가 있으면 포함
            if os.path.exists(self.knowledge_path):
                files_to_push.append("knowledge.md")
                print(f"    → knowledge.md 포함됨")

            # Git add (명시적으로 지정된 파일만)
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

            # config.json, projects 폴더가 실수로 추가되었는지 확인 후 제거
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8"
            )
            for exclude_file in ["config.json", "projects"]:
                if exclude_file in result.stdout:
                    print(f"    [⚠️ 경고] {exclude_file}이 git에 추가되려고 합니다. 제외 중...")
                    subprocess.run(
                        ["git", "-C", self.git_work_dir, "reset", exclude_file],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        encoding="utf-8"
                    )

            # Git commit
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            files_desc = f"{self.folder_name} - {', '.join(files_to_push)}"
            commit_msg = f"[{self.folder_name}] {timestamp} - {files_desc}"
            
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8"
            )
            if result.returncode != 0:
                if "nothing to commit" not in result.stdout.lower():
                    print(f"[Git Commit 실패] {result.stderr}")
                    return False
                print(f"    → 커밋할 변경사항 없음")
            else:
                print(f"    → Commit 완료: {commit_msg}")

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
            print(f"    → Push 완료 ({', '.join(files_to_push)})")
            
            return True

        except subprocess.TimeoutExpired:
            print("[오류] Git 작업 시간 초과")
            return False
        except Exception as e:
            print(f"[Git 오류] {str(e)}")
            return False

    # ── .gitignore 설정 ────────────────────────────
    def _setup_gitignore(self):
        """git_work_dir에 .gitignore를 생성하여 민감한 파일 제외"""
        gitignore_path = os.path.join(self.git_work_dir, ".gitignore")
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "config.json" not in content:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n# 민감한 설정 파일\nconfig.json\nprojects/\n.env\n.env.local\n")
        else:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("""# 민감한 설정 파일 (API 키, PAT 등)
config.json
projects/
.env
.env.local

# IDE & 시스템 파일
.vscode/
.idea/
__pycache__/
*.pyc
.DS_Store
Thumbs.db

# 로컬 작업 폴더
git_workspace/
""")
        
        print(f"    → .gitignore 설정 완료 (config.json, projects/ 제외)")

    # ── Knowledge.md 초기화 ────────────────────────
    def _init_knowledge(self):
        """knowledge.md 템플릿 생성 (첫 clone 시 한번만)"""
        if os.path.exists(self.knowledge_path):
            return
        
        with open(self.knowledge_path, "w", encoding="utf-8") as f:
            f.write("""# 📚 누적된 콘텐츠 제작 방법론

> 여러 여행을 통해 축적된 시나리오 제작 방법과 베스트 프랙티스를 기록합니다.
> 각 회차마다 새로운 발견이나 개선사항을 이곳에 추가하세요.

---

## 🎬 유튜브 시나리오 제작 팁

### 3초 훅 작성
- (경험을 통해 추가해주세요)

### 시각/청각 분리 레이아웃
- (경험을 통해 추가해주세요)

### 썸네일 컨셉
- (경험을 통해 추가해주세요)

---

## 📝 네이버 블로그 제작 팁

### 상위 노출 키워드 선정
- (경험을 통해 추가해주세요)

### 본문 구성 방법
- (경험을 통해 추가해주세요)

### 대문 사진 선정
- (경험을 통해 추가해주세요)

---

## 🌍 여행별 특수 사항

### 산/협곡/높은 곳
- (경험을 통해 추가해주세요)

### 해변/물가
- (경험을 통해 추가해주세요)

### 도시/건축
- (경험을 통해 추가해주세요)

---

## 📊 유효하지 않은 방법 (피해야 할 것)

- (경험을 통해 추가해주세요)

---

마지막 업데이트: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
""")
        print(f"    → knowledge.md 템플릿 생성됨")

    # ── 전체 파이프라인 ──────────────────────────
    def run(self):
        print("=" * 60)
        print("  🏔️  여행 콘텐츠 AI 오케스트레이터 v2.0")
        print("  여행별 독립 관리 | 누적 방법론 | Charset 호환성")
        print("=" * 60)

        # 1. 프로젝트 디렉토리 초기화 (여행별 독립)
        print("\n[0/4] 프로젝트 디렉토리 초기화 중...")
        if not self.init_project_dir():
            return

        # 2. 미디어 스캔
        if not self.generate_filelist():
            return

        # 3. 지침 파일 보장
        print("\n[2/4] 프로젝트 지침 파일 확인 중...")
        self.ensure_instruction_file()

        # 4. 반복 회차 확인
        iteration = self.get_iteration_count()
        print(f"    → 현재 {iteration}회차 실행")

        # 5. AI 호출
        ai_response = self.call_gemini(iteration)
        if not ai_response:
            return

        # 6. 저장
        print(f"\n[4/4] 결과 저장 중...")
        output_path = self.save_output(ai_response, iteration)
        self.log_iteration(iteration, output_path)

        # 7. Git Push
        if not self.push_to_git(output_path):
            print("\n" + "=" * 60)
            print(f"  ❌ Git 업로드 실패!")
            print("=" * 60)
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"  ✅ {iteration}회차 완료!")
        print(f"  📁 프로젝트 폴더: {self.project_dir}")
        print(f"  📄 결과 파일: {output_path}")
        print(f"  📋 지침 파일: {self.instruction_path}")
        print(f"  📚 방법론: {self.knowledge_path} (Git에서 관리)")
        print(f"  🔁 개선: project_instructions.md 피드백 추가 → 재실행")
        print("=" * 60)


# ─────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    cfg = load_config("config.json")
    target_dir = input_target_dir()
    orchestrator = TravelContentOrchestrator(cfg, target_dir)
    orchestrator.run()
