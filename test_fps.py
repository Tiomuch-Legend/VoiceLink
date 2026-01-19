import cv2
import mediapipe as mp
import numpy as np
import time

# MediaPipe Face Mesh

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# Landmarks

NOSE = 1
UPPER_LIP = 13
LOWER_LIP = 14

# FPS / Tracking stats

frame_count = 0
lost_count = 0
total_count = 0
start_time = time.time()

cap = cv2.VideoCapture(0)
time.sleep(1)

print("Camera test started. Press ESC to exit.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        total_count += 1
        frame_count += 1

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark

            nose = np.array([lm[NOSE].x * w, lm[NOSE].y * h])
            upper_lip = np.array([lm[UPPER_LIP].x * w, lm[UPPER_LIP].y * h])
            lower_lip = np.array([lm[LOWER_LIP].x * w, lm[LOWER_LIP].y * h])

            # Розмітка точок
            cv2.circle(frame, tuple(nose.astype(int)), 4, (0, 255, 0), -1)
            cv2.circle(frame, tuple(upper_lip.astype(int)), 4, (255, 0, 0), -1)
            cv2.circle(frame, tuple(lower_lip.astype(int)), 4, (255, 0, 0), -1)
        else:
            lost_count += 1  # landmark not found + increment lost count

        # Show the frame
        cv2.imshow("Face Mesh Test", frame)

        # Once every 5 seconds, print FPS and loss ratio
        if time.time() - start_time >= 5:
            avg_fps = frame_count / (time.time() - start_time)
            loss_ratio = lost_count / total_count * 100
            print(f"Середній FPS: {avg_fps:.2f}, Втрата трекінгу: {loss_ratio:.2f}%")

            frame_count = 0
            lost_count = 0
            total_count = 0
            start_time = time.time()

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
