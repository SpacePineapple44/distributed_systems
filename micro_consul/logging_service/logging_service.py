import atexit, time, os, logging, json
from flask import Flask, request, jsonify
import hazelcast, consul

app = Flask(__name__)

# Отримання конфігурації середовища
SERVICE_ID = os.getenv("INSTANCE_ID", "default_logger")
SERVICE_PORT = int(os.getenv("PORT", "8881"))
CONSUL_ADDRESS = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

# Встановлюємо рівень логування Flask додатку
app.logger.setLevel(logging.DEBUG)

# Ініціалізація клієнта Consul
consul_client = consul.Consul(host=CONSUL_ADDRESS, port=CONSUL_PORT)


def register_with_consul():
    """
    Реєстрація сервісу в Consul з HTTP чекером здоров'я.
    Ім'я адреси та endpoint з урахуванням останнього символу SERVICE_ID.
    """
    service_address = f"logging-service{SERVICE_ID[-1]}"
    consul_client.agent.service.register(
        service_id=SERVICE_ID,
        name="logging-service",
        address=service_address,
        port=SERVICE_PORT,
        check=consul.Check.http(
            url=f"http://{service_address}:{SERVICE_PORT}/health",
            interval="10s",
            timeout="5s"
        )
    )
    print(f"[{SERVICE_ID}] Зареєстровано в Consul як {SERVICE_ID}")


def deregister_from_consul():
    """Видалення сервісу з Consul при завершенні роботи."""
    consul_client.agent.service.deregister(SERVICE_ID)
    print(f"[{SERVICE_ID}] Видалено з Consul")


@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint для перевірки стану сервісу."""
    return jsonify({"status": "healthy"}), 200


def fetch_hazelcast_settings():
    """
    Отримання конфігурації Hazelcast (кластерні ноди та ім'я кластера) з Consul.
    Проводить 10 спроб із затримкою 5 секунд при невдачі.
    """
    for attempt in range(10):
        try:
            _, members_kv = consul_client.kv.get("config/hazelcast/cluster_members")
            app.logger.debug(f"[{SERVICE_ID}] Спроба {attempt + 1}: members_kv = {members_kv}")
            if members_kv is None:
                raise ValueError("Ключ config/hazelcast/cluster_members відсутній у Consul")

            cluster_members = json.loads(members_kv["Value"].decode("utf-8"))

            _, cluster_name_kv = consul_client.kv.get("config/hazelcast/cluster_name")
            app.logger.debug(f"[{SERVICE_ID}] Спроба {attempt + 1}: cluster_name_kv = {cluster_name_kv}")
            if cluster_name_kv is None:
                raise ValueError("Ключ config/hazelcast/cluster_name відсутній у Consul")

            cluster_name = json.loads(cluster_name_kv["Value"].decode("utf-8"))

            app.logger.info(f"[{SERVICE_ID}] Отримано конфіг Hazelcast: members={cluster_members}, cluster_name={cluster_name}")
            return cluster_members, cluster_name
        except Exception as ex:
            app.logger.warning(f"[{SERVICE_ID}] Спроба {attempt + 1} не вдалася: {ex}")
            time.sleep(5)

    raise Exception(f"[{SERVICE_ID}] Не вдалося отримати конфігурацію Hazelcast після 10 спроб")


# Отримуємо параметри Hazelcast та ініціалізуємо клієнта
HZ_CLUSTER_MEMBERS, HZ_CLUSTER_NAME = fetch_hazelcast_settings()
hz_client = hazelcast.HazelcastClient(
    cluster_members=HZ_CLUSTER_MEMBERS,
    cluster_name=HZ_CLUSTER_NAME
)

# Отримуємо блокуючу мапу для зберігання логів
log_map = hz_client.get_map("logs").blocking()


@app.route("/tracker", methods=["POST", "GET"])
def logs_handler():
    """
    Обробник запитів на додавання та отримання логів.
    POST - додає повідомлення, GET - повертає всі збережені повідомлення.
    """
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            message_key = data.get("msg")
            message_value = data.get("msg")
        else:
            message_key = request.form.get("key")
            message_value = request.form.get("data")

        if not message_key or not message_value:
            return jsonify({"error": "Відсутній ключ або дані"}), 400

        if log_map.contains_key(message_key):
            app.logger.info(f"[{SERVICE_ID}] Пропущено дублікат: {message_key}")
            return jsonify({"status": "Дублікат"}), 201

        log_map.put(message_key, message_value)
        app.logger.info(f"[{SERVICE_ID}] Збережено повідомлення: {message_value} [Key: {message_key}]")
        return jsonify({"status": "OK"}), 201

    elif request.method == "GET":
        all_logs = list(log_map.values())
        return jsonify({"messages": all_logs})


if __name__ == "__main__":
    # Затримка перед стартом, щоб бути впевненим у доступності інших сервісів
    time.sleep(20)

    # Реєстрація сервісу та налаштування його відключення
    register_with_consul()
    atexit.register(deregister_from_consul)

    app.logger.info(f"[{SERVICE_ID}] Запуск logging-service на порту {SERVICE_PORT}")
    app.run(host='0.0.0.0', port=SERVICE_PORT)
