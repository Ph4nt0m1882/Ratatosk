from pathlib import Path

import cv2


def extract_video_thumbnail_webp(
    video_path: Path,
    max_dimension: int = 1280,
    quality: int = 80,
) -> bytes:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        raw_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        target_frame = 0
        if 0 < fps < 1000 and 0 < raw_frames < 1e9:
            total_frames = int(raw_frames)
            frame_at_1s = int(fps * 1.0)
            frame_at_10pct = int(total_frames * 0.10)
            target_frame = min(frame_at_1s, frame_at_10pct, total_frames - 1)

        if target_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        success, frame = cap.read()

        if not success or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, frame = cap.read()
            if not success or frame is None:
                raise RuntimeError(f"No visible frame available : {video_path}")

        h, w = frame.shape[:2]
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        encode_params = [cv2.IMWRITE_WEBP_QUALITY, quality]
        ok, buffer = cv2.imencode(".webp", frame, encode_params)
        if not ok:
            raise RuntimeError("Failed to encode WebP with OpenCV")

        return buffer.tobytes()

    finally:
        cap.release()
