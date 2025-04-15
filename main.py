import sounddevice as sd
import scipy.io.wavfile
import whisper
import os
import subprocess
import sys

# Установка зависимостей, если не установлены
def install_if_missing(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_if_missing("pydub")
install_if_missing("simpleaudio")

import time
import pygame
import speech_recognition as sr
import subprocess
import threading
import numpy as np
import winsound
import re
from num2words import num2words
from dotenv import load_dotenv
from openai import OpenAI
from TTS.api import TTS as TTS_API  # ← для озвучки

try:
    import keyboard
except ImportError:
    keyboard = None

# ===== Загрузка API ключа OpenAI =====
pygame.mixer.init()
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ===== Выбор модели =====
print("\nВыбери модель GPT:")
print("[1] 💬 gpt-3.5-turbo (быстрее, дешевле)")
print("[2] 🧠 gpt-4o (умнее, дороже)")

model_choice = input("Твой выбор (1/2): ").strip()
selected_model = "gpt-4o" if model_choice == "2" else "gpt-3.5-turbo"
print(f"✅ Используется модель: {selected_model}")

# ===== Whisper =====
print("🧠 Загружаем Whisper модель на GPU...")
whisper_model = whisper.load_model("base", device="cuda")
print("✅ Whisper работает на видеокарте!")

# ===== Голос Лапушки (TTS - tacotron отключен, используем nova) =====
fs = 16000
filename = "my_voice.wav"

import io
from pydub import AudioSegment
from pydub.playback import play

def speak_nova(text):
    try:
        # Получаем байты аудио
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        # Получаем контент напрямую
        audio_bytes = io.BytesIO(response.content)

        # Проигрываем
        audio = AudioSegment.from_file(audio_bytes, format="mp3")
        play(audio)

    except Exception as e:
        print(f"❌ Ошибка озвучки: {e}")

# ===== Главный цикл =====
# ===== Настройки =====
echo_repeat = False
while True:
    print("\nВыбери режим записи:")
    print("[1] ⏱ 10 секунд")
    print("[2] ⏱ 60 секунд")
    print("[3] 🖐 Ручной режим с паузой и пробелом")
    print("[4] 🗣️ Режим диалога с ассистентом (разговор с Лапулькой)")

    choice = input("Твой выбор (1/2/3/4): ").strip()

    # ===== Вариант 1 и 2: фиксированная длительность =====
    if choice in ["1", "2"]:
        seconds = 10 if choice == "1" else 60

        def countdown(seconds):
            for i in range(seconds, 0, -1):
                print(" " * 50, end="\r")  # Очистка строки
                print(f"⏱ Осталось: {i} сек", end="\r")
                time.sleep(1)
            print(" " * 50, end="\r")

        print(f"\n🎙️ Говори после сигнала ({seconds} секунд)...")
        winsound.Beep(1000, 300)

        timer_thread = threading.Thread(target=countdown, args=(seconds,))
        timer_thread.start()

        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        timer_thread.join()

        scipy.io.wavfile.write(filename, fs, recording)
        print(f"✅ Запись сохранена как {filename}")

    # ===== Вариант 3: ручной режим =====
    elif choice == "3":
        if not keyboard:
            print("⚠️ Модуль keyboard не установлен. Установи его через: pip install keyboard")
            continue

        stop_flag = threading.Event()

        def stop_recording(event):
            stop_flag.set()

        keyboard.on_press_key("space", stop_recording)

        print("\n🎙️ Режим ручной записи включен:")
        print("   ▶️ Нажимай [P], чтобы поставить/снять паузу")
        print("   ⏹ Нажми [пробел], чтобы завершить запись")
        winsound.Beep(1000, 300)

        chunks = []
        paused = False
        chunk_duration = 0.5
        frames_per_chunk = int(fs * chunk_duration)
        current_chunk = []

        try:
            while not stop_flag.is_set():
                if keyboard.is_pressed("p"):
                    paused = not paused
                    print("⏸ Пауза." if paused else "▶️ Продолжение.")
                    time.sleep(0.5)

                if not paused:
                    data = sd.rec(frames_per_chunk, samplerate=fs, channels=1, dtype='int16')
                    sd.wait()
                    current_chunk.append(data)

        except KeyboardInterrupt:
            print("⛔ Прервано вручную.")

        if current_chunk:
            chunks.append(np.concatenate(current_chunk, axis=0))

        if not chunks:
            print("⚠️ Нет записанных данных.")
            continue

        final_audio = np.concatenate(chunks, axis=0)
        scipy.io.wavfile.write(filename, fs, final_audio)
        print(f"✅ Запись сохранена как {filename}")

        keyboard.unhook_all()
    elif choice == "4":
        print("\n🎧 Включён режим диалога. Скажи что-нибудь, я тебя слушаю!")

        while True:
            # 🎤 Запись
            recording = sd.rec(int(6 * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            scipy.io.wavfile.write(filename, fs, recording)

            # 🔍 Распознавание
            result = whisper_model.transcribe(filename)
            recognized = result["text"].strip()
            if not recognized:
                print("😶 Ничего не распознано. Скажи ещё раз...")
                continue

            print("📄 Ты сказал:", recognized)


            # 💬 Ответ GPT
            def gpt_reply(text):
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": text}],
                    max_tokens=200,
                    temperature=0.8
                )
                return response.choices[0].message.content.strip()


            reply = gpt_reply(recognized)
            print("🤖 Лапулька:", reply)

            # 🔊 Озвучка
            speak_nova(reply)

            # 🛑 Выход по команде
            if any(word in recognized.lower() for word in ["exit", "quit", "выйти", "стоп"]):
                speak_nova("Okay, see you next time!")
                break


    else:
        print("❌ Неверный ввод. Попробуй снова.")
        continue

    # ===== Распознавание и фидбэк =====
    print("🔍 Распознаём...")
    result = whisper_model.transcribe(filename)
    recognized = result["text"]

    def convert_digits_to_words(text):
        return re.sub(r'\b\d+\b', lambda x: num2words(int(x.group())), text)

    recognized_words = convert_digits_to_words(recognized)
    print("📄 Ты сказал:", recognized_words)

    # # 🔁 Спросить: повторить голосом?
    # print("\n🔁 Повторить твою фразу голосом Lapulka?")
    # print("[1] Да")
    # print("[2] Нет")
    # echo_choice = input("Твой выбор (1/2): ").strip()
    # echo_repeat = echo_choice == "1"
    # # ===== Jenny повторяет твою речь =====
    # if echo_repeat:
    #    print("🪞 Lapulka повторяет твою фразу...")
    #    subprocess.run([
    #     "tts",
    #     "--text", recognized_words,
    #     "--model_name", "tts_models/en/jenny/jenny",
    #     "--out_path", "lapulka_echo.wav"
    # ])
    # os.system("start lapulka_echo.wav")

    # ===== GPT-анализ =====
    def gpt_feedback(text):
        prompt = f"You are an empathetic English tutor. Analyze this spoken sentence and give kind and constructive feedback on pronunciation, grammar or word choice:\n\n{text}"

        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a helpful English tutor with British politeness and supportive tone."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    comment = gpt_feedback(recognized_words)
    print("💬 Комментарий Лапушки (GPT):", comment)
    speak_nova(comment)

    # 🔁 Повтор или выход
    print("\nЧто дальше?")
    print("[1] 🔁 Записать снова")
    print("[2] ❌ Выйти")

    next_action = input("Твой выбор (1/2): ").strip()
    if next_action != "1":
        print("👋 До встречи, Модель А! Завершаем работу.")
        break
