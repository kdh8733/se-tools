# console-capture 단일 이미지. command만 바꿔 worker/consumer/slackbot/request로 기동.
FROM python:3.12-slim

WORKDIR /app

# mock 어댑터의 합성 콘솔 PNG가 컨테이너에서도 또렷하게 렌더되도록 TTF 폰트 포함
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 런타임 의존성 설치(개발용 pytest 제외)
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# 컨테이너 내 기본 인벤토리(실배포는 볼륨/ConfigMap으로 덮어쓰기 권장)
COPY inventory.yaml ./

ENV CC_INVENTORY=/app/inventory.yaml \
    CC_CAPTURE_DIR=/data/captures \
    CC_UPLOAD_DIR=/data/uploads

# `python -m <module>` 형태로 실행 -> compose/k8s에서 command만 교체
ENTRYPOINT ["python", "-m"]
CMD ["console_capture.worker"]
