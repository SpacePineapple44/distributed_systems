import random
import requests
from flask import Flask, request, jsonify

# Ініціалізація веб-серверу Flask
gateway_app = Flask(__name__)

# Адреса сервера конфігурації
SERVICE_REGISTRY_URL = "http://config-server:8888"

# ----------- Отримання доступних адрес сервісу -----------

def fetch_service_instances(service_key):
    """
    Отримує список URL-адрес для заданого сервісу з конфіг-сервера.
    """
    try:
        res = requests.get(f"{SERVICE_REGISTRY_URL}/services/{service_key}", timeout=2)
        return res.json() if res.status_code == 200 else []
    except Exception as err:
        print(f"[Gateway] Registry fetch failed: {err}")
        return []

# ----------- Відправка запиту на один із доступних екземплярів -----------

def delegate_request(service_key, endpoint_path, http_method="GET", payload=None):
    """
    Випадковим чином обирає один із екземплярів сервісу та надсилає запит.
    """
    service_urls = fetch_service_instances(service_key)
    random.shuffle(service_urls)  # Перемішуємо список для балансування

    for base in service_urls:
        try:
            full_endpoint = f"{base}{endpoint_path}"
            if http_method == "POST":
                resp = requests.post(full_endpoint, json=payload, timeout=3)
            else:
                resp = requests.get(full_endpoint, timeout=3)

            if resp.status_code in (200, 201):
                print(f"[Gateway] Response from {service_key}: {resp.json()}")
                content_type = resp.headers.get("Content-Type", "")
                return resp.json() if "application/json" in content_type else resp.text
        except Exception as err:
            print(f"[Gateway] Failed to reach {full_endpoint}: {err}")

    return {"error": "No reachable instances"}, 500

# ----------- Обробка запитів на /entry -----------

@gateway_app.route("/entry", methods=["GET", "POST"])
def process_log_entry():
    """
    GET — отримує дані з лог-сервісу
    POST — передає повідомлення в лог-сервіс
    """
    if request.method == "POST":
        message = request.json.get("msg")
        return delegate_request(
            service_key="logging-service",
            endpoint_path="/tracker",
            http_method="POST",
            payload={"msg": message}
        )
    else:
        return delegate_request(
            service_key="logging-service",
            endpoint_path="/tracker",
            http_method="GET"
        )

# ----------- Обробка запитів на /notify -----------

@gateway_app.route("/notify", methods=["GET"])
def handle_notification():
    """
    GET — отримує відповідь від сервісу повідомлень
    """
    return delegate_request(
        service_key="messages-service",
        endpoint_path="/placeholder",
        http_method="GET"
    )

# ----------- Точка запуску програми -----------

if __name__ == "__main__":
    # Запуск API-шлюзу на порту 4344
    gateway_app.run(host="0.0.0.0", port=8880)
