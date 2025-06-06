from flask import Flask, request, jsonify
import hazelcast, os, logging

app_logger = Flask(__name__)
INSTANCE_NAME = os.getenv("INSTANCE_ID", "default")
LISTEN_PORT = int(os.getenv("PORT", "8881"))

app_logger.logger.setLevel(logging.DEBUG)

# Підключення до Hazelcast-кластера
hazelcast_client = hazelcast.HazelcastClient(
    cluster_members=["hazelcast1:5701", "hazelcast2:5701", "hazelcast3:5701"],
    cluster_name="dev"
)
log_map = hazelcast_client.get_map("logs").blocking()

@app_logger.route("/tracker", methods=["POST", "GET"])
def log_handler():
    """
    Обробник POST і GET запитів:
    - POST: зберігає новий запис у Hazelcast, уникаючи дублікатів
    - GET: повертає всі збережені повідомлення
    """
    if request.method == "POST":
        # Отримання даних з JSON або форми
        if request.is_json:
            data = request.get_json()
            key = data.get("msg")
            value = data.get("msg")
        else:
            key = request.form.get("key")
            value = request.form.get("data")

        # Перевірка валідності
        if not (key and value):
            return jsonify({"error": "Ключ або дані відсутні"}), 400

        # Уникнення дубліката
        if log_map.contains_key(key):
            app_logger.logger.info(f"[{INSTANCE_NAME}] Пропущено (дублікат): {key}")
            return jsonify({"status": "Дублікат"}), 201

        # Збереження нового запису
        log_map.put(key, value)
        app_logger.logger.info(f"[{INSTANCE_NAME}] Збережено: {value} (ключ: {key})")
        return jsonify({"status": "OK"}), 201

    elif request.method == "GET":
        # Повернення всіх значень
        all_logs = log_map.values()
        return jsonify({"messages": list(all_logs)})

if __name__ == "__main__":
    app_logger.logger.info(f"[{INSTANCE_NAME}] Запуск logging-service на порту {LISTEN_PORT}")
    app_logger.run(host="0.0.0.0", port=LISTEN_PORT)
