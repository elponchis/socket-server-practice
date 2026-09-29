"""
클라이언트 Request 확인용 소켓 서버

실습 1: 클라이언트 요청 원본을 request/YYYY-MM-DD-HH-MM-SS.bin 으로 저장
실습 2: multipart/form-data 로 전송된 이미지를 별도 파일로 분리 저장

사용법:
    python socket_server.py

테스트 (다른 터미널에서):
    curl -X POST -F "title=curl 테스트" \
         -F "image=@test.jpg;type=image/jpeg" \
         http://127.0.0.1:8000/api_root/Post/
"""

import os
import re
import socket
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8000
BUFFER_SIZE = 8192

REQUEST_DIR = "request"
IMAGE_DIR = "images"

# Content-Type 과 확장자 매핑
EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


def timestamp():
    """년-월-일-시-분-초 형식 문자열"""
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def recv_full_request(conn):
    """헤더의 Content-Length 를 보고 본문까지 모두 수신한다."""
    data = b""

    # 1) 헤더 끝(\r\n\r\n)까지 읽기
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            return data
        data += chunk

    header_blob, body = data.split(b"\r\n\r\n", 1)

    # 2) Content-Length 파싱
    m = re.search(rb"Content-Length:\s*(\d+)", header_blob, re.IGNORECASE)
    if not m:
        return data

    content_length = int(m.group(1))

    # 3) 본문이 다 찰 때까지 계속 수신
    while len(body) < content_length:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            break
        body += chunk

    return header_blob + b"\r\n\r\n" + body


def save_raw_request(raw):
    """실습 1: 요청 전체를 이진 파일로 저장"""
    os.makedirs(REQUEST_DIR, exist_ok=True)
    path = os.path.join(REQUEST_DIR, f"{timestamp()}.bin")
    with open(path, "wb") as f:
        f.write(raw)
    print(f"  [실습1] 원본 저장: {path} ({len(raw):,} bytes)")
    return path


def get_boundary(header_blob):
    """Content-Type 헤더에서 multipart boundary 추출"""
    m = re.search(rb'boundary=(?:"([^"]+)"|([^\s;]+))', header_blob, re.IGNORECASE)
    if not m:
        return None
    return m.group(1) or m.group(2)


def extract_images(raw):
    """실습 2: multipart 본문에서 이미지 파트를 골라 파일로 저장"""
    if b"\r\n\r\n" not in raw:
        return []

    header_blob, body = raw.split(b"\r\n\r\n", 1)
    boundary = get_boundary(header_blob)
    if not boundary:
        print("  [실습2] multipart 요청이 아님 - 건너뜀")
        return []

    os.makedirs(IMAGE_DIR, exist_ok=True)
    delimiter = b"--" + boundary
    saved = []

    # 파트 단위로 분리
    for idx, part in enumerate(body.split(delimiter)):
        part = part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue

        part_header, part_body = part.split(b"\r\n\r\n", 1)
        part_body = part_body.rstrip(b"\r\n")  # 파트 끝 개행 제거

        # Content-Type 확인 - 이미지가 아니면 통과
        ctype_m = re.search(rb"Content-Type:\s*([^\r\n;]+)", part_header, re.IGNORECASE)
        if not ctype_m:
            continue
        ctype = ctype_m.group(1).strip().decode("utf-8", "replace").lower()
        if not ctype.startswith("image/"):
            continue

        # 원본 파일명 확보 (없으면 Content-Type 기준 확장자 사용)
        fname_m = re.search(rb'filename="([^"]*)"', part_header)
        original = fname_m.group(1).decode("utf-8", "replace") if fname_m else ""
        ext = os.path.splitext(original)[1] or EXT_MAP.get(ctype, ".bin")

        path = os.path.join(IMAGE_DIR, f"{timestamp()}-{idx}{ext}")
        with open(path, "wb") as f:
            f.write(part_body)

        print(f"  [실습2] 이미지 저장: {path} ({len(part_body):,} bytes, {ctype})")
        saved.append(path)

    if not saved:
        print("  [실습2] 이미지 파트를 찾지 못함")
    return saved


def print_summary(raw):
    """요청 라인과 주요 헤더를 콘솔에 표시"""
    head = raw.split(b"\r\n\r\n", 1)[0]
    lines = head.split(b"\r\n")
    if lines:
        print(f"  요청: {lines[0].decode('utf-8', 'replace')}")
    for line in lines[1:]:
        low = line.lower()
        if low.startswith((b"content-type:", b"content-length:", b"authorization:")):
            print(f"  {line.decode('utf-8', 'replace')}")


def build_response(raw_path, images):
    """클라이언트에 돌려줄 간단한 JSON 응답"""
    img_list = ", ".join(f'"{os.path.basename(p)}"' for p in images)
    body = (
        "{"
        '"status": "ok", '
        f'"saved_request": "{os.path.basename(raw_path)}", '
        f'"saved_images": [{img_list}]'
        "}"
    ).encode("utf-8")

    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    return header + body


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)

        print("=" * 55)
        print(f"  Socket Server 시작 : http://{HOST}:{PORT}")
        print(f"  요청 저장 폴더     : ./{REQUEST_DIR}/")
        print(f"  이미지 저장 폴더   : ./{IMAGE_DIR}/")
        print("  종료하려면 Ctrl+C")
        print("=" * 55)

        count = 0
        while True:
            conn, addr = server.accept()
            count += 1
            with conn:
                print(f"\n[{count}] 접속: {addr[0]}:{addr[1]}")
                try:
                    raw = recv_full_request(conn)
                    if not raw:
                        print("  빈 요청 - 무시")
                        continue

                    print_summary(raw)
                    raw_path = save_raw_request(raw)
                    images = extract_images(raw)

                    conn.sendall(build_response(raw_path, images))
                except Exception as e:
                    print(f"  오류: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
