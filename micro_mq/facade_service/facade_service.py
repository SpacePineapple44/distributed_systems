import random, requests, json, time
from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

app = Flask(__name__)

# Константи з конфігурацією
CONFIG_URL = "http://config-server:8888"
TOPIC_NAME = "messages"
BROKER_LIST = ["kafka1:9092", "kafka2:9093", "kafka3:9094"]

# Kafka продюсер (буде ініціалізований під час старту)
kafka_producer = None

def initialize_kafka_producer():
    """
    Спроба створити Kafka-продюсер з повторними підключеннями у разі помилок.
    """
    for attempt in range(10):
        try:
            producer_instance = KafkaProducer(
                bootstrap_servers=BROKER_LIST,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("[Facade] Підключення до Kafka успішне", flush=True)
            return producer_instance
        except NoBrokersAvailable:
            print(f"[Facade] Kafka недоступна (спроба {attempt + 1}/10), очікування 5 с...", flush=True)
            time.sleep(5)
    raise Exception("[Facade] Не вдалося підключитися до Kafka після кількох спроб")

def discover_service_endpoints(service_name):
    """
    Отримати список URL-адрес для вказаного сервісу з config-сервера.
    """
    try:
        response = requests.get(f"{CONFIG_URL}/services/{service_name}", timeout=2)
        return response.json() if response.status_code == 200 else []
    except Exception as err:
        print(f"[Facade] Помилка при зверненні до config-сервера: {err}")
        return []

def forward_request_to_service(service_name, endpoint_path, method="GET", payload=None):
    """
    Надіслати запит до випадкового інстансу сервісу.

    Returns:
        dict|tuple: Відповідь від інстансу або повідомлення про помилку.
    """
    instance_urls = discover_service_endpoints(service_name)
    random.shuffle(instance_urls)

    for base_url in instance_urls:
        try:
            full_url = f"{base_url}{endpoint_path}"
            if method == "POST":
                response = requests.post(full_url, json=payload, timeout=3)
            else:
                response = requests.get(full_url, timeout=3)

            if response.status_code in (200, 201):
                return response.json()
        except Exception as err:
            print(f"[Facade] Помилка при запиті до {full_url}: {err}")

    return {"error": "Всі спроби звернення до сервісу неуспішні"}, 500

@app.route("/entry", methods=["POST"])
def handle_message_post():
    """
    Обробка POST-запиту: відправка повідомлення до Kafka та лог-сервісу.
    """
    message_text = request.json.get("msg")
    if message_text:
        kafka_producer.send(TOPIC_NAME, {"msg": message_text})
        print(f"[Facade] Повідомлення надіслано до Kafka: {message_text}")

        log_response = forward_request_to_service("logging-service", "/tracker", method="POST", payload={"msg": message_text})
        if "error" in log_response:
            print(f"[Facade] Не вдалося надіслати до logging-service: {log_response['error']}")
            return jsonify({"error": "Збереження в logging-service не вдалося"}), 500

        return jsonify({"status": "Успішно надіслано"}), 201

    return jsonify({"error": "Не вказано поле 'msg'"}), 400

@app.route("/entry", methods=["GET"])
def handle_log_retrieval():
    """
    Отримати лог-повідомлення з logging-service.
    """
    return forward_request_to_service("logging-service", "/tracker", method="GET")

@app.route("/notify", methods=["GET"])
def handle_notifications():
    """
    Отримати повідомлення з messages-service.
    """
    return forward_request_to_service("messages-service", "/messages", method="GET")

@app.route("/combined", methods=["GET"])
def handle_combined_retrieval():
    """
    Об'єднати повідомлення з logging-service та messages-service.
    """
    logs = forward_request_to_service("logging-service", "/tracker", method="GET")
    messages = forward_request_to_service("messages-service", "/messages", method="GET")

    logs_list = logs.get("messages", []) if "error" not in logs else []
    service_msgs = messages.get("messages", []) if "error" not in messages else []

    merged = list(set(logs_list + service_msgs))
    return jsonify({"messages": merged})

if __name__ == "__main__":
    # Ініціалізація Kafka-продюсера перед стартом Flask-додатку
    kafka_producer = initialize_kafka_producer()
    app.run(host='0.0.0.0', port=8880)
