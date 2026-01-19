from multiprocessing import Process
from app.shared_state import create_shared_state
import app.cv as cv
import app.voiceLink as voiceLink

if __name__ == "__main__":
    vision_enabled = create_shared_state()

    # Start CV (mouse control) and voice assistant in separate processes
    p1 = Process(target=cv.main, args=(vision_enabled,))
    p2 = Process(target=voiceLink.main, args=(vision_enabled,))

    p1.start()
    p2.start()

    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        # Terminate both processes if user presses CTRL+C
        p1.terminate()
        p2.terminate()
        p1.join()
        p2.join()
