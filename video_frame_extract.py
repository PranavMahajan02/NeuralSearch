import cv2
import os


def extract_frames(
    video_path,
    output_folder,
    interval=5
):

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    cap = cv2.VideoCapture(
        video_path
    )

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    frame_interval = int(
        fps * interval
    )

    count = 0

    saved = []

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        if count % frame_interval == 0:

            frame_path = os.path.join(
                output_folder,
                f"frame_{len(saved)}.jpg"
            )

            cv2.imwrite(
                frame_path,
                frame
            )

            saved.append(
                frame_path
            )

        count += 1

    cap.release()

    return saved