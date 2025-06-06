from flask import Flask, request, jsonify
import requests, uuid, time, logging, grpc, tracker_pb2, tracker_pb2_grpc

# Створюємо Flask-додаток
my_app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
log_handler = logging.getLogger("Facade-service-gRPC")

# gRPC з'єднання з трекером
grpc_channel = grpc.insecure_channel('localhost:50051')
grpc_tracker = tracker_pb2_grpc.TrackerStub(grpc_channel)

# URL сервісу message
URL_MESSAGE = "http://localhost:4345/message"  # змінив порт із 8882

# Відправка даних до трекера через gRPC з повторними спробами
def try_send_to_grpc_tracker(entry_key, entry_data, attempts_allowed=3, delay_between_tries=1):
    # Формуємо gRPC-запит з ключем і даними
    grpc_payload = tracker_pb2.LogRequest(key=entry_key, data=entry_data)

    # Проводимо кілька спроб відправити запит (за замовчуванням 3 спроби)
    for current_try in range(attempts_allowed):
        try:
            # Викликаємо метод LogEntry через gRPC-клієнт
            grpc_response = grpc_tracker.LogEntry(grpc_payload, timeout=4)

            # Якщо запит вдався — лог і повернення відповіді
            log_handler.info(f"gRPC: {entry_key} успішно передано — статус: {grpc_response.status}")
            return grpc_response

        except grpc.RpcError as err:

            # У разі помилки — попереджувальний лог із деталями
            log_handler.warning(f"Спроба {current_try + 1}/{attempts_allowed} невдала для {entry_key}: {err.details()}")

            # Якщо це не остання спроба — чекаємо перед наступною
            if current_try < attempts_allowed - 1:
                time.sleep(delay_between_tries)
            continue
    
    # Якщо всі спроби вичерпані — повертаємо помилку
    log_handler.error(f"gRPC: Не вдалося передати {entry_key} після {attempts_allowed} спроб")
    return None

# Отримання усіх записів з logger через gRPC
def fetch_all_grpc_entries():
    try:
        # Викликаємо метод GetEntries без аргументів (передаємо порожній запит)
        grpc_response = grpc_tracker.GetEntries(tracker_pb2.Empty(), timeout=4)

        # Повертаємо рядок зі всіма записами, отриманими з logger
        return grpc_response.entries
    
    except grpc.RpcError as err:
        # У разі помилки — повідомляємо про неможливість підключення
        log_handler.error(f"gRPC: неможливо отримати записи: {err.details()}")
        return "Трекер недоступний"


# ------------------- ОСНОВНИЙ МАРШРУТ ДЛЯ /enter -------------------
@my_app.route("/enter", methods=["POST", "GET"])
def handle_entry():

    if request.method == "POST":
        # Отримуємо значення з форми (поле "data")
        user_input = request.form.get("data")

        # Якщо дані не передані — повертаємо помилку
        if not user_input:
            return jsonify({"Помилка": "пусті дані"}), 400

        # Генеруємо унікальний ідентифікатор (ключ) для запису
        generated_key = str(uuid.uuid4())

        # Пробуємо надіслати дані до gRPC-трекера з повторними спробами
        grpc_result = try_send_to_grpc_tracker(generated_key, user_input)

        # Якщо передати дані не вдалося — сервіс недоступний
        if grpc_result is None:
            return jsonify({"помилка": "gRPC-трекер недоступний"}), 503

        # Якщо успішно — повертаємо ключ та дані у відповіді
        return jsonify({"key": generated_key, "data": user_input}), 200

    elif request.method == "GET":
        # Отримуємо дані з обох сервісів
        tracker_resp = fetch_all_grpc_entries()

        # Отримуємо додаткове повідомлення з зовнішнього HTTP-сервісу
        placeholder_resp = requests.get(URL_MESSAGE)

        # Об'єднуємо результати обох джерел в єдину відповідь
        combined_response = f"Logger: {tracker_resp} || Message-service: {placeholder_resp.text}"
        return combined_response, 200

    else:
        # Якщо метод не підтримується — повідомляємо про це
        return jsonify({"Помилка": "некоректний метод"}), 405

# Запуск сервера на іншому порту
if __name__ == "__main__":
    my_app.run(port=4308)
