# 운영 가이드 & Know-how — BMC 콘솔 스크린샷

실 환경 전개에서 반복적으로 부딪히는 벤더/펌웨어 특성, 보안, 장애 대응 노하우를 모았다.

## 1. 벤더별 캡처 특성 (한눈에)

| 벤더 | 캡처 방식 | 난이도 | 핵심 주의 |
|---|---|---|---|
| **Lenovo XCC** | `rp_screenshot` API가 BMC 내부에서 PNG 생성 → download | ★☆☆ 가장 쉬움 | 디코더 0줄. API가 직접 이미지를 줘서 안정적 |
| **Dell iDRAC** | fw≥7: Redfish OEM `ExportServerScreenShot` / fw<7: RFB/WebSocket | ★★☆ | **펌웨어로 경로가 갈린다** |
| **VMware ESXi** | hypervisor가 VM 콘솔 PNG 직접(`CreateScreenshot`/`/screen?id=`) | ★★☆ | BMC 아님. 게스트 에이전트 불필요 |
| **HPE iLO** | 공개 와이어 스펙 없음 → BMC가 서빙하는 JS 디코더 포팅 | ★★★ 가장 어려움 | 펌웨어 업데이트에 취약 |
| **Supermicro** | 스크린샷 전용 API **미확인** | ? | 실HW에서 IPMI/CGI/Redfish OEM 검증 필요 |

요점: **Lenovo는 벤더가 API를 제공**해서 쉽고, **HPE는 공개 스펙이 없어** reverse-engineering이 필요하다.

## 2. 펌웨어 버전별 차이 — 가장 흔한 함정

- **Dell**: `FirmwareVersion` major ≥ 7 → Redfish OEM 한 번의 POST. major < 7 → 레거시 RESTGUI + RFB 풀스택. **같은 모델도 펌웨어에 따라 캡처 경로가 다르다.** probe 단계에서 fw를 읽어 분기하라.
- **HPE iLO**: 와이어 스펙이 비공개라 **BMC가 브라우저에 내려주는 JS(state.js 등)가 사실상의 스펙**이다. 펌웨어 업데이트가 그 JS를 바꾸면 디코더가 **조용히 깨진다**(에러 없이 깨진 이미지). 펌웨어 버전별 골든 이미지 회귀가 필요.
- **Lenovo XCC vs XCC2**: 세대별로 로그인 흐름(`get_nonce`, CSP nonce) 차이가 있을 수 있다. 캡처 API 경로 자체는 비교적 안정적.
- **교훈**: "벤더"로만 분기하지 말고 **"벤더 + 펌웨어 버전"**으로 분기하라.

## 3. 자격증명 보안 (중요)

- BMC 자격증명 = **하드웨어 풀권한**(전원·가상미디어·KVM). 평문 노출은 치명적이다.
- **ID/PW를 CMDB·코드·환경변수 평문·로그에 두지 마라.** 캡처 실패 로그/스택트레이스에 password가 새지 않도록 redaction.
- MVP: `secrets.yaml`(gitignore). **운영: Vault / AWS Secrets Manager**로 `SecretResolver` 구현체 교체.
- 최소권한 계정(가능하면 screenshot/read 전용), BMC별 분리 자격증명.
- **콘솔 픽셀 자체가 secret을 담을 수 있다** — BIOS 패스워드 입력 화면, OS 로그인, 복호화된 데이터. 캡처 이미지가 MQ/Slack/저장소에 잔류하므로 **retention·채널 ACL·접근 감사**를 설계하라. (PCI-DSS/ISO 27001 환경이면 필수)

## 4. 네트워크 분리

- BMC는 **OOB 관리망**(인터넷·사내망 비라우팅)에 두는 게 일반적. Slack은 인터넷.
- **worker를 OOB망 안에 두고 broker로 아웃바운드 연결만** 맺어라(인바운드 0). 이 MVP의 2-큐 구조가 그 분리를 그대로 지원한다.
- BMC는 self-signed 인증서가 흔하다 → `CC_TLS_VERIFY=false`가 기본. 운영에선 내부 CA로 검증 켜기 권장.

## 5. 세션 경합 & BMC 부하

- BMC는 약한 임베디드 컨트롤러다. 동시 세션/요청에 취약 → **per-BMC 동시성 1 + rate limit**.
- **iLO `acquire`가 활성 사람 세션을 선점할 수 있다** — 장애 대응 중 콘솔 보던 엔지니어를 쫓아낼 위험. 정책 확인 후, 활성 세션이면 캡처 거부하는 가드 권장.
- 캡처가 hang할 수 있다 → 타임아웃 + (운영) subprocess process-group kill로 좀비 방지.

## 6. 정합성 — 조용히 깨진 PNG 주의

- signature/치수 검증만으로는 **"valid PNG지만 픽셀이 깨진"** 이미지를 못 잡는다. 특히 reverse-engineered 디코더(HPE)는 일부 블록부터 latch되며 깨질 수 있다.
- 운영자가 garbage 화면 보고 오판하는 게 최악. **펌웨어별 골든 이미지 회귀 / perceptual check(SSIM·OCR sanity)** 를 권장.

## 7. 트러블슈팅

| 증상 / error.code | 원인 후보 | 해결 |
|---|---|---|
| `401/403` | 자격증명/scope 문제 | secrets 확인, 계정 권한, X-Auth-Token 만료 |
| WS timeout | GraphicalConsole/KVMIP 비활성 | BMC 설정에서 KVM 활성, probe로 사전 점검 |
| iLO "acquired by another user" | 세션 경합 | 대기 또는 세션 정리(destructive 주의) |
| 검정/일부만 그려진 화면 | coverage 미달, 캡처 타이밍 | 부팅·입력 후 재시도, coverage gate 대기 |
| 응답이 PNG가 아님 | content-type 헤더 신뢰 | **실제 bytes signature로 판단**(TRUST THE BYTES) |
| `inline_payload_too_large` | 화면이 시각적으로 커서 base64 한도 초과 | object store(presigned URL) 경로로 전환 검토 |
| `cmdb_lookup_failed` | 인벤토리 미스/시리얼·호스트네임 오타 | 인벤토리/CMDB 레코드 확인 |
| `vendor_unknown` | CMDB의 vendor 값이 alias 맵에 없음 | `adapters/__init__.py` alias 추가 |
| `vendor_unsupported` | MVP 미구현 벤더(HPE live/Supermicro/VMware) | 해당 벤더 백엔드 구현 |
| `capture_failed` | 네트워크/인증/디코드 오류 | 메시지의 예외 내용 확인, BMC 도달성·자격증명 점검 |

## 8. 새 벤더 추가 (확장)

1. `src/console_capture/adapters/<vendor>.py`에 `probe()` / `capture()` 구현 (반환은 `CaptureResult`).
2. `adapters/__init__.py`의 `_ALIAS` + `_REGISTRY`에 한 줄씩.
3. 인벤토리의 `vendor` 값에 사용. 끝 — manager/router/MQ/Slack은 손대지 않는다.
