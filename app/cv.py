import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time

# PyAutoGUI SAFETY
pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()

# MediaPipe 
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

# Settings
MOVE_SENSITIVITY = 3.5
MAX_MOVE = 20
DEAD_ZONE = 4
MOUTH_OPEN_THRESHOLD = 18
CLICK_COOLDOWN = 0.8

def main(vision_enabled, running_flag): 
    last_click_time = 0
    neutral_nose = None

    cap = cv2.VideoCapture(0)
    time.sleep(1)

    print(" Mouse control starts OFF")
    print(" Use voice: start mouse control / pause mouse control")
    print(" Press 'C' to calibrate neutral head position")
    print(" ESC to exit")

    cv2.namedWindow("Head Controlled Mouse", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Head Controlled Mouse", 480, 360)
    cv2.setWindowProperty("Head Controlled Mouse", cv2.WND_PROP_TOPMOST, 1)

    while cap.isOpened() and running_flag.value:  
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark

            nose = np.array([lm[NOSE].x * w, lm[NOSE].y * h])
            upper_lip = np.array([lm[UPPER_LIP].x * w, lm[UPPER_LIP].y * h])
            lower_lip = np.array([lm[LOWER_LIP].x * w, lm[LOWER_LIP].y * h])

            # Calibration
            if neutral_nose is None:
                neutral_nose = nose.copy()

            # Only move mouse if enabled
            if vision_enabled.value:
                dx = (nose[0] - neutral_nose[0]) * MOVE_SENSITIVITY
                dy = (nose[1] - neutral_nose[1]) * MOVE_SENSITIVITY

                if abs(dx) < DEAD_ZONE: dx = 0
                if abs(dy) < DEAD_ZONE: dy = 0

                dx = np.clip(dx, -MAX_MOVE, MAX_MOVE)
                dy = np.clip(dy, -MAX_MOVE, MAX_MOVE)

                cur_x, cur_y = pyautogui.position()
                new_x = np.clip(cur_x + dx, 0, screen_w - 1)
                new_y = np.clip(cur_y + dy, 0, screen_h - 1)

                pyautogui.moveTo(new_x, new_y, duration=0.03)

                # Mouth click (LMB)
                mouth_open = np.linalg.norm(upper_lip - lower_lip)
                now = time.time()
                if mouth_open > MOUTH_OPEN_THRESHOLD:
                    if now - last_click_time > CLICK_COOLDOWN:
                        pyautogui.click()
                        last_click_time = now

            # Status overlay
            status_text = "MOUSE: ON" if vision_enabled.value else "MOUSE: OFF"
            status_color = (0, 255, 0) if vision_enabled.value else (0, 0, 255)
            cv2.putText(frame, status_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

            # Debug points
            cv2.circle(frame, tuple(nose.astype(int)), 4, (0, 255, 0), -1)
            cv2.circle(frame, tuple(upper_lip.astype(int)), 4, (255, 0, 0), -1)
            cv2.circle(frame, tuple(lower_lip.astype(int)), 4, (255, 0, 0), -1)

        cv2.imshow("Head Controlled Mouse", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            running_flag.value = False  # sign to shut down
            break
        elif key == ord('c'):
            neutral_nose = nose.copy()
            print(" Neutral position calibrated")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    from multiprocessing import Value
    main(Value('b', False), Value('b', True))  # for a standalone testing
