import os
import sys
import json
import datetime
import subprocess
import shutil
import cv2
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
#  메인 오케스트레이터
# ─────────────────────────────────────────────
class TravelContentOrchestrator:
    def __init__(self, cfg: dict, target_dir: str):
        self.cfg = cfg
        self.target_dir      = target_dir
        self.output_dir      = cfg.get("output_dir", ".")
        self.model_name      = cfg.get("gemini_model", "gemini-2.5-flash")
        self.temperature     = cfg.get("temperature", 0.3)
        
        # Git 설정
        self.git_repo_url    = cfg.get("git_repo_url")
        self.git_pat         = cfg.get("git_pat")
        self.git_work_dir    = cfg.get("git_work_dir", "./git_workspace")

        # 하위 폴더명 추출 (파일 생성에 사용)
        self.folder_name = os.path.basename(self.target_dir.rstrip(os.sep))

        # 파일 경로 정의
        self.filelist_path      = os.path.join(self.output_dir, "filelist.md")
        self.instruction_path   = os.path.join(self.output_dir, "project_instructions.md")
        self.iteration_log_path = os.path.join(self.output_dir, "iteration_log.md")

        self.client = genai.Client(api_key=cfg["gemini_api_key"])

    # ── 출력 파일명 생성 ────────────────────────
    def get_output_path(self) -> str:
        """형식: {폴더명}____YYYYMMDD-HHMMSS.md"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{self.folder_name}____{timestamp}.md"
        return os.path.join(self.output_dir, filename)
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
        """파일명의 확장자를 제거하고 언더스코어 기준 3번째 이후를 설명으로 사용.
        형식이 맞지 않으면 파일명 자체를 반환."""
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

        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.filelist_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"    → {len(media_files)}개 파일 스캔 완료. '{self.filelist_path}' 저장됨.")
        return True

    # ── project_instructions.md 초기 템플릿 생성 ─
    def ensure_instruction_file(self):
        if os.path.exists(self.instruction_path):
            return  # 이미 있으면 건드리지 않음

        template = """# 🗒️ 프로젝트 누적 지침

## 여행 기본 정보
- 여행지: 태백산 (강원도 태백시)
- 날짜: 2026년 6월 12일
- 코스: 절골 → 천제단(정상) → 용연동굴
- 동행: (예: 2인, 가족, 혼자 등 입력)
- 날씨: (예: 맑음, 기온 18도)

## 유튜브 채널 정보
- 채널 이름: (채널명 입력)
- 채널 성격: (예: 등산/여행 브이로그, 30~50대 타깃)
- 영상 스타일: (예: 감성 편집, 예능형, 정보 위주)
- 목표 영상 길이: (예: 15~20분)

## 블로그 정보
- 플랫폼: 네이버 블로그
- 주요 타깃 키워드: (예: 태백산 등산, 태백산 코스, 태백산 절골)
- 원하는 글 분위기: (예: 친근하고 유머러스, 정보 중심)

## 피드백 / 이전 회차 수정 사항
- (AI 결과를 보고 마음에 안 드는 부분을 여기에 자유롭게 적어주세요)
- 예) "유튜브 훅이 너무 평범함, 더 자극적으로"
- 예) "블로그 분량 2배로 늘려줘"
- 예) "3봉 구간 영상을 하이라이트로 더 강조해줘"
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
        # "## 회차 N" 패턴 개수로 카운트
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

        system_instruction = f"""
너는 전문 여행/등산 유튜버이자 네이버 상위 노출 최적화 블로거야.
사실에 기반하되 예능적 재미가 가득한 콘텐츠 초안을 작성해야 해.
이번은 {iteration}회차 작업이야. 이전 피드백이 있다면 반드시 반영해.

[프로젝트 누적 지침]
{instruction_content}

[분석할 미디어 타임라인]
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

    # ── Git에 결과 파일 Push ──────────────────────
    def push_to_git(self, output_path: str) -> bool:
        """결과 파일을 Git 저장소에 commit & push합니다."""
        print(f"\n[5/4] Git에 결과 업로드 중...")
        
        try:
            # git_work_dir이 없으면 repo clone
            if not os.path.exists(self.git_work_dir):
                print(f"    → Git 저장소 복제 중: {self.git_repo_url}")
                # PAT를 URL에 포함하여 인증
                auth_url = self.git_repo_url.replace(
                    "https://", 
                    f"https://{self.git_pat}@"
                )
                result = subprocess.run(
                    ["git", "clone", auth_url, self.git_work_dir],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    print(f"[Git Clone 실패] {result.stderr}")
                    return False
                print(f"    → 저장소 복제 완료")
                
                # .gitignore 생성 (config.json, *.env 등 제외)
                self._setup_gitignore()
            else:
                # 기존 repo pull
                print(f"    → Git 저장소 업데이트 중")
                result = subprocess.run(
                    ["git", "-C", self.git_work_dir, "pull"],
                    capture_output=True,
                    text=True,
                    timeout=30
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
                # main.py를 git_work_dir로 복사
                main_py_path = "main.py"
                if os.path.exists(main_py_path):
                    dest_main = os.path.join(self.git_work_dir, "main.py")
                    shutil.copy2(main_py_path, dest_main)
                    files_to_push.append("main.py")
                    print(f"    → main.py 추가됨")
                else:
                    print(f"    [경고] main.py를 찾을 수 없습니다.")

            # Git add (명시적으로 지정된 파일만)
            for file in files_to_push:
                result = subprocess.run(
                    ["git", "-C", self.git_work_dir, "add", file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    print(f"[Git Add 실패] {result.stderr}")
                    return False

            # config.json이 실수로 git에 추가되었는지 확인 후 제거
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if "config.json" in result.stdout:
                print(f"    [⚠️ 경고] config.json이 git에 추가되려고 합니다. 제외 중...")
                subprocess.run(
                    ["git", "-C", self.git_work_dir, "reset", "config.json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            # Git commit
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            files_desc = "main.py + 결과" if include_main == 'y' else "결과"
            commit_msg = f"[콘텐츠 초안] {self.folder_name} - {timestamp} ({files_desc})"
            result = subprocess.run(
                ["git", "-C", self.git_work_dir, "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                # commit할 변경사항이 없을 수 있음
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
                timeout=30
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
        
        # 이미 .gitignore가 있으면 config.json이 있는지 확인
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "config.json" not in content:
                # 기존 내용에 추가
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n# 민감한 설정 파일\nconfig.json\n.env\n.env.local\n")
        else:
            # 새로 생성
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("""# 민감한 설정 파일 (API 키, PAT 등)
config.json
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
        
        print(f"    → .gitignore 설정 완료 (config.json 제외)")

    # ── 전체 파이프라인 ──────────────────────────
    def run(self):
        print("=" * 55)
        print("  🏔️  여행 콘텐츠 오케스트레이터 시작")
        print("=" * 55)

        # 1. 미디어 스캔
        if not self.generate_filelist():
            return

        # 2. 지침 파일 보장
        print("\n[2/4] 프로젝트 지침 파일 확인 중...")
        self.ensure_instruction_file()

        # 3. 반복 회차 확인
        iteration = self.get_iteration_count()
        print(f"    → 현재 {iteration}회차 실행")

        # 4. AI 호출
        ai_response = self.call_gemini(iteration)
        if not ai_response:
            return

        # 5. 저장
        print(f"\n[4/4] 결과 저장 중...")
        output_path = self.save_output(ai_response, iteration)
        self.log_iteration(iteration, output_path)

        # 6. Git Push
        if not self.push_to_git(output_path):
            print("\n" + "=" * 55)
            print(f"  ❌ Git 업로드 실패!")
            print("=" * 55)
            sys.exit(1)

        print("\n" + "=" * 55)
        print(f"  ✅ {iteration}회차 완료!")
        print(f"  📄 결과 파일: {output_path}")
        print(f"  🔁 수정 후 재실행: project_instructions.md 피드백 추가 → 재실행")
        print("=" * 55)


# ─────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    cfg = load_config("config.json")
    target_dir = input_target_dir()
    orchestrator = TravelContentOrchestrator(cfg, target_dir)
    orchestrator.run()
