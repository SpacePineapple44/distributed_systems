import hazelcast, threading, time  # Імпортуємо необхідні модулі: Hazelcast-клієнт, багатопоточність та таймер

# Функція, яка виконує інкремент значення у розподіленій мапі без будь-якої синхронізації
def naive_increment(shared_map, operations_count):
    for _ in range(operations_count):
        # Отримуємо поточне значення або 0, якщо ключ ще не існує
        current_val = shared_map.get("counter") or 0

        # Збільшуємо значення на одиницю
        shared_map.put("counter", current_val + 1)

# Ініціалізація клієнта Hazelcast і підключення до кластеру
hz_client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",
    cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
)

# Отримання розподіленої мапи з іменем "naive_map"
naive_counter_map = hz_client.get_map("naive_map").blocking()

# Ініціалізація значення ключа
naive_counter_map.put("counter", 0)

# Налаштування: скільки разів кожен потік інкрементує значення
incr_per_thread = 10_000

# Кількість потоків, які будуть одночасно працювати
number_of_threads = 3

# Очікуване підсумкове значення після завершення всіх потоків
expected_total = incr_per_thread * number_of_threads

# Роздільник у виводі
print("\n---------------->>>")

# Фіксація початкового часу виконання
start = time.time()

# Створення списку для збереження потоків
worker_threads = []

# Створення та запуск потоків
for t_id in range(number_of_threads):
    # Створюємо потік для запуску naive_increment
    thread = threading.Thread(
        target=naive_increment,
        args=(naive_counter_map, incr_per_thread),
        name=f"Thread-{t_id+1}"
    )
    thread.start()
    worker_threads.append(thread)

# Очікуємо завершення кожного потоку
for thread in worker_threads:
    thread.join()

# Обчислення часу виконання
duration = time.time() - start

# Отримання фінального значення
final_result = naive_counter_map.get("counter")

# Вивід результатів
print(f"Final result: {final_result}, time: {duration:.2f} seconds")
print(f"Expected result: {expected_total}")

# Завершення з'єднання з Hazelcast
hz_client.shutdown()
