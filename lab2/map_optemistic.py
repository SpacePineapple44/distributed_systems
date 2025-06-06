import hazelcast, threading, time  # Імпортуємо клієнт Hazelcast, модуль для роботи з потоками та модуль для часу

# Функція для потокобезпечного інкременту значення в мапі за допомогою оптимістичної блокування (CAS-підхід)
def optimistic_increment(map_instance, count):
    for i in range(count):
        while True:
            # Отримуємо поточне значення за ключем "key", якщо None — беремо 0
            old_value = map_instance.get("key") or 0

            # Обчислюємо нове значення, збільшуючи поточне на 1
            new_value = old_value + 1

            # Намагаймося замінити старе значення на нове лише якщо воно не змінилося іншим потоком
            if map_instance.replace_if_same("key", old_value, new_value):
                # Якщо заміна пройшла успішно — виходимо з циклу
                break

# Створюємо клієнт Hazelcast та підключаємось до кластера
client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",  # Вказуємо назву кластера
    cluster_members=[
        "localhost:5701",       # Вузли кластеру Hazelcast
        "localhost:5702",
        "localhost:5703"
    ]
)

# Отримуємо розподілену мапу з назвою "new_map", у синхронному режимі (blocking)
distributed_map = client.get_map("new_map").blocking()

# Ініціалізуємо значення за ключем "key" нулем
distributed_map.put("key", 0)

# Кількість інкрементів, які виконає кожен потік
count = 10_000

# Кількість потоків, які будуть працювати паралельно
thread_num = 3

# Очікуване значення після завершення всіх потоків (10_000 * 3)
expected_value = count * thread_num

# Починаємо відлік часу виконання
start_time = time.time()

# Створення та запуск потоків
threads = []
for i in range(thread_num):
    # Створюємо потік з цільовою функцією optimistic_increment
    thread = threading.Thread(
        target=optimistic_increment,
        args=(distributed_map, count),
        name=f"IncThread-{i+1}"  # Ім’я потоку (для діагностики, не обов’язково)
    )
    thread.start()      # Запускаємо потік
    threads.append(thread)  # Додаємо потік у список

# Очікуємо завершення всіх потоків
for thread in threads:
    thread.join()

# Вимірюємо скільки часу пройшло
elapsed = time.time() - start_time

# Отримуємо фінальне значення ключа "key" після роботи всіх потоків
final_value = distributed_map.get("key")

# Виводимо отриманий та очікуваний результат, а також час виконання
print(f"фінальний результат: {final_value}, час: {elapsed:.2f} сек.")
print(f"Очікуваний результат: {expected_value}")

# Завершуємо роботу клієнта Hazelcast
client.shutdown()
