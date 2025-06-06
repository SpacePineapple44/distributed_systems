import requests

def transmit_test_messages():
    """
    Надсилає 10 тестових повідомлень до facade-сервісу.
    Кожне повідомлення має формат {"msg": "msgN"}, де N — номер повідомлення.
    Відповіді сервера логуються у консоль.
    """
  
    # URL фасаду, що делегує запити на логування
    facade_endpoint = "http://localhost:8880/entry" 

    # Заголовок для передачі JSON
    request_headers = {"Content-Type": "application/json"}  

    for index in range(1, 11):
        message_payload = {"msg": f"msg{index}"}  # Формуємо повідомлення: {"msg": "msg1"}, ..., {"msg": "msg10"}

        try:
            response = requests.post(
                facade_endpoint,
                json=message_payload,
                headers=request_headers,
                timeout=5  # Обмеження на тривалість запиту
            )

            if response.status_code in (200, 201):
                print(f"[OK] Повідомлення msg{index} успішно надіслано. Відповідь: {response.json()}")
            else:
                print(f"[ERROR] Відмова при надсиланні msg{index}: {response.status_code} - {response.text}")

        except Exception as ex:
            print(f"[EXCEPTION] Збій при спробі надіслати msg{index}: {ex}")

if __name__ == "__main__":
    print("Відправка 10 повідомлень...")
    transmit_test_messages()
    print("Відправка завершена.")
