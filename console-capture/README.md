# console_capture — BMC/VM 콘솔 스크린샷 → Message Queue → Slack (MVP)

Slack에서 `!bmc <SERIAL|HOSTNAME>`(또는 `/bmc ...`)을 입력하면 → **CMDB에서 벤더·IPMI IP 조회** →
**벤더별 로그인/캡처 분기** → **PNG를 base64로 인코딩해 Message Queue로 전달** → **Slack 봇이 파일을
write 후 같은 스레드에 업로드**하는 파이프라인의 동작 모델. 설정 일부만 바꾸면 어느 환경에서도 돌아가도록 설계했다.

> 운영/벤더/펌웨어 노하우는 [`docs/OPERATIONS.md`](docs/OPERATIONS.md) 참고.

## 아키텍처 (3-stage, 2-queue)

```
[입력]                         [요청 큐]            [캡처]                [결과 큐]           [출력]
Slack !bmc / /bmc  ─publish─►  bmc_screen_request ─►  worker            ─►  bmc_screen_result ─►  consumer
  (또는 토큰 없이                                       ├ CMDB resolve                              ├ base64 decode/검증
   console_capture.request)                                    │  (vendor, ipmi_ip)                        ├ captures/<host>.png write
                                                       ├ Secret resolve (creds)                    └ Slack files_upload_v2
                                                       ├ vendor adapter.capture() → PNG               (토큰 없으면 uploads/ sink)
                                                       └ base64 + 결과 발행
```

- **즉시 ack + 비동기**: 봇은 입력 즉시 "🔍 캡처 중"을 답하고, 결과는 worker→consumer를 거쳐 스레드에 올라온다.
- **네트워크 분리**: worker를 BMC OOB망 안에 두고 broker로 아웃바운드만 — Slack(인터넷)과 BMC망이 직접 닿지 않는다.
- 모든 실패(CMDB 미스/벤더 미지원/캡처 오류)는 `status=error`로 발행돼 스레드에 사람이 읽을 메시지로 표시된다.

### 컴포넌트

| 파일 | 역할 |
|---|---|
| `slackbot.py` | Slack 봇 (`!bmc` 메시지 + `/bmc` 슬래시, Socket Mode). 입력 → 요청 큐 발행 |
| `request.py` | 토큰 없이 입력을 시뮬레이션하는 CLI (`!bmc` 대용) |
| `worker.py` | 요청 소비 → CMDB·Secret resolve → 벤더 캡처 → 결과 발행 |
| `consumer.py` | 결과 소비 → PNG write → Slack 업로드(또는 로컬 sink) |
| `cmdb.py` / `secrets_resolver.py` | CMDB/Secret 추상화 + 로컬 구현체 |
| `adapters/*.py` | 벤더별 로그인·캡처 (dell/lenovo 실코드, hpe/supermicro/vmware stub) |
| `producer.py` | (저수준) CMDB 없이 `-V vendor -H ip` 직접 캡처 — 어댑터 단위 테스트용 |

## 벤더 매트릭스

| 벤더(alias) | 상태 | 경로 |
|---|---|---|
| `mock` | ✅ 완전 동작 | 합성 PNG (로컬 데모 엔진) |
| `dell`/`idrac` | ✅ 실코드 | Redfish OEM `ExportServerScreenShot` (fw≥7) |
| `lenovo`/`xcc` | ✅ 실코드 | `rp_screenshot` → PNG download (디코더 0) |
| `hpe`/`ilo` | ⚠️ probe만 | Redfish capability 확인 (live 디코더는 프로덕션) |
| `supermicro` | ⚠️ probe만 | Redfish 도달성 (스크린샷 API 미확인) |
| `vmware`/`esxi` | 🟡 스캐폴딩 | vim25 `CreateScreenshot`/`/screen?id=` (라이선스로 구성만) |

## 빠른 시작 — 토큰 없이 (어느 환경이든)

```powershell
python -m pip install -e .          # 의존성 + 패키지
docker compose up -d redis          # 브로커
copy .env.example .env              # 필요시 수정
# inventory.yaml = 더미 인벤토리(이미 포함). 본인 환경이면 여기에 서버 추가.

# 3-stage 원샷 데모 (--once = 처리 후 종료)
python -m console_capture.request srv-mock-01     # 입력(=!bmc) 시뮬레이션
python -m console_capture.worker  --once          # CMDB resolve → mock 캡처 → 결과 발행
python -m console_capture.consumer --once         # PNG write + uploads\srv-mock-01.png 로 sink
```

실 BMC가 있으면(homelab 등): `inventory.yaml`에 `vendor/ipmi_ip` 추가 + `secrets.yaml`에 자격증명 →
`request.py <serial|hostname>` 하면 worker가 dell/lenovo는 실제 캡처한다.

## Slack 연동 (토큰 발급 후)

1. Slack 앱 생성 → **Socket Mode 활성** → App-level token(`xapp-`, scope `connections:write`) 발급.
2. Bot scopes: `chat:write`, `files:write` (+ `!bmc` 메시지용 `message.channels` 이벤트 구독, `/bmc` 슬래시 커맨드 등록).
3. 봇 토큰(`xoxb-`) 발급, 대상 채널에 봇 초대.
4. `.env`에 `SLACK_BOT_TOKEN`/`SLACK_APP_TOKEN`/`SLACK_CHANNEL`(+ 운영은 `CC_ALLOWED_CHANNELS`) 설정.
5. 3개 프로세스 실행:
   ```powershell
   python -m console_capture.slackbot   # 입력
   python -m console_capture.worker     # 캡처
   python -m console_capture.consumer   # Slack 업로드
   ```
6. 채널에서 `!bmc srv-dell-01` 또는 `/bmc srv-dell-01`, 도움말은 `!bmc help`.

## 다른 환경으로 가져갈 때 — 바꿀 것은 4곳뿐

1. **`.env`** — Redis/Slack 토큰/채널/정책
2. **`inventory.yaml`** — 그 환경의 서버(serial/hostname/vendor/ipmi_ip). 또는 ↓
3. **`cmdb.py`** — 실 CMDB API가 있으면 `CmdbResolver` 인터페이스(`resolve(query)->CmdbRecord`)를 따르는 구현체로 교체하고 worker에서 그것을 주입
4. **`secrets_resolver.py`** — 운영은 `SecretResolver` 인터페이스(`resolve(vendor, ip)->Credential`)를 Vault/Secrets Manager 구현체로 교체

벤더 추가는 `adapters/<vendor>.py` + `adapters/__init__.py` 한 줄(OPERATIONS.md 8장).

## 테스트
```powershell
python -m pytest -q
```

## MVP가 의도적으로 안 다루는 것 (정직)
- HPE live 디코더 / Supermicro 캡처 / VMware 실 캡처는 미구현(probe·스캐폴딩). 호출 시 `vendor_unsupported`로 명시 실패.
- 보안 거버넌스(콘솔 픽셀 secret, 토픽 ACL/retention)는 운영 전개 전 별도 설계 — OPERATIONS.md 3장.
- 로컬 브로커는 Redis Streams. 프로덕션은 Kafka 스왑(`mq.py` 인터페이스 유지).
