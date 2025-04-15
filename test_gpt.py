import os
from openai import OpenAI
from dotenv import load_dotenv

# Загружаем ключ
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Подключение к OpenAI
client = OpenAI(api_key=api_key)

# Тестовый запрос
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Say hello to Mодель А like a British butler."}
        ],
        temperature=0.5,
        max_tokens=50
    )

    print("✅ GPT ответил:\n")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ Ошибка при подключении к OpenAI API:")
    print(e)
