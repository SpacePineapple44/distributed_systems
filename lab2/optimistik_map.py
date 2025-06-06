import hazelcast, threading, time

# Функція для оптимістичного інкременту значення у мапі (CAS-логіка)
def cas_increment(sync_map_ref, op_count):
    for _ in range(op_count):
        while True:
            current_val = sync_map_ref.get("key") or 0     # Поточне значення або 0
            updated_val = current_val + 1                  # Нове значення

            # CAS-операція: замінюємо тільки якщо не змінилося
            if sync_map_ref.replace_if_same("key", current_val, updated_val):
                break

# Ініціалізація клієнта Hazelcast
hz_client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",
    cluster_members=[
        "localhost:5701",
        "localhost:5702",
        "localhost:5703"
    ]
)

# Отримання об'єкта синхронної мапи
sync_map = hz_client.get_map("data_cache").blocking()

# Початкове значення
sync_map.put("key", 0)

# Конфігурація потоків
ops_per_thread = 10_000
num_threads = 3
expected_total = ops_per_thread * num_threads

# Початок вимірювання часу
start_ts = time.time()

# Створення та запуск потоків
worker_threads = []
for i in range(num_threads):
    t = threading.Thread(
        target=cas_increment,
        args=(sync_map, ops_per_thread),
        name=f"CASWorker-{i+1}"
    )
    t.start()
    worker_threads.append(t)

# Очікування завершення всіх потоків
for t in worker_threads:
    t.join()

# Завершення вимірювання
elapsed_ts = time.time() - start_ts

# Отримання фінального результату
final_val = sync_map.get("key")

# Вивід результатів
print(f"Фінальне значення: {final_val}, час виконання: {elapsed_ts:.2f} с.")
print(f"Очікуване значення: {expected_total}")

# Завершення роботи клієнта
hz_client.shutdown()
