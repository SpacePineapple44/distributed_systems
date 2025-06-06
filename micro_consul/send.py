import requests

# Функція для відправки тестових повідомлень на сервіс facade
def push_test_payloads_to_facade():
    endpoint_url = "http://localhost:8880/entry"  # URL фасаду
    request_headers = {"Content-Type": "application/json"}  # Заголовки HTTP-запиту

    # Цикл надсилання 10 повідомлень
    for counter in range(1, 11):
        message_body = {"msg": f"msg{counter}"}  # Формуємо JSON-повідомлення

        try:
            response = requests.post(
                endpoint_url,
                json=message_body,
                headers=request_headers,
                timeout=5
            )

            # Успішна відповідь від сервера
            if response.status_code in (200, 201):
                print(f"Повідомлення msg{counter} відправлено: {response.json()}")
            else:
                # Некоректна відповідь (наприклад, 400, 500 тощо)
                print(f"Помилка при відправці msg{counter}: {response.status_code} - {response.text}")
        
        except Exception as error:
            # Випадок мережевої помилки, таймауту тощо
            print(f"Виняток при відправці msg{counter}: {error}")

# Точка входу
if __name__ == "__main__":
    print("Відправка 10 повідомлень...")
    push_test_payloads_to_facade()
    print("Відправка завершена.")
