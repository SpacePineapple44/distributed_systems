import hazelcast, threading, time  

# Функція, яка виконує інкремент значення у розподіленій мапі з використанням песимістичного блокування
def locked_increment(shared_map, operations_count):
    for _ in range(operations_count):
        # Захоплюємо блокування для ключа "counter"
        shared_map.lock("counter")
        try:
            # Отримуємо поточне значення або 0, якщо ключ ще не існує
            current_val = shared_map.get("counter") or 0

            # Збільшуємо значення на одиницю
            shared_map.put("counter", current_val + 1)
        finally:
            # Гарантовано звільняємо блокування після завершення операції
            shared_map.unlock("counter")

# Ініціалізація клієнта Hazelcast і підключення до кластеру
hz_client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",
    cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
)

# Отримання розподіленої мапи з іменем "sync_counter_map"
sync_counter_map = hz_client.get_map("sync_counter_map").blocking()

# Ініціалізація початкового значення лічильника
sync_counter_map.put("counter", 0)

# Налаштування: скільки разів кожен потік інкрементує значення
incr_per_thread = 10_000

# Кількість потоків, які будуть одночасно працювати
number_of_threads = 3

# Обчислення очікуваного результату після завершення всіх потоків
expected_total = incr_per_thread * number_of_threads

# Вивід роздільника перед стартом тесту
print("\n---------------->>>")

# Фіксуємо час початку виконання
start = time.time()

# Список для зберігання потоків
worker_threads = []

# Створення та запуск потоків
for t_id in range(number_of_threads):
    # Створюємо потік для запуску locked_increment
    thread = threading.Thread(
        target=locked_increment,
        args=(sync_counter_map, incr_per_thread),
        name=f"Thread-{t_id+1}"
    )
    thread.start()
    worker_threads.append(thread)

# Очікуємо завершення кожного потоку
for thread in worker_threads:
    thread.join()

# Обчислюємо, скільки часу зайняв весь процес
duration = time.time() - start

# Отримуємо фінальне значення лічильника
final_result = sync_counter_map.get("counter")

# Виводимо результати
print(f"Final result: {final_result}, time: {duration:.2f} seconds")
print(f"Expected result: {expected_total}")

# Завершення з'єднання з Hazelcast
hz_client.shutdown()
