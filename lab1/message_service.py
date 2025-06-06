from flask import Flask, request, jsonify

# Ініціалізація Flask-додатку
message = Flask(__name__)

# ------------------- МАРШРУТ ДЛЯ MESAGE-SERVICE -------------------
@message.route("/message", methods=["GET"])
def respond():
    # Обробляємо лише GET-запити
    if request.method == "GET":
        return "Відсутній реалізований функціонал"
    else:
        # У разі іншого методу — повертаємо помилку
        return jsonify({"Помилка": "Дозволений тільки метод GET!"}), 405

# ------------------- ЗАПУСК СЕРВЕРА -------------------
if __name__ == "__main__":
    message.run(port=4345)
