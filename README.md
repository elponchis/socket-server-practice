# Socket Server

2023105667 신지수

## 실습 내용

- 실습 1: 클라이언트 요청을 `request/년-월-일-시-분-초.bin` 이진파일로 저장
- 실습 2: 멀티파트로 받은 이미지를 `images/` 에 별도 파일로 저장

## 실행

서버 실행

    python socket_server.py

다른 터미널에서 curl로 요청

    curl -X POST -F "title=test" -F "image=@test.jpg;type=image/jpeg" http://127.0.0.1:8000/api_root/Post/

## 결과

- request/2026-09-29-11-27-37.bin - 요청 원본
- images/2026-09-29-11-27-37-6.jpg - 추출된 이미지

원본 test.jpg와 저장된 이미지의 MD5 해시가 일치하는 것을 확인함.
