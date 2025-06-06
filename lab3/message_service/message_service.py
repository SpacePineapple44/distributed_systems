from flask import Flask, request, jsonify

# Ініціалізація Flask-застосунку для службового (заглушкового) сервісу
placeholder_app = Flask(__name__)

@placeholder_app.route("/placeholder", methods=["GET"])
def handle_placeholder_request():
    """
    Обробник GET-запиту для заглушки.
    Повідомляє, що сервіс поки не має функціональності.
    """
    return jsonify({
        "status": "Placeholder active, no features yet"
    })

def run_placeholder_service():
    """
    Запуск Flask-серверу на вказаному хості та порту.
    """
    placeholder_app.run(host='0.0.0.0', port=8882)

if __name__ == "__main__":
    run_placeholder_service()
