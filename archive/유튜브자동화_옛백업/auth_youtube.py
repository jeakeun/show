"""유튜브 업로드 권한 최초 인증 (브라우저가 열리면 채널 계정으로 로그인)."""
from src.uploader import get_credentials

print("브라우저가 열립니다. 유튜브 채널 계정으로 로그인하고 '허용'을 눌러주세요...")
creds = get_credentials()
print("인증 성공! 토큰이 secrets/token.json 에 저장되었습니다.")
print("이제 매일 자동 업로드가 가능합니다.")
