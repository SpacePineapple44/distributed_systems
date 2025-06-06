
import hazelcast  # Імпорт клієнта Hazelcast для Python
import time       # Імпорт модуля time (не використовується, але може знадобитися для затримок)

# Ініціалізація клієнта Hazelcast для підключення до існуючого кластера
client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",  # Назва цільового кластера Hazelcast
    cluster_members=[
        "localhost:5701",  # IP-адреси/порти вузлів кластера
        "localhost:5702",
        "localhost:5703"
    ]
)

# Отримання розподіленої мапи з іменем "my-distributed-map"
# blocking() робить доступ до мапи синхронним (очікує завершення операцій)
distributed_map = client.get_map("my-distributed-map").blocking()

# Цикл для запису 1000 пар ключ-значення у мапу
for i in range(1000):
    key = str(i)              # Ключ у форматі рядка (наприклад, "0", "1", ..., "999")
    value = f"value_{i}"      # Значення у форматі рядка (наприклад, "value_0", ..., "value_999")
    distributed_map.put(key, value)  # Додавання пари ключ-значення у мапу

# Після завершення циклу — вивід повідомлення про успішне завершення
print("Записано значень: 1000 до Distributed Map!")

# Вивід загальної кількості записів, що зберігаються у мапі
print(f"Map size: {distributed_map.size()}")

# Закриття клієнта — завершує з'єднання з кластером Hazelcast
client.shutdown()
