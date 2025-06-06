import hazelcast, threading, time         

# Функція для інкременту значення за ключем у розподіленій мапі
def increment_counter(map_instance, count):
    for _ in range(count):
        current = map_instance.get("key") or 0   # Отримуємо поточне значення (якщо None — беремо 0)
        map_instance.put("key", current + 1)     # Збільшуємо значення на 1 та записуємо назад

# Ініціалізація клієнта Hazelcast та підключення до кластера
client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",  # Назва кластера
    cluster_members=[
        "localhost:5701",       # Список вузлів кластера (IP:порт)
        "localhost:5702",
        "localhost:5703"
    ]
)

# Отримання мапи з назвою "new_map" у блокуючому (синхронному) режимі
distributed_map = client.get_map("new_map").blocking()

# Ініціалізація ключа "key" зі значенням 0
distributed_map.put("key", 0)

# Кількість інкрементів у кожному потоці
count = 10_000

# Кількість потоків
thread_num = 3

# Очікуване фінальне значення після завершення всіх потоків
expected_value = count * thread_num

# Початок вимірювання часу
start_time = time.time()

# Створення та запуск потоків
threads = []
for i in range(thread_num):
    # Кожен потік викликає функцію increment_counter з переданими аргументами
    thread = threading.Thread(
        target=increment_counter,
        args=(distributed_map, count),
        name=f"IncThread-{i+1}"  # Ім’я потоку для зручності (не обов’язково)
    )
    thread.start()      # Запуск потоку
    threads.append(thread)  # Додавання до списку потоків

# Очікування завершення всіх потоків
for thread in threads:
    thread.join()

# Завершено — обрахунок і вивід результатів
elapsed = time.time() - start_time  # Скільки часу зайняло виконання
final_value = distributed_map.get("key")  # Фінальне значення за ключем "key"
print(f"результат: {final_value}, time: {elapsed:.2f} сек.")
print(f"Очікуваний результат: {expected_value}")  # Виводимо, яке значення ми очікували

# Закриття клієнта Hazelcast
client.shutdown()
