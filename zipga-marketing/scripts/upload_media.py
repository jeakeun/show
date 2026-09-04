#!/usr/bin/env python3
"""영상을 오브젝트 스토리지에 올려 공개 URL을 만든다.

왜 필요한가:
  인스타그램과 스레드는 미디어 파일을 직접 업로드받지 않는다. 공개 URL을 주면
  Meta 서버가 그걸 내려받는 방식이다. 로컬 폴더의 영상을 그대로 줄 수 없으므로
  중간에 이 단계가 필요하다. (유튜브·티스토리는 필요 없다 — 직접 업로드된다.)

권장 스토리지: Cloudflare R2 (무료 10GB, S3 호환)
  다른 S3 호환 스토리지도 동일하게 동작한다 (Backblaze B2, Supabase Storage 등).

  주의: 구글 드라이브·드롭박스 공유 링크는 쓸 수 없다. 파일 자체가 아니라
  미리보기 페이지를 돌려주기 때문에 Meta가 내려받지 못한다.

준비물:
  pip install boto3

  환경변수:
    S3_ENDPOINT      예: https://<account_id>.r2.cloudflarestorage.com
    S3_BUCKET
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_PUBLIC_BASE   공개 접근 주소. 예: https://pub-xxxx.r2.dev

사용법:
  python3 upload_media.py --file 영상.mp4
  python3 upload_media.py --file 영상.mp4 --key videos/20260828.mp4
  python3 upload_media.py --file 영상.mp4 --verify     # 업로드 후 공개 접근 확인
"""

import argparse
import os
import sys
import urllib.request

REQUIRED = ["S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_PUBLIC_BASE"]

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--key", help="스토리지 안의 경로. 기본은 파일명")
    p.add_argument("--verify", action="store_true", help="업로드 후 공개 접근 확인")
    args = p.parse_args()

    if not os.path.exists(args.file):
        sys.exit(f"[!] 파일이 없습니다: {args.file}")

    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        sys.exit(f"[!] 환경변수가 비어 있습니다: {', '.join(missing)}")

    try:
        import boto3
    except ImportError:
        sys.exit("[!] boto3가 없습니다. 실행: pip install boto3")

    key = args.key or os.path.basename(args.file)
    ext = os.path.splitext(args.file)[1].lower()
    ctype = CONTENT_TYPES.get(ext, "application/octet-stream")

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    )

    size_mb = os.path.getsize(args.file) / 1024 / 1024
    print(f"[.] 업로드 중: {args.file} ({size_mb:.1f} MB) → {key}")
    try:
        s3.upload_file(
            args.file,
            os.environ["S3_BUCKET"],
            key,
            ExtraArgs={"ContentType": ctype},
        )
    except Exception as e:
        sys.exit(f"[!] 업로드 실패: {e}")

    url = os.environ["S3_PUBLIC_BASE"].rstrip("/") + "/" + key.lstrip("/")
    print(f"[+] 공개 URL: {url}")

    if args.verify:
        # Meta가 실제로 내려받을 수 있는지 미리 확인한다.
        # 여기서 실패하면 인스타·스레드 게시도 실패한다.
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"[+] 공개 접근 확인: HTTP {resp.status}, "
                      f"Content-Type: {resp.headers.get('Content-Type')}")
        except Exception as e:
            sys.exit(
                f"[!] 공개 접근 실패: {e}\n"
                "    버킷의 공개 접근 설정을 확인하세요. "
                "이 URL을 못 열면 인스타·스레드 게시도 실패합니다."
            )

    # 다음 단계에서 쓸 수 있게 URL만 마지막 줄에 출력
    print(url)


if __name__ == "__main__":
    main()
