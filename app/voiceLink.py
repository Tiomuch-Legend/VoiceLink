from app.config import groq_api_key
import os
import time
import json
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import pyautogui
import subprocess
import pygetwindow as gw
import asyncio
from groq import Groq
import edge_tts
import pygame

# Application registry

APP_REGISTRY = {
    "блокнот": "notepad.exe",
    "калькулятор": "calc.exe",
    "малюнок": "mspaint.exe",
}

# Groq client initialization

groq_client = Groq(api_key=groq_api_key)

# EDGE TTS + PYGAME

async def generate_tts_to_file(text, filename):
    communicate = edge_tts.Communicate(text, voice="uk-UA-Standard-A")
    await communicate.save(filename)

def speak_sync(text):
    if not text:
        return
    print("Асистент:", text)
    tts_file = "temp_tts.mp3"
    asyncio.run(generate_tts_to_file(text, tts_file))

    pygame.mixer.init()
    pygame.mixer.music.load(tts_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.quit()
    os.remove(tts_file)

# Audio recording

def record_audio(duration=5, sample_rate=16000):
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.int16
    )
    sd.wait()
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.write(temp_file.name, sample_rate, audio)
    return temp_file.name, audio

# Silence check

def is_audio_silent(audio, threshold=500):
    return np.max(np.abs(audio)) < threshold

# Trasnscription

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f
        )
    return transcription.text

# GPT interpretation

def interpret_command(user_text):
    chat = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": (
                    "Ти голосовий помічник для ПК. "
                    "Класифікуй команду у JSON з ключами: intent, value. "
                    "Intents: open_app, type_text, type_telegram, question, exit, "
                    "start_mouse, pause_mouse, resume_mouse. "
                    "Поверни строгий JSON.\n"
                    f"Команда користувача: {user_text}"
                )
            }
        ]
    )
    response = chat.choices[0].message.content.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"intent": "question", "value": user_text}

def answer_question(question):
    chat = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": f"Відповідай коротко: {question}"}]
    )
    return chat.choices[0].message.content.strip()

#  PC control functions

def open_via_start_menu(app_name):
    pyautogui.press("win")
    time.sleep(1)
    pyautogui.write(app_name)
    time.sleep(1)
    pyautogui.press("enter")

def open_application(app_name):
    app_name = app_name.lower()
    if app_name in APP_REGISTRY:
        subprocess.Popen(APP_REGISTRY[app_name])
        return f"Відкриваю {app_name}"
    else:
        open_via_start_menu(app_name)
        return f"Намагаюся відкрити {app_name}"

def focus_app_window(app_title, wait_time=1):
    try:
        window = gw.getWindowsWithTitle(app_title)[0]
        window.activate()
        time.sleep(wait_time)
        return True
    except IndexError:
        return False

def type_text_anywhere(text, delay=2):
    time.sleep(delay)
    pyautogui.write(text, interval=0.03)
    return "Друкую текст"

def type_text_in_telegram(text):
    if focus_app_window("Telegram"):
        time.sleep(0.5)
        pyautogui.write(text, interval=0.03)
        pyautogui.press("enter")
        return "Повідомлення надіслано в Telegram"
    return "Вікно Telegram не знайдено"

# Intent execution

def execute_intent(intent, value, vision_enabled):
    if intent == "open_app":
        return open_application(value)
    elif intent == "type_text":
        return type_text_anywhere(value)
    elif intent == "type_telegram":
        return type_text_in_telegram(value)
    elif intent == "question":
        return answer_question(value)
    elif intent == "start_mouse":
        vision_enabled.value = True
        return "Управління мишею увімкнено"
    elif intent == "pause_mouse":
        vision_enabled.value = False
        return "Управління мишею призупинено"
    elif intent == "resume_mouse":
        vision_enabled.value = True
        return "Управління мишею відновлено"
    elif intent == "exit":
        return "До побачення"
    else:
        return "Не зрозумів команду"

# Main audio assitant loop

def main(vision_enabled):
    speak_sync("Голосовий асистент запущено. Управління мишею вимкнено.")

    while True:
        try:
            audio_path, audio_data = record_audio()
            if is_audio_silent(audio_data):
                os.remove(audio_path)
                continue

            user_text = transcribe_audio(audio_path)
            os.remove(audio_path)

            # Minimal command length check

            if not user_text.strip() or len(user_text.strip()) < 2:
                continue

            data = interpret_command(user_text)
            phrase = execute_intent(data.get("intent"), data.get("value"), vision_enabled)
            if phrase:
                speak_sync(phrase)

            if data.get("intent") == "exit":
                break

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Помилка:", e)
            speak_sync("Сталася помилка")

if __name__ == "__main__":
    from multiprocessing import Value
    main(Value('b', False))
