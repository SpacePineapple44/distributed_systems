import os, time, json, random, requests, atexit, 

from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Ініціалізація Flask застосунку
service_app = Flask(__name__)

# Конфігураційні змінні
CONSUL_ADDRESS = os.getenv("CONSUL_HOST", "consul")
CONSUL_API_PORT = int(os.getenv("CONSUL_PORT", "8500"))
SERVICE_INSTANCE_ID = os.getenv("INSTANCE_ID", "facade1")
SERVICE_PORT = 8880

# Підключення до Consul
kv_client = consul.Consul(host=CONSUL_ADDRESS, port=CONSUL_API_PORT)

# Реєстрація сервісу у Consul
def register_facade_instance():
    kv_client.agent.service.register(
        service_id=SERVICE_INSTANCE_ID,
        name="facade-service",
        address="facade-service",
        port=SERVICE_PORT,
        check=consul.Check.http(
            f"http://facade-service:{SERVICE_PORT}/health",
            interval="10s",
            timeout="5s"
        )
    )
    print(f"[Facade] Інстанс {SERVICE_INSTANCE_ID} зареєстрований у Consul")

# Видалення сервісу з реєстру Consul при завершенні
def deregister_facade_instance():
    kv_client.agent.service.deregister(SERVICE_INSTANCE_ID)
    print("[Facade] Інстанс видалено з Consul")

# Простий health-check
@service_app.route("/health", methods=["GET"])
def check_health():
    return jsonify({"status": "healthy"}), 200

# Отримання конфігурації Kafka з Consul
def fetch_kafka_settings_from_consul():
    for attempt in range(10):
        try:
            _, broker_raw = kv_client.kv.get("config/kafka/brokers")
            if broker_raw is None:
                raise ValueError("Немає ключа config/kafka/brokers")

            kafka_brokers = json.loads(broker_raw["Value"].decode("utf-8"))

            _, topic_raw = kv_client.kv.get("config/kafka/topic")
            if topic_raw is None:
                raise ValueError("Немає ключа config/kafka/topic")

            kafka_topic = json.loads(topic_raw["Value"].decode("utf-8"))
            return kafka_brokers, kafka_topic
        except Exception as e:
            print(f"[Facade] Неможливо отримати Kafka-конфіг: {e}")
            time.sleep(5)

    raise Exception("[Facade] Не вдалося зчитати Kafka-конфігурацію після 10 спроб")

# Ініціалізація Kafka
KAFKA_SERVERS, KAFKA_TOPIC_NAME = fetch_kafka_settings_from_consul()

for attempt in range(10):
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("[Facade] Підключено до Kafka брокерів", flush=True)
        break
    except NoBrokersAvailable:
        print(f"[Facade] Kafka недоступна (спроба {attempt+1}/10), повтор через 5с...", flush=True)
        time.sleep(5)
else:
    raise Exception("[Facade] Підключення до Kafka не вдалося після 10 спроб")

# Визначення URL усіх інстансів сервісу
def discover_service_instances(service_name):
    try:
        _, entries = kv_client.catalog.service(service_name)
        return [f"http://{s['ServiceAddress']}:{s['ServicePort']}" for s in entries if s["ServiceID"]]
    except Exception as e:
        print(f"[Facade] Не вдалося знайти сервіс {service_name}: {e}")
        return []

# Запит до випадкової інстанції сервісу
def request_random_instance(service_name, endpoint, method="GET", payload=None):
    available_urls = discover_service_instances(service_name)
    random.shuffle(available_urls)

    for base_url in available_urls:
        try:
            url = f"{base_url}{endpoint}"
            if method == "POST":
                response = requests.post(url, json=payload, timeout=3)
            else:
                response = requests.get(url, timeout=3)

            if response.status_code in (200, 201):
                return response.json()
        except Exception as error:
            print(f"[Facade] Помилка доступу до {base_url}: {error}")

    return {"error": "Сервіс недоступний"}, 500

# Обробка POST-запиту /entry — надсилання повідомлення до Kafka і логів
@service_app.route("/entry", methods=["POST"])
def handle_message_entry():
    message = request.json.get("msg")
    if message:
        kafka_producer.send(KAFKA_TOPIC_NAME, {"msg": message})
        print(f"[Facade] Повідомлення відправлено до Kafka: {message}")

        log_result = request_random_instance(
            service_name="logging-service",
            endpoint="/tracker",
            method="POST",
            payload={"msg": message}
        )

        if "error" in log_result:
            print(f"[Facade] Не вдалося записати лог: {log_result['error']}")
            return jsonify({"error": "Не вдалося зберегти log"}), 500

        print(f"[Facade] Лог успішно збережено: {log_result}")
        return jsonify({"status": "Відправлено до Kafka і logging-service"}), 201

    print("[Facade] Помилка: порожній msg у запиті")
    return jsonify({"error": "Відсутній msg"}), 400

# Отримання логів з logging-service
@service_app.route("/entry", methods=["GET"])
def retrieve_logs():
    return request_random_instance("logging-service", "/tracker", method="GET")

# Отримання повідомлень з messages-service
@service_app.route("/notify", methods=["GET"])
def notify_user():
    return request_random_instance("messages-service", "/messages", method="GET")

# Об’єднання повідомлень з двох сервісів
@service_app.route("/combined", methods=["GET"])
def get_all_messages():
    logs_data = request_random_instance("logging-service", "/tracker", method="GET")
    logs = logs_data.get("messages", []) if "error" not in logs_data else []

    messages_data = request_random_instance("messages-service", "/messages", method="GET")
    other_messages = messages_data.get("messages", []) if "error" not in messages_data else []

    combined_unique = list(set(logs + other_messages))
    return jsonify({"messages": combined_unique})

# Запуск сервісу
if __name__ == "__main__":
    register_facade_instance()
    atexit.register(deregister_facade_instance)
    service_app.run(host="0.0.0.0", port=SERVICE_PORT)
