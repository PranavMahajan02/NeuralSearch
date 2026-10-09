"""Phase 7A.5-B1: seek-per-sample frame extraction keeps the exact sampled frames."""

import cv2
import numpy as np
import pytest

from app.extractors import video_frames
from app.search.frame_null import FRAME_INTERVAL_S, frame_time_s


def make_video(path, seconds=23, fps=10, size=(64, 48)):
    """Every frame encodes its own number in its pixels, so a wrong frame is detectable."""

    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    for n in range(seconds * fps):
        frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        frame[:, :, 0] = (n % 32) * 8 + 4          # low bits, in steps of 8 (robust to JPEG noise)
        frame[:, :, 1] = (n // 32) * 8 + 4         # high bits
        writer.write(frame)
    writer.release()
    return path


def frame_number_of(path) -> int:

    image = cv2.imread(str(path)).astype(float)
    low, high = round((image[:, :, 0].mean() - 4) / 8), round((image[:, :, 1].mean() - 4) / 8)
    return high * 32 + low


def test_sample_numbers_and_timestamps_match_the_calibration_interval():

    assert video_frames.INTERVAL_SECONDS == FRAME_INTERVAL_S == 5
    assert video_frames.sample_frame_numbers(25, 1000) == list(range(0, 1000, 125))
    assert video_frames.sample_frame_numbers(29.97, 300) == [0, 149, 298]   # int(fps * 5), as before
    assert video_frames.sample_frame_numbers(0, 3) == [0, 1, 2]           # unreadable fps: every frame
    for k, n in enumerate(video_frames.sample_frame_numbers(30, 5000)):
        assert abs(n / 30 - frame_time_s(k)) <= 0.5                        # within +/-0.5 s of the stored time


def test_seeking_returns_exactly_the_frames_of_the_sequential_decode(tmp_path):

    video = make_video(tmp_path / "v.avi")

    seek = video_frames.extract_frames(str(video), str(tmp_path / "seek"))
    sequential = video_frames._sequential(str(video), str(tmp_path / "seq"), 5)

    assert [frame_number_of(p) for p in seek] == [0, 50, 100, 150, 200]
    assert [frame_number_of(p) for p in seek] == [frame_number_of(p) for p in sequential]


def test_unknown_frame_count_falls_back_to_the_sequential_decode(tmp_path, monkeypatch):

    video = make_video(tmp_path / "v.avi", seconds=11)
    calls = []
    real = video_frames._sequential
    monkeypatch.setattr(video_frames, "_sequential", lambda *a: calls.append(1) or real(*a))
    monkeypatch.setattr(video_frames, "_probe", lambda cap: (cap.get(cv2.CAP_PROP_FPS), 0))

    frames = video_frames.extract_frames(str(video), str(tmp_path / "out"))

    assert calls and len(frames) == 3


@pytest.mark.parametrize("name", ["missing.mp4"])
def test_unreadable_video_gives_no_frames(tmp_path, name):

    assert video_frames.extract_frames(str(tmp_path / name), str(tmp_path / "out")) == []
