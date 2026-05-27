# se-tools

Systems / Infra Engineering 툴 모음. 각 툴은 독립 디렉토리로 구성되고, 컨테이너로 배포 가능하다.

## Tools

| Name | Description | Status |
|---|---|---|
| console-capture | Slack bot 호출 기반으로 서버 BMC / VM 콘솔 스크린샷을 캡쳐 & Slack Upload | MVP |

> 추가 툴은 같은 패턴(자체 `pyproject.toml` + `Dockerfile` + `docker-compose.yml`)으로 디렉토리를 늘린다.

## console-capture 빠른 시작 (Docker)

```bash
cd console-capture
docker compose up -d redis worker consumer          # 브로커 + 캡처 워커 + Slack 업로더
docker compose run --rm worker console_capture.request srv-mock-01   # !bmc 입력 시뮬레이션
# 결과 PNG -> console-capture/out/uploads/srv-mock-01.png  (Slack 토큰 없으면 로컬 sink)

docker compose --profile slack up -d slackbot       # 토큰 설정 후 실제 Slack 봇 기동
```

자세한 사용방법 console-capture/README.md 참고.

## 공통 원칙
- 설정은 환경변수 + 로컬 인벤토리/시크릿 파일로 주입. 실 연동(CMDB/Vault)은 인터페이스 구현체만 교체.
- 콘솔 캡처는 민감 권한 — 자격증명은 secret/Vault, 캡처 이미지 retention/채널 ACL을 운영 전 설계할 것.
