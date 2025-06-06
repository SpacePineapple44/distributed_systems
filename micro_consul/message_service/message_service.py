from flask import Flask, jsonify
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import json, threading, consul, os, atexit, time

web_app = Flask(__name__)

# Змінні середовища для налаштування сервісу
SERVICE_INSTANCE_ID = os.getenv("INSTANCE_ID", "default")
SERVICE_PORT = int(os.getenv("PORT", "8890"))
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

# Список для збереження отриманих повідомлень з Kafka
received_messages = []

# Ініціалізація клієнта Consul
consul_agent = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register_service_in_consul():
    """
    Реєстрація сервісу у Consul із HTTP перевіркою стану.
    Адреса формується з урахуванням останнього символу SERVICE_INSTANCE_ID.
    """
    service_address = f"messages-service{SERVICE_INSTANCE_ID[-1]}"
    consul_agent.agent.service.register(
        service_id=SERVICE_INSTANCE_ID,
        name="messages-service",
        address=service_address,
        port=SERVICE_PORT,
        check=consul.Check.http(
            url=f"http://{service_address}:{SERVICE_PORT}/health",
            interval="10s",
            timeout="5s"
        )
    )
    print(f"[{SERVICE_INSTANCE_ID}] Зареєстровано в Consul як {SERVICE_INSTANCE_ID}")


def deregister_service_from_consul():
    """Видалення сервісу з Consul при завершенні роботи програми."""
    consul_agent.agent.service.deregister(SERVICE_INSTANCE_ID)
    print(f"[{SERVICE_INSTANCE_ID}] Видалено з Consul")


@web_app.route("/health", methods=["GET"])
def health_check_endpoint():
    """Endpoint для перевірки статусу сервісу."""
    return jsonify({"status": "healthy"}), 200


def retrieve_kafka_configuration():
    """
    Отримання конфігурації Kafka (списки брокерів та топік) з Consul.
    Здійснюється 10 спроб з паузою в 5 секунд між ними.
    """
    for attempt in range(10):
        try:
            _, brokers_kv = consul_agent.kv.get("config/kafka/brokers")
            print(f"[{SERVICE_INSTANCE_ID}] Attempt {attempt + 1}: brokers_kv = {brokers_kv}")
            if brokers_kv is None:
                raise ValueError("Ключ config/kafka/brokers відсутній у Consul")

            brokers_list = json.loads(brokers_kv["Value"].decode("utf-8"))

            _, topic_kv = consul_agent.kv.get("config/kafka/topic")
            if topic_kv is None:
                raise ValueError("Ключ config/kafka/topic відсутній у Consul")

            topic_name = json.loads(topic_kv["Value"].decode("utf-8"))

            print(f"[{SERVICE_INSTANCE_ID}] Successfully retrieved Kafka config: brokers={brokers_list}, topic={topic_name}")
            return brokers_list, topic_name

        except Exception as err:
            print(f"[{SERVICE_INSTANCE_ID}] Attempt {attempt + 1} failed: {err}")
            time.sleep(5)

    raise Exception(f"[{SERVICE_INSTANCE_ID}] Не вдалося отримати конфігурацію Kafka після 10 спроб")


def kafka_consumer_loop():
    """
    Функція для підключення до Kafka та отримання повідомлень.
    Проводить 10 спроб підключення з інтервалом 5 секунд.
    Після успішного підключення починає нескінченний цикл прослуховування топіку.
    """
    kafka_brokers, kafka_topic = retrieve_kafka_configuration()

    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                kafka_topic,
                bootstrap_servers=kafka_brokers,
                auto_offset_reset="earliest",
                group_id="group-messages",
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            print(f"[{SERVICE_INSTANCE_ID}] Підключено до Kafka", flush=True)
            break
        except NoBrokersAvailable:
            print(f"[{SERVICE_INSTANCE_ID}] Kafka недоступна (спроба {attempt + 1}/10), повтор через 5с...", flush=True)
            time.sleep(5)
    else:
        raise Exception(f"[{SERVICE_INSTANCE_ID}] Kafka недоступна після кількох спроб")

    print(f"[{SERVICE_INSTANCE_ID}] Запуск циклу споживача Kafka", flush=True)
    for message in consumer:
        msg_content = message.value.get("msg")
        if msg_content:
            received_messages.append(msg_content)
            print(f"[{SERVICE_INSTANCE_ID}] Отримано з Kafka: {msg_content}", flush=True)


@web_app.route("/messages", methods=["GET"])
def serve_messages():
    """Endpoint для отримання всіх отриманих повідомлень з Kafka."""
    return jsonify({"messages": received_messages})


if __name__ == "__main__":
    # Очікування на готовність залежних сервісів
    time.sleep(20)

    # Реєстрація сервісу у Consul та налаштування deregister при завершенні
    register_service_in_consul()
    atexit.register(deregister_service_from_consul)

    print(f"[{SERVICE_INSTANCE_ID}] Запуск на порті {SERVICE_PORT}")

    # Запуск Kafka споживача у фоновому потоці
    threading.Thread(target=kafka_consumer_loop, daemon=True).start()

    # Запуск Flask веб-сервісу
    web_app.run(host='0.0.0.0', port=SERVICE_PORT)
