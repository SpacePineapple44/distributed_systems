from flask import Flask, request, jsonify
import requests, time, uuid, logging

# Посилання на інші сервіси (трекер і плейсхолдер)
URL_LOGGING = "http://localhost:4344/logger"
URL_MESSAGE = "http://localhost:4345/message"

# створення об'єкта Flask-додатку
my_app = Flask(__name__)

# Налаштовуємо базове логування
logging.basicConfig(level=logging.INFO)
log_handler = logging.getLogger("Facade-service")

# Функція для відправки даних з повторними спробами
def try_send_to_tracker(data_packet, attempts_allowed=3, delay_between_tries=1):
    # проходимо цикл із максимальною кількістю дозволених спроб
    for current_try in range(attempts_allowed):
        try:
            # Надсилаємо POST-запит до трекера
            response = requests.post(URL_LOGGING, data=data_packet, timeout=4)

            # якщо сервер повертає 201 (Created) — вважаємо, що все ок
            if response.status_code == 201:
                log_handler.info(f"Пакет {data_packet['key']} успішно відправлений")
                return response
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as ex:
            # якщо підключення або таймаут — фіксуємо це в логах
            log_handler.warning(f"Спроба {current_try + 1}/{attempts_allowed} невдала для {data_packet['key']}: {ex}")
            
            # перевірка: чи ще залишились спроби
            if current_try < attempts_allowed - 1:
                # чекаємо перед наступною спробою
                time.sleep(delay_between_tries)  
            continue

    # якщо ми тут — значить всі спроби закінчились невдачею
    log_handler.error(f"Не вдалося відправити {data_packet['key']} після {attempts_allowed} спроб")
    return None


# Основний маршрут для прийому та обробки запитів
@my_app.route("/enter", methods=["POST", "GET"])

def handle_entry():
    if request.method == "POST":

        # отримуємо дані з форми
        user_input = request.form.get("data")

        if not user_input:
            return jsonify({"Помилка": "пусті дані"}), 400

        # генеруємо унікальний ключ
        generated_key = str(uuid.uuid4())
        prepared_payload = {"key": generated_key, 
                            "data": user_input}

        # Надсилаємо з повторними спробами (на випадок якщо трекер мертвий)
        tracker_result = try_send_to_tracker(prepared_payload)

        if tracker_result is None:
            return jsonify({"помилка": "Logger недоступний"}), 503

        # повертаємо клієнту ключ і його ж дані
        return jsonify({"key": generated_key, "data": user_input}), 200

    elif request.method == "GET":
        # тянемо дані з logger та message
        tracker_resp = requests.get(URL_LOGGING)
        placeholder_resp = requests.get(URL_MESSAGE)

        # склеюємо відповіді і повертаємо
        combined_response = f"Logger: {tracker_resp.text} || Message-service: {placeholder_resp.text}"
        return combined_response, 200

    else:
        # якщо якийсь інший метод — помилка
        return jsonify({"Помилка": "некоректний метод"}), 405

# Запускаємо сервер
if __name__ == "__main__":
    my_app.run(port=4308)
