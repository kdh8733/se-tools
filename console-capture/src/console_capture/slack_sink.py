"""이미지/텍스트 전송 sink.

토큰+채널이 있고 channel이 'local'이 아니면 Slack(files_upload_v2 / chat_postMessage),
아니면 로컬 디렉토리/로그로 fallback. 덕분에 토큰 없이도 파이프라인 end-to-end 데모 가능."""
from __future__ import annotations

import os
import shutil


def _slack_enabled(token, channel) -> bool:
    return bool(token and channel and channel != "local")


def deliver_image(png_path, *, token, channel, upload_dir, title, comment, thread_ts=None):
    if _slack_enabled(token, channel):
        # files_upload_v2 = files.getUploadURLExternal + files.completeUploadExternal 래퍼(현재 권장 API).
        from slack_sdk import WebClient

        client = WebClient(token=token)
        resp = client.files_upload_v2(channel=channel, thread_ts=thread_ts or None,
                                      file=png_path, title=title, initial_comment=comment)
        file_obj = resp.get("file") or {}
        return {"target": "slack", "ok": bool(resp.get("ok")), "file_id": file_obj.get("id")}

    os.makedirs(upload_dir, exist_ok=True)
    dest = os.path.join(upload_dir, os.path.basename(png_path))
    shutil.copyfile(png_path, dest)
    return {"target": "local", "ok": True, "path": dest,
            "note": "Slack 토큰/채널 미설정 -> 로컬 sink. 설정 시 실제 Slack 업로드."}


def post_text(token, channel, thread_ts, text):
    if _slack_enabled(token, channel):
        from slack_sdk import WebClient

        WebClient(token=token).chat_postMessage(channel=channel, thread_ts=thread_ts or None, text=text)
        return {"target": "slack", "ok": True}
    return {"target": "local", "ok": True, "text": text}
