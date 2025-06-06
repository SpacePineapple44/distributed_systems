from flask import Flask, jsonify
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import json, threading, os, time

# Ініціалізація Flask-додатку
kafka_app = Flask(__name__)

# Зчитування змінних середовища
INSTANCE_NAME = os.getenv("INSTANCE_ID", "default")
APP_PORT = int(os.getenv("PORT", "8890"))

# Локальний список для збереження отриманих повідомлень
received_messages = []

# Список Kafka-брокерів
KAFKA_BROKERS = ["kafka1:9092", "kafka2:9093", "kafka3:9094"]
KAFKA_TOPIC = "messages"
KAFKA_CONSUMER_GROUP = "group-messages"

def init_kafka_consumer():
    """
    Підключення до Kafka-брокера з кількома спробами.
    Повертає об'єкт KafkaConsumer у випадку успішного підключення.
    """
    for attempt in range(10):
        try:
            consumer_instance = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BROKERS,
                auto_offset_reset="earliest",
                group_id=KAFKA_CONSUMER_GROUP,
                value_deserializer=lambda m: json.loads(m.decode("utf-8"))
            )
            print(f"[{INSTANCE_NAME}] Успішне підключення до Kafka", flush=True)
            return consumer_instance
        except NoBrokersAvailable:
            print(f"[{INSTANCE_NAME}] Kafka недоступна (спроба {attempt+1}/10), чекаємо 5 секунд...", flush=True)
            time.sleep(5)
    
    # Виняток, якщо після 10 спроб Kafka все ще недоступна
    raise Exception(f"[{INSTANCE_NAME}] Не вдалося підключитися до Kafka")

def kafka_listener_loop(consumer):
    """
    Основний цикл прослуховування Kafka-повідомлень.
    Отримані повідомлення додаються до списку received_messages.
    """
    print(f"[{INSTANCE_NAME}] Старт прослуховування Kafka", flush=True)
    for msg in consumer:
        payload = msg.value.get("msg")
        if payload:
            received_messages.append(payload)
            print(f"[{INSTANCE_NAME}] Отримано повідомлення з Kafka: {payload}", flush=True)

@kafka_app.route("/messages", methods=["GET"])
def fetch_messages():
    """
    HTTP-ендпоінт для отримання всіх Kafka-повідомлень.
    """
    return jsonify({"messages": received_messages})

def start_kafka_background_consumer():
    """
    Запускає Kafka-споживача в окремому потоці.
    """
    consumer = init_kafka_consumer()
    thread = threading.Thread(target=kafka_listener_loop, args=(consumer,), daemon=True)
    thread.start()

if __name__ == "__main__":
    print(f"[{INSTANCE_NAME}] Запуск сервісу на порту {APP_PORT}", flush=True)
    start_kafka_background_consumer()
    kafka_app.run(host="0.0.0.0", port=APP_PORT)
