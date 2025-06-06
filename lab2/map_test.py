import hazelcast, time

# Створення клієнта для підключення до кластеру Hazelcast
hz_client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",  # Вказуємо назву кластера
    cluster_members=[
        "localhost:5701",  # Список вузлів кластеру
        "localhost:5702",
        "localhost:5703"
    ]
)

# Отримуємо об'єкт синхронної розподіленої мапи
sync_map = hz_client.get_map("data_cache").blocking()

# Записуємо 1000 пар ключ-значення у розподілену мапу
for idx in range(1000):
    entry_key = str(idx)                 # Ключ у вигляді рядка
    entry_val = f"entry_{idx}"           # Значення у вигляді рядка
    sync_map.put(entry_key, entry_val)   # Додаємо запис у мапу

# Виводимо підтвердження успішного завершення запису
print("Успішно збережено 1000 записів у мапу!")

# Виводимо загальну кількість записів у мапі
print(f"Розмір мапи: {sync_map.size()}")

# Закриваємо клієнт — завершуємо з'єднання з кластером
hz_client.shutdown()
