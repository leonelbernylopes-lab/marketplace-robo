import os
import requests
import time

TOKEN = os.environ["TELEGRAM_TOKEN"]

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

offset = 0

print("Bot iniciado!")

while True:
    try:
        response = requests.get(
            url,
            params={"timeout": 30, "offset": offset},
            timeout=35
        )

        data = response.json()

        for update in data.get("result", []):
            offset = update["update_id"] + 1

            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")

            if chat_id:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    data={
                        "chat_id": chat_id,
                        "text": "🤖 Robô do Mercado online!\n\nEm breve vou procurar oportunidades de revenda para você."
                    }
                )

    except Exception as e:
        print("Erro:", e)
        time.sleep(5)
