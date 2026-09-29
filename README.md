# 🔌 Python Socket Server

클라이언트(`curl`)의 HTTP Request를 직접 수신·파싱하는 소켓 서버 실습

> 작성자: 신지수 · 경희대학교 컴퓨터공학과

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Socket](https://img.shields.io/badge/socket-TCP-orange?style=flat)

---

## 📋 과제 내용

| 실습 | 요구사항 | 구현 함수 |
|:---:|:---|:---|
| **1** | 클라이언트 요청을 그대로 `request/` 하위에 `년-월-일-시-분-초.bin` 이진파일로 저장 | `save_raw_request()` |
| **2** | 멀티파트로 전송받은 이미지 데이터를 별도 이미지 파일로 저장 후 확인 | `extract_images()` |

---

## 📁 디렉터리 구조

```
socket_practice/
├── socket_server.py                    # 소켓 서버 본체
├── test.jpg                            # 테스트용 이미지 (원본)
├── request/
│   └── 2026-09-29-11-27-37.bin         # [실습1] 요청 원본 이진파일
├── images/
│   └── 2026-09-29-11-27-37-6.jpg       # [실습2] 추출된 이미지
└── README.md
```

---

## 🚀 실행 방법

### 1. 서버 실행

```bash
python socket_server.py
```

```
=======================================================
  Socket Server 시작 : http://127.0.0.1:8000
  요청 저장 폴더     : ./request/
  이미지 저장 폴더   : ./images/
  종료하려면 Ctrl+C
=======================================================
```

### 2. curl로 요청 전송 (다른 터미널)

```bash
curl -X POST -S \
  -H "Authorization: JWT b181ce4155b7413ebd1d86f1379151a7e035f8bd" \
  -H 'Accept: application/json' \
  -F "author=1" \
  -F "title=curl 테스트" \
  -F "text=API curl로 작성된 API 테스트 입력 입니다." \
  -F "created_date=2026-09-29T11:27:00+09:00" \
  -F "published_date=2026-09-29T11:27:00+09:00" \
  -F "image=@test.jpg;type=image/jpeg" \
  http://127.0.0.1:8000/api_root/Post/
```

---

## ✅ 실행 결과

### 서버 콘솔 출력

```
[1] 접속: 127.0.0.1:41730
  요청: POST /api_root/Post/ HTTP/1.1
  Authorization: JWT b181ce4155b7413ebd1d86f1379151a7e035f8bd
  Content-Length: 4115
  Content-Type: multipart/form-data; boundary=------------------------UM3tVllhsZujBNGR1n14Os
  [실습1] 원본 저장: request/2026-09-29-11-27-37.bin (4,395 bytes)
  [실습2] 이미지 저장: images/2026-09-29-11-27-37-6.jpg (3,282 bytes, image/jpeg)
```

### 클라이언트가 받은 응답

```json
{
  "status": "ok",
  "saved_request": "2026-09-29-11-27-37.bin",
  "saved_images": ["2026-09-29-11-27-37-6.jpg"]
}
```

### 저장된 `.bin` 파일 내용 (앞부분)

```http
POST /api_root/Post/ HTTP/1.1
Host: 127.0.0.1:8000
User-Agent: curl/8.5.0
Authorization: JWT b181ce4155b7413ebd1d86f1379151a7e035f8bd
Accept: application/json
Content-Length: 4115
Content-Type: multipart/form-data; boundary=------------------------UM3tVllhsZujBNGR1n14Os

--------------------------UM3tVllhsZujBNGR1n14Os
Content-Disposition: form-data; name="author"

1
--------------------------UM3tVllhsZujBNGR1n14Os
...
```

### 🔍 이미지 무결성 검증

원본과 저장된 이미지의 MD5 해시가 **완전히 일치**한다.

```bash
$ md5sum test.jpg images/2026-09-29-11-27-37-6.jpg
233835eda69306588b5aa942b6319063  test.jpg
233835eda69306588b5aa942b6319063  images/2026-09-29-11-27-37-6.jpg
```

```bash
$ file images/2026-09-29-11-27-37-6.jpg
JPEG image data, JFIF standard 1.01, baseline, precision 8, 200x150, components 3
```

> [!NOTE]
> 바이트 단위로 손실 없이 복원되었음을 의미한다.

---

## ⚙️ 동작 원리

<details>
<summary>👉 클릭해서 펼치기</summary>

### 1) 요청 전체 수신 — `recv_full_request()`

TCP는 스트림이라 `recv()` 한 번으로 전체가 오지 않는다. 따라서

1. `\r\n\r\n`(헤더 끝)이 나올 때까지 읽는다
2. 헤더에서 `Content-Length`를 파싱한다
3. 본문 길이가 그 값에 도달할 때까지 계속 읽는다

이 과정이 없으면 **이미지가 잘린 채로 저장**된다.

### 2) multipart 파싱 — `extract_images()`

`Content-Type` 헤더의 `boundary` 값으로 본문을 파트 단위로 자른다.

```
Content-Type: multipart/form-data; boundary=----XXXX
                                            ↑ 이 값

------XXXX
Content-Disposition: form-data; name="title"

curl 테스트
------XXXX
Content-Disposition: form-data; name="image"; filename="test.jpg"
Content-Type: image/jpeg          ← 이미지 파트만 골라냄

<이진 데이터>
------XXXX--
```

각 파트에서 `Content-Type`이 `image/`로 시작하는 것만 파일로 저장한다.

### 3) 파일명 규칙

| 항목 | 형식 | 예시 |
|:---|:---|:---|
| 요청 원본 | `%Y-%m-%d-%H-%M-%S.bin` | `2026-09-29-11-27-37.bin` |
| 이미지 | `%Y-%m-%d-%H-%M-%S-{파트번호}{확장자}` | `2026-09-29-11-27-37-6.jpg` |

확장자는 `filename=` 값에서 가져오고, 없으면 `Content-Type`으로 추론한다.

</details>

---

## 🧪 추가 테스트

| 케이스 | 결과 |
|:---|:---|
| JPEG 단일 전송 | ✅ 저장 성공 (MD5 일치) |
| JPEG + PNG 동시 전송 | ✅ 2개 모두 개별 저장 |
| 일반 GET 요청 (multipart 아님) | ✅ `.bin`만 저장, 이미지 건너뜀 |
| 한글 필드값 | ✅ 정상 저장 |

---

## 📌 주요 코드

```python
def recv_full_request(conn):
    """헤더의 Content-Length 를 보고 본문까지 모두 수신한다."""
    data = b""
    while b"\r\n\r\n" not in data:          # 헤더 끝까지
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            return data
        data += chunk

    header_blob, body = data.split(b"\r\n\r\n", 1)
    m = re.search(rb"Content-Length:\s*(\d+)", header_blob, re.IGNORECASE)
    if not m:
        return data

    content_length = int(m.group(1))
    while len(body) < content_length:        # 본문이 다 찰 때까지
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            break
        body += chunk

    return header_blob + b"\r\n\r\n" + body
```

---

## 🔧 환경

- Python 3.11
- 표준 라이브러리만 사용 (`socket`, `os`, `re`, `datetime`)
- 클라이언트: [curl](https://curl.se/download.html) 8.5.0

---

<div align="center">

**Made with ❤️ by 신지수**

</div>
