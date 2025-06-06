from flask import Flask, request, hazelcast, jsonify, os, logging

# Ініціалізація Flask-додатку (сервіс логування подій)
log_service_app = Flask(__name__)

# Отримання унікального ідентифікатора інстансу та порту із змінних середовища
INSTANCE_IDENTIFIER = os.getenv("INSTANCE_ID", "default")
SERVICE_PORT = int(os.getenv("PORT", "8881"))

# Налаштування рівня логування на DEBUG (повна деталізація)
log_service_app.logger.setLevel(logging.DEBUG)

# Ініціалізація клієнта Hazelcast для підключення до кластеру з 3 вузлами
hazelcast_client = hazelcast.HazelcastClient(
    cluster_members=["hazelcast1:5701", "hazelcast2:5701", "hazelcast3:5701"],
    cluster_name="dev"
)

# Отримання блокуючого доступу до розподіленої мапи "logs"
log_entries_map = hazelcast_client.get_map("logs").blocking()

# Основна точка входу для обробки POST та GET запитів на ендпоінт /tracker
@log_service_app.route("/tracker", methods=["POST", "GET"])
def process_log_requests():
    # Обробка POST-запиту — запис повідомлення в Hazelcast (із перевіркою на дублікати)
    if request.method == "POST":
        # Витягуємо дані з JSON або з форми (fallback)
        if request.is_json:
            payload_data = request.get_json()
            log_key = payload_data.get("msg")
            log_value = payload_data.get("msg")
        else:
            log_key = request.form.get("key")
            log_value = request.form.get("data")

        # Перевірка на наявність обов’язкових параметрів
        if not (log_key and log_value):
            return jsonify({"error": "Missing key or data"}), 400

        # Уникнення дублювання: якщо ключ вже існує, не записуємо ще раз
        if log_entries_map.contains_key(log_key):
            log_service_app.logger.info(f"[{INSTANCE_IDENTIFIER}] Duplicate ignored: {log_key}")
            return jsonify({"status": "Duplicate"}), 201

        # Запис у розподілену мапу
        log_entries_map.put(log_key, log_value)
        log_service_app.logger.info(f"[{INSTANCE_IDENTIFIER}] Logged: {log_value} (Key: {log_key})")
        return jsonify({"status": "OK"}), 201

    # Обробка GET-запиту — повертає всі наявні значення в мапі
    elif request.method == "GET":
        stored_messages = log_entries_map.values()
        return jsonify({"messages": list(stored_messages)})

# Точка запуску сервісу
if __name__ == "__main__":
    log_service_app.logger.info(f"[{INSTANCE_IDENTIFIER}] Launching log service on port {SERVICE_PORT}")
    log_service_app.run(host='0.0.0.0', port=SERVICE_PORT)
