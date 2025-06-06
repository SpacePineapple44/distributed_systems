from flask import Flask, request, jsonify

# Ініціалізуємо Flask-додаток
log_collector = Flask(__name__)

# Внутрішній "сховище" для збереження отриманих записів
collected_entries = {}

# ------------------- ГОЛОВНИЙ МАРШРУТ -------------------
@log_collector.route("/logger", methods=["POST", "GET"])
def track_request():
    # Якщо надійшов POST-запит (тобто додавання нових даних)
    if request.method == "POST":
        # Отримуємо ключ (ідентифікатор) та дані з POST-форми
        entry_key = request.form.get("key")
        entry_value = request.form.get("data")

        # Перевіряємо, що обидва поля заповнені
        if not (entry_key and entry_value):
            return jsonify({"error": "Missing key or data"}), 400

        # Перевірка на дублікати — якщо такий ключ вже є, не додаємо ще раз
        if entry_key in collected_entries:
            print(f"Repeated entry skipped: {entry_key}")  # просто друк для себе
            return jsonify({"status": "Skipped repeat"}), 201  # але повертаємо 201 (Created) для узгодженості

        # Якщо все нове — зберігаємо в словник
        collected_entries[entry_key] = entry_value
        print(f"Tracked: {entry_value} [Key: {entry_key}]")  # друк записаного значення
        return jsonify({"status": "Entry recorded"}), 201

    # Якщо надійшов GET-запит — повертаємо всі значення (без ключів)
    elif request.method == "GET":
        # об'єднуємо всі збережені значення через кому
        return ", ".join(collected_entries.values())

    # Якщо метод не підтримується — повертаємо відповідь з помилкою
    else:
        return jsonify({"error": "Method unsupported"}), 405

# ------------------- ЗАПУСК СЕРВЕРА -------------------
if __name__ == "__main__":
    log_collector.run(port=4344)
