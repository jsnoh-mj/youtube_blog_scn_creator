import os
import sys
import cv2
import subprocess
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class TravelContentOrchestrator:
    def __init__(self, target_dir):
        self.target_dir = target_dir
        # 사진 디렉토리명 마지막 부분으로 결과 폴더 생성
        dir_name = os.path.basename(target_dir)
        self.output_dir = os.path.join(target_dir, dir_name)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.filelist_path = os.path.join(self.output_dir, "filelist.md")
        self.instruction_path = "project_instructions.md"
        self.yt_draft_path = os.path.join(self.output_dir, "youtube_scenario_draft.md")
        self.blog_draft_path = os.path.join(self.output_dir, "blogpost_scenario_draft.md")
        self.ai_raw_output_path = os.path.join(self.output_dir, "ai_raw_output.md")
        
        # Google AI Studio 무료 API 키 로드 (환경변수만 사용)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[Error] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
            print("[Info] PowerShell에서 다음을 실행해주세요:")
            print("       $env:GEMINI_API_KEY = 'your-api-key-here'")
            sys.exit(1)
        self.client = genai.Client(api_key=api_key)
        # 무료 한도가 높고 빠른 2.5-flash를 기본 엔진으로 설정
        self.model_name = "gemini-2.5-flash" 

    def get_video_duration(self, file_path):
        try:
            video = cv2.VideoCapture(file_path)
            duration = video.get(cv2.CAP_PROP_FRAME_COUNT) / video.get(cv2.CAP_PROP_FPS)
            video.release()
            return f"{round(duration, 1)}초"
        except:
            return "-"

    def generate_filelist(self):
        print(f"[*] '{self.target_dir}' 미디어 스캔 및 정렬 중...")
        if not os.path.exists(self.target_dir):
            print(f"[Error] 경로가 없습니다: {self.target_dir}")
            return False
            
        files = [f for f in os.listdir(self.target_dir) if os.path.isfile(os.path.join(self.target_dir, f))]
        files.sort()
        
        md = "# 📄 여행 미디어 마스터 타임라인 리스트\n\n"
        md += "| 순번 | 파일명 | 파일 유형 | 재생 시간 | 유저 설명 |\n"
        md += "| :---: | :--- | :---: | :---: | :--- |\n"
        
        for idx, filename in enumerate(files, 1):
            if filename.startswith('.'): continue
            full_path = os.path.join(self.target_dir, filename)
            ext = os.path.splitext(filename)[1].lower()
            f_type = "영상 (Video)" if ext in ['.mp4', '.mov', '.avi'] else "사진 (Image)"
            duration = self.get_video_duration(full_path) if f_type == "영상 (Video)" else "-"
            parts = filename.split('_')
            description = parts[2] if len(parts) > 2 else "설명 없음"
            
            md += f"| {idx} | `{filename}` | {f_type} | {duration} | {description} |\n"
            
        with open(self.filelist_path, "w", encoding="utf-8") as f:
            f.write(md)
        return True

    def call_gemini_brain(self, prompt_type, user_feedback=""):
        """[핵심 알고리즘] 마스터 프롬프트와 지침서를 결합하여 Gemini API 호출"""
        print(f"[*] Gemini AI 브레인 가동 중... ({prompt_type})")
        
        # 1. 기존 타임라인과 지침서 내용 읽기
        with open(self.filelist_path, "r", encoding="utf-8") as f:
            filelist_content = f.read()
        
        instruction_content = ""
        if os.path.exists(self.instruction_path):
            with open(self.instruction_path, "r", encoding="utf-8") as f:
                instruction_content = f.read()

        # 2. 상용 크리에이터 노하우 패키징 마스터 프롬프트 조립
        master_system_instruction = f"""
        너는 전문 여행/등산 유튜버이자 네이버 최적화 블로거야. 사실에 기반하되 예능적 재미가 가득한 초안을 짜야 해.
        
        [현재 프로젝트 누적 지침 정보]
        {instruction_content}
        
        [분석할 미디어 타임라인]
        {filelist_content}
        """
        
        if prompt_type == "generate_drafts":
            user_prompt = "위 타임라인과 지침을 완벽히 분석해서 상용 노하우가 담긴 youtube_scenario_draft.md 와 blogpost_scenario_draft.md 초안 내용을 생성해줘. 유튜브 시나리오는 3초 훅과 시청각 분리 레이아웃을 지키고, 리터칭한 느낌의 대문 사진(흰 공백 레이아웃 포함) 배치를 구체적으로 제안해줘. 블로그는 상위 노출 로직을 적용해줘. 두 파일의 구분을 확실히 해줘."
        elif prompt_type == "feedback_loop":
            user_prompt = f"사용자가 다음과 같은 피드백을 줬어: '{user_feedback}'. 이 내용을 분석해서 1) 'project_instructions.md'에 영구 지침으로 누적 업데이트하고, 2) 그에 맞춰 시나리오 초안들을 리비전해줘."

        # 3. Gemini API 실시간 무료 요청
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=master_system_instruction,
                    temperature=0.3
                )
            )
            return response.text
        except Exception as e:
            print(f"[API Error] Gemini 호출 실패: {e}")
            return None

    def save_and_git_sync(self, commit_message):
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print(f"[Success] Git 동기화 완료: {commit_message}")
        except Exception as e:
            print(f"[Git Error] Push 실패: {e}")

    def execute_pipeline(self):
        # 1단계: 파일 리스트 정리
        if not self.generate_filelist(): return
        
        # 2단계: Gemini를 통해 초안 생성 알고리즘 작동
        ai_response = self.call_gemini_brain("generate_drafts")
        if not ai_response: return
        
        # 파싱 로직 (간단히 파일 분할 저장 예시 - 실제 환경에선 마크다운 태그 기준으로 분할)
        print("[*] AI가 생성한 초안 내용을 파일로 이관 및 저장 중...")
        # (AI 응답을 나누어 youtube_scenario_draft.md, blogpost_scenario_draft.md에 저장하는 코드 블록)
        with open(self.ai_raw_output_path, "w", encoding="utf-8") as f:
            f.write(ai_response)
            
        # 3단계: 무인 Git 백업
        self.save_and_git_sync("AI Auto-Pipeline: 태백산 프로젝트 초안 빌드 완료")

if __name__ == "__main__":
    target = r"D:\00_나의사진들\2026_06_12_태백산_3봉정복_절골힐링_용연동굴"
    orchestrator = TravelContentOrchestrator(target)
    orchestrator.execute_pipeline()