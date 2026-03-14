from app.config import GROQ_API_KEY
import os
import sys
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
import pyperclip


#safe settings
RMS_THRESHOLD = 600
MIN_TEXT_LEN = 3
COMMAND_COOLDOWN = 1.2


if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


APP_REGISTRY = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
}

LAUNCHED_PROCESSES = []

groq_client = Groq(api_key=GROQ_API_KEY)


# tts using edge_tts

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


def is_audio_silent(audio):
    rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
    return rms < RMS_THRESHOLD


def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="en",
            prompt="This is English speech."
        )
    return transcription.text


# analyzing request and qualification using groq(chatgpt)

def interpret_command(user_text):
    print(f"[DEBUG] User: '{user_text}'", flush=True)

    chat = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{
            "role": "user",
            "content": (
                "You are a PC voice assistant. "
                "Classify the command strictly into JSON with keys: intent, value. "
                "Intents: open_app, type_text, type_telegram, question, exit, "
                "start_mouse, pause_mouse, resume_mouse. "
                "Return strict JSON only.\n"
                f"User command: {user_text}"
            )
        }]
    )

    response = chat.choices[0].message.content.strip()
    print(f"[DEBUG] GPT: '{response}'", flush=True)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"intent": "question", "value": user_text}


def answer_question(question):
    chat = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{
            "role": "user",
            "content": f"Answer briefly in English: {question}"
        }]
    )
    return chat.choices[0].message.content.strip()


# PC control

def open_via_start_menu(app_name):
    pyautogui.press("win")
    time.sleep(1)
    pyautogui.write(app_name)
    time.sleep(1)
    pyautogui.press("enter")


def open_application(app_name):
    app_name = app_name.lower()

    if app_name in APP_REGISTRY:
        try:
            proc = subprocess.Popen([APP_REGISTRY[app_name]])
            LAUNCHED_PROCESSES.append((proc, APP_REGISTRY[app_name]))
        except Exception:
            open_via_start_menu(app_name)
        return f"Opening {app_name}"

    open_via_start_menu(app_name)
    return f"Trying to open {app_name}"


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

    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    except Exception:
        pyautogui.write(text, interval=0.03)

    return "Typing text"


def type_text_in_telegram(text):
    if focus_app_window("Telegram"):
        time.sleep(0.5)

        try:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.write(text, interval=0.03)

        pyautogui.press("enter")
        return "Message sent"

    return "Telegram not found"


# executing function

def execute_intent(intent, value, vision_enabled, running_flag):
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
        return "Mouse control enabled"

    elif intent == "pause_mouse":
        vision_enabled.value = False
        return "Mouse control disabled"

    elif intent == "resume_mouse":
        vision_enabled.value = True
        return "Mouse control resumed"

    elif intent == "exit":
        running_flag.value = False

        for proc, _ in LAUNCHED_PROCESSES:
            if proc.poll() is None:
                proc.terminate()

        return "Goodbye"

    return None


# main loop

def main(vision_enabled, running_flag):
    speak_sync("Voice assistant at your service!")

    last_command_time = 0

    while running_flag.value:
        try:
            audio_path, audio_data = record_audio()

            if is_audio_silent(audio_data):
                os.remove(audio_path)
                continue

            user_text = transcribe_audio(audio_path)
            os.remove(audio_path)

            user_text = user_text.strip().lower()

            if len(user_text) < MIN_TEXT_LEN:
                continue

            now = time.time()
            if now - last_command_time < COMMAND_COOLDOWN:
                continue

            data = interpret_command(user_text)

            phrase = execute_intent(
                data.get("intent"),
                data.get("value"),
                vision_enabled,
                running_flag
            )

            last_command_time = now

            if phrase:
                speak_sync(phrase)

            if data.get("intent") == "exit":
                break

            time.sleep(0.15)

        except Exception as e:
            print("Error:", str(e), flush=True)
