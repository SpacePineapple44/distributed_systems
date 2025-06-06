import requests

# Конфігурація клієнта
FACADE_ENDPOINT = "http://localhost:8880/entry"
HEADERS = {"Content-Type": "application/json"}
TOTAL_MESSAGES = 10

def send_test_payloads():
    """
    Надсилає серію тестових повідомлень до фасад-сервісу.
    """
    for idx in range(1, TOTAL_MESSAGES + 1):
        message_body = {"msg": f"msg{idx}"}

        try:
            response = requests.post(
                FACADE_ENDPOINT,
                json=message_body,
                headers=HEADERS,
                timeout=5
            )

            if response.status_code in (200, 201):
                print(f"Повідомлення msg{idx} відправлено: {response.json()}")
            else:
                print(f"Помилка при відправці msg{idx}: {response.status_code} — {response.text}")

        except Exception as error:
            print(f"Виняток при відправці msg{idx}: {error}")

def start_facade_client():
    """
    Точка запуску клієнта для надсилання повідомлень.
    """
    print("Відправка 10 повідомлень...")
    send_test_payloads()
    print("Відправка завершена.")

if __name__ == "__main__":
    start_facade_client()
