from multiprocessing import Process
from app.shared_state import vision_enabled, running_flag
import app.cv as cv
import app.voiceLink as voiceLink

if __name__ == "__main__":
    # Start CV and voice assistant
    p_cv = Process(target=cv.main, args=(vision_enabled, running_flag))
    p_voice = Process(target=voiceLink.main, args=(vision_enabled, running_flag))

    p_cv.start()
    p_voice.start()

    try:
        p_cv.join()
        p_voice.join()
    except KeyboardInterrupt:
        running_flag.value = False
        p_cv.terminate()
        p_voice.terminate()
        p_cv.join()
        p_voice.join()
