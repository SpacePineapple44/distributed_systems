from flask import Flask, request, json, jsonify, sys

# Ініціалізація Flask-додатку
app = Flask(__name__)

# Словник для зберігання інформації про сервіси
service_registry = {}

# ----------- Маршрут для отримання конкретного сервісу -----------

@app.route("/services/<service_name>", methods=["GET"])
def get_service(service_name):
    """
    Повертає інформацію про конкретний сервіс за його ім'ям.
    Якщо сервіс не знайдено — повертає помилку 404.
    """
    if service_name in service_registry:
        return jsonify(service_registry[service_name])
    return jsonify({"error": "Service not found"}), 404

# ----------- Маршрут для отримання всіх зареєстрованих сервісів -----------

@app.route("/services", methods=["GET"])
def list_services():
    """
    Повертає повний список усіх зареєстрованих сервісів.
    """
    return jsonify(service_registry)

# ----------- Точка входу в застосунок -----------

if __name__ == "__main__":
    # Перевірка наявності шляху до конфігураційного JSON
    if len(sys.argv) < 2:
        print("Usage: python config-server.py <path_to_services.json>")
        sys.exit(1)

    config_file_path = sys.argv[1]

    # Завантаження конфігурацій сервісів із JSON-файлу
    try:
        with open(config_file_path, "r") as json_file:
            service_registry = json.load(json_file)
            print(f"Service registry loaded from: {config_file_path}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Запуск Flask-сервера на всіх інтерфейсах, порт 8888
    app.run(host="0.0.0.0", port=4308)
