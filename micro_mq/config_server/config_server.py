from flask import Flask, request, json, jsonify, sys

class ServiceRegistry:
    """
    Обгортка над словником, що містить реєстр сервісів.
    Дозволяє інкапсулювати логіку доступу до конфігурацій.
    """
    _services = {}

    @staticmethod
    def load_from_file(file_path):
        """
        Завантаження сервісів з JSON-файлу.

        Args:
            file_path (str): Шлях до конфігураційного файлу.
        """
        with open(file_path, "r") as config_file:
            ServiceRegistry._services = json.load(config_file)

    @staticmethod
    def get_service(name):
        return ServiceRegistry._services.get(name)

    @staticmethod
    def get_all():
        return ServiceRegistry._services

def create_app():
    """
    Створює та налаштовує Flask-додаток.
    """
    app = Flask(__name__)

    @app.route("/services/<service_name>", methods=["GET"])
    def retrieve_service(service_name):
        """
        Отримати дані про конкретний сервіс за ім'ям.
        """
        service_data = ServiceRegistry.get_service(service_name)
        if service_data:
            return jsonify(service_data)
        return jsonify({"error": "Сервіс не знайдено"}), 404

    @app.route("/services", methods=["GET"])
    def retrieve_all_services():
        """
        Отримати повний список сервісів.
        """
        return jsonify(ServiceRegistry.get_all())

    return app

if __name__ == "__main__":
    # Перевірка аргументу командного рядка
    if len(sys.argv) < 2:
        print("Usage: python config-server.py services.json")
        sys.exit(1)

    # Завантаження сервісів у реєстр
    config_path = sys.argv[1]
    ServiceRegistry.load_from_file(config_path)

    # Створення та запуск Flask-додатку
    app = create_app()
    app.run(host='0.0.0.0', port=8888)
