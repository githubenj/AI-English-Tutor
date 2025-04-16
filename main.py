import sounddevice as sd
import scipy.io.wavfile
import whisper
import random
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


# ===== GPT-анализ =====
# Старый вариант промпта:
# prompt = f"You are an empathetic English tutor. Analyze this spoken sentence and give kind and constructive feedback on pronunciation, grammar or word choice:\n\n{text}"
def gpt_feedback(text, mode="default"):
    if mode == "text_input":
        prompt = f"""
You are a kind and professional English teacher. The student has submitted a written response. Your feedback should be brief and to the point.

Please do the following:
- Provide kind and constructive feedback on grammar, vocabulary, word choice and structure.
- Explain your choice.
- Suggest improvements, if any.
- If there are any mistakes, show all them in **"before → after"** format.
- Write the text with the corrected mistakes.
- Be kind and encouraging, like a supportive English tutor.

Student's text:        
{text}
"""
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an encouraging English tutor with deep expertise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=170,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    else:
        prompt = f"""
You are a professional English pronunciation and speaking coach. When the student says something, analyze it and give structured, supportive feedback with the following structure:

1. Provide encouraging and constructive feedback
2. Emphasize natural spoken English rhythm and tone.
3. Repeat the sentence with corrected pronunciation, grammar, word choice and intonation after that.

Structure your response like:
💬 Feedback: [Your kind feedback here about pronunciation, word choice, grammar and clarity.]
🗣️ Corrected Sentence: [Your corrected or improved version here, spoken naturally with correct intonation.]"
"""
        prompt += f"\n\nUser said:\n{text}"

    response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system",
             "content": "You are a helpful English tutor with British politeness and supportive tone."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


while True:
    print("\nВыбери режим:")
    print("[1] ⏱ 10 секунд coach")
    print("[2] 💬 Текстовый ввод")
    print("[3] 🗣️ Режим Лапульки-ассистента (выполнение команд и объяснений)")
    print("[4] 🤖 Тренер по произношению (анализ и фидбэк от Лапульки)")
    print("[5] 📚 Dictionary Mode (learn word or idiom deeply)")

    choice = input("Твой выбор (1/2/3/4/5): ").strip()

    # ===== Вариант 1 и 2: фиксированная длительность =====
    if choice == "1":
        seconds = 10


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

    # ===== Вариант 2: текст =====
    elif choice == "2":
        print("💬 Enter your text (press Enter twice to finish):")
        lines = []
        empty_count = 0

        while True:
            line = input()
            if line.strip() == "":
                empty_count += 1
                if empty_count == 2:
                    break
            else:
                empty_count = 0
                lines.append(line)

        recognized_words = "\n".join(lines).strip()
        print("📄 You wrote:", recognized_words)

        # GPT-анализ — используем старый стиль для текстового режима
        comment = gpt_feedback(recognized_words, mode="text_input")
        print("💬 Комментарий Лапушки (GPT):", comment)
        speak_nova(comment)

        # 🔁 Повтор или выход
        print("\nЧто дальше?")
        print("[1] 🔁 Ввести снова")
        print("[2] ❌ Выйти")

        next_action = input("Твой выбор (1/2): ").strip()
        if next_action != "1":
            print("👋 See you next time! I'm always here when you need me 🌟.")
            break
        else:
            continue

    # ===== Вариант 3: Режим ассистента =====
    elif choice == "3":
        def gpt_pronunciation_greeting():
            prompt = "Say a kind and cheerful greeting as an English tutor-assistant who is happy to help the student. Keep it under 15 words and cheerful."
            resp = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a friendly and supportive English pronunciation coach."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.9
            )
            return resp.choices[0].message.content.strip()


        # 💬 Получаем и сразу выводим приветствие от Лапульки-коуча
        greeting = gpt_pronunciation_greeting()
        print("🤖 Лапулька:", greeting)
        speak_nova(greeting)

        while True:
            if not keyboard:
             print("⚠️ Модуль keyboard не установлен. Установи его через: pip install keyboard")
             continue

            stop_flag = threading.Event()


            def stop_recording(event):
                stop_flag.set()


            keyboard.on_press_key("space", stop_recording)

            print("\n🎙️ Assistant mode is active:")
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
                print("⛔ Stopped by you — I’ll be here whenever you need me.💖")

            if current_chunk:
                chunks.append(np.concatenate(current_chunk, axis=0))

            if not chunks:
                print("🫢 Nothing recorded... Let’s try again, sweet voice!")
                continue

            final_audio = np.concatenate(chunks, axis=0)
            scipy.io.wavfile.write(filename, fs, final_audio)
            # print(f"✅ Запись сохранена как {filename}")  # ← тоже убираем

            keyboard.unhook_all()
            # 🤖 Ассистент-GPT отвечает
            print("🔍 Transcribing your speech...")
            result = whisper_model.transcribe(filename)
            recognized = result["text"].strip()
            print("📄 You said:", recognized)

            if not recognized:
                no_input_responses = [
                    "Sorry, I didn't catch that. Could you say it again?",
                    "I didn’t hear you clearly. Please repeat.",
                    "Hmm, I missed that. Would you mind repeating?",
                    "Could you say that one more time?",
                    "I'm here, but I didn't understand. Try again, please!",
                    "Oopsie~ I missed that! Can you say it again, pretty please?",
                    "Tehee~ I didn’t hear you. Wanna try one more time? 💕",
                    "Your voice got shy! Could you speak a little louder, sweetie?",
                    "Nyaa~ I didn’t catch that, but I’m listening! Try again? 🐾",
                    "Hmm... That was too soft for my ears! Say it again? 🌸",
                    "Oh no~ Lapulka didn’t hear you! Could you say it again with love?"
                ]
                message = random.choice(no_input_responses)
                print("😶", message)  # ← ← ← добавь это, чтобы было видно
                speak_nova(message)
                continue


            def gpt_assistant_reply(text):
                prompt = f"""You are a helpful and supportive English tutor. Respond naturally and clearly to what the user says. Keep your answers short and to the point, giving explanations, corrections, or encouragement where needed.

User said: "{text}"
"""
                resp = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a kind and professional English tutor."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=130,
                    temperature=0.7
                )
                return resp.choices[0].message.content.strip()


            reply = gpt_assistant_reply(recognized)
            print("🤖 Лапулька:", reply)
            speak_nova(reply)

            if any(word in recognized.lower() for word in ["exit", "quit", "выйти", "стоп"]):
                speak_nova("Okay, see you next time!")
                break



    elif choice == "4":
        def gpt_pronunciation_greeting():
            prompt = "Say a friendly and encouraging greeting as an English pronunciation coach. Keep it under 15 words and cheerful."
            resp = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a friendly and supportive English pronunciation coach."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.9
            )
            return resp.choices[0].message.content.strip()


        # 💬 Получаем и сразу выводим приветствие от Лапульки-коуча
        greeting = gpt_pronunciation_greeting()
        print("🤖 Лапулька:", greeting)
        speak_nova(greeting)

        if not keyboard:
            print("⚠️ Модуль keyboard не установлен. Установи его через: pip install keyboard")
            continue

        while True:
            stop_flag = threading.Event()

            def stop_recording(event):
                stop_flag.set()

            keyboard.on_press_key("space", stop_recording)

            print("\n🎙️ 🗣️ Тренер по произношению включен:")
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
                print("⛔ Stopped by you — I’ll be here whenever you need me.💖")

            if current_chunk:
                chunks.append(np.concatenate(current_chunk, axis=0))

            if not chunks:
                print("🫢 Nothing recorded... Let’s try again, sweet voice!")
                continue

            final_audio = np.concatenate(chunks, axis=0)
            scipy.io.wavfile.write(filename, fs, final_audio)

            keyboard.unhook_all()

            # 🔍 Распознавание
            result = whisper_model.transcribe(filename, language="en")
            recognized = result["text"].strip()

            import random


            not_recognized_phrases = [
                "Oops, I didn’t catch that. Could you please say it again?",
                "Hmm, I couldn’t quite hear that. Try one more time?",
                "I missed that one, love. Let’s try again 💫",
                "Say that again for me, sweetie 💗",
                "Can you repeat that a little louder? I’m all ears! 🐰",
                "Could you speak up a little bit? I really want to hear you clearly 🎀",
                "Let’s try that again together, darling ✨",
                "Oh no, I missed that. Want to give it another try? 💕",
                "That one slipped past me! Say it one more time, please 🌈",
                "Just one more time, cutie 🌟 I’m listening with all my heart 💞",
                "It sounded soft like a whisper... mind saying it again? 🎧",
                "Hmm, I blinked for a second 😳 Could you repeat that?",
                "You sounded adorable, but I need to hear you again 💖"
            ]

            if not recognized:
                message = random.choice(not_recognized_phrases)
                print("😶 " + message)
                speak_nova(message)
                continue

            print("📄 You said:", recognized)


            # 💬 Ответ GPT
            def gpt_pronunciation_reply(text):
                prompt = f"""

You are a professional English pronunciation and speaking coach. When the student says something, analyze it and give structured, supportive feedback with the following structure:

1. Provide encouraging and constructive feedback
2. Emphasize natural spoken English rhythm and tone.
3. Repeat the sentence with corrected pronunciation, grammar, word choice and intonation after that.

Structure your response like:

💬 Feedback: [Your kind feedback here about pronunciation, word choice, grammar and clarity.]
🗣️ Corrected Sentence: [Your corrected or improved version here, spoken naturally with correct intonation.]

Student's sentence:
{text}
"""
                resp = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a supportive English pronunciation coach."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                return resp.choices[0].message.content.strip()

            result = gpt_pronunciation_reply(recognized)
            print("🤖 Лапулька:", result)

            # 🔊 Озвучка
            speak_nova(result)

            # 🛑 Выход по команде
            if any(word in recognized.lower() for word in ["exit", "quit", "выйти", "стоп"]):
                speak_nova("Okay, see you next time!")
                break

    elif choice == "5":
        while True:
            print("\n📚 Dictionary Mode activated! Enter a word or idiom you'd like to learn.")
            user_word = input("🔤 Enter a word or phrase: ").strip()

            if not user_word:
                print("❌ No input received. Returning to main menu.")
                continue

            # Озвучка слова
            speak_nova(user_word)

            # 🎀 Украшаем слово эмоджи (для текста)
            emoji_choices = ["💗", "💫", "🌟", "💕", "🌸", "🎀", "🩷", "✨", "🍬", "🫶", "🧁", "🦋", "🌈", "💖", "🌼", "🌺", "🥰", "🍭", "🐣", "💝"]
            random_emoji = random.choice(emoji_choices)
            decorated_word = f"{random_emoji}{user_word}{random_emoji}"

            # GPT-запрос
            def gpt_dictionary_explanation(word):
                prompt = f"""
Please provide a detailed English dictionary-style explanation for the following word or phrase: "{decorated_word}"

Provide a detailed and structured explanation as follows:

Include:
1. British and American pronunciation in IPA.
2. Part of speech and if it's formal/informal.
3. Meaning(s) in clear English.
4. Notes like: transitive/intransitive (for verbs), countable/uncountable (for nouns). Comparative/Superlative (if adjective):  
- Comparative: [e.g. friendlier / more friendly]  
- Superlative: [e.g. friendliest / most friendly] 
5. Typical prepositions or collocations.
6. Synonyms or similar expressions.
7. 2–3 real-life usage examples.
8. Usage tips, frequency, common mistakes, cultural context, etc.
"""
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a friendly dictionary expert and English tutor."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()

            # 🔎 Получаем результат
            result = gpt_dictionary_explanation(user_word)
            print(f"\n📘 Dictionary Entry for {decorated_word}:\n")
            print(result)

            # 🎤 Озвучиваем только слово
            speak_nova(user_word)

            # 💡 Повторная опция после показа информации
            while True:
                print("\nWhat would you like to do next?")
                print("[1] 🔁 Repeat the pronunciation")
                print("[2] 📚 Enter another word or phrase")
                print("[3] ❌ Return to main menu")

                followup = input("Your choice (1/2/3): ").strip()

                if followup == "1":
                    speak_nova(user_word)  # Повторяем произношение
                elif followup == "2":
                    break  # Выйдем из while, начнётся снова режим 5
                elif followup == "3":
                    print("👋 Returning to main menu!")
                    continue_outer_loop = True
                    break
                else:
                    print("🌀 Hmm, that option doesn’t exist. Try again?")

            if 'break_outer' in locals() and break_outer:
                del break_outer
                break  # Полный выход из режима 5


    else:
        print("🌀 Hmm... I think you typed something mysterious! Try again?")
        continue

    # ===== Распознавание и фидбэк =====
    print("🔍 Transcribing your speech...")
    result = whisper_model.transcribe(filename)
    recognized = result["text"]


    def convert_digits_to_words(text):
        return re.sub(r'\b\d+\b', lambda x: num2words(int(x.group())), text)


    recognized_words = convert_digits_to_words(recognized)
    print("📄 You said:", recognized_words)

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

    # Комментарий Лапушки только для режимов 1 и 4 (не для режима 3)
    if choice in ["1", "4"]:
        comment = gpt_feedback(recognized_words)
        print("💬 Комментарий Лапушки (GPT):", comment)
        speak_nova(comment)

        # 🔁 Повтор или выход
        print("\nЧто дальше?")
        print("[1] 🔁 Записать снова")
        print("[2] ❌ Выйти")

        next_action = input("Твой выбор (1/2): ").strip()
        if next_action != "1":
            print("👋 See you next time! I'm always here when you need me 🌟.")
            break  # ← теперь всё ок!
