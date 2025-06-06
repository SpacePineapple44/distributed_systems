import hazelcast
import threading
import time

# Ініціалізація Hazelcast клієнта
hz_client = hazelcast.HazelcastClient(
    cluster_name="my-cluster",
    cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
)

# Отримуємо синхронну чергу
bounded_queue = hz_client.get_queue("bounded-demo-queue").blocking()

# Флаг завершення роботи продюсера
is_producer_done = False

# Флаг для завершення демонстраційного потоку put()
stop_put_attempt = False

# ---------- Продюсер ----------

def queue_producer():
    global is_producer_done
    print("Producer: почав запис значень від 1 до 100")
    for number in range(1, 101):
        bounded_queue.put(number)
        print(f"Producer: записав {number}, розмір черги: {bounded_queue.size()}")
        time.sleep(0.05)  # Симуляція затримки при записі
    print("Producer: завершив запис")
    is_producer_done = True

# ---------- Консюмер ----------

def queue_consumer(consumer_id):
    print(f"Consumer {consumer_id}: старт читання")
    while not is_producer_done or bounded_queue.size() > 0:
        try:
            item = bounded_queue.poll(timeout=1.0)
            if item is None:
                # Якщо черга порожня і продюсер завершився — вихід
                if is_producer_done and bounded_queue.size() == 0:
                    break
                continue
            print(f"Consumer {consumer_id}: прочитав {item}, розмір черги: {bounded_queue.size()}")
        except Exception as e:
            print(f"Consumer {consumer_id}: помилка: {e}")
            break
    print(f"Consumer {consumer_id}: завершив читання")

# ---------- Демонстрація блокування при переповненій черзі ----------

def try_blocking_put(queue_ref):
    global stop_put_attempt
    try:
        queue_ref.put(11)  # Очікується блокування, якщо черга заповнена
        print("Unexpected: елемент 11 додано, але не мав би")
    except Exception as e:
        if not stop_put_attempt:
            print(f"Помилка в try_blocking_put: {e}")

def test_queue_blocking_behavior():
    global stop_put_attempt
    print("\nТест: поведінка при повній черзі (без споживачів)")
    
    bounded_queue.clear()
    print("Черга очищена")

    # Записуємо до повної місткості (10 елементів)
    for i in range(1, 11):
        bounded_queue.put(i)
        print(f"Producer (тест): записав {i}, розмір черги: {bounded_queue.size()}")

    print("Спроба додати 11-й елемент — очікується блокування...")
    start_block_time = time.time()

    block_thread = threading.Thread(target=try_blocking_put, args=(bounded_queue,))
    block_thread.daemon = True
    block_thread.start()

    time.sleep(5)
    elapsed = time.time() - start_block_time

    if block_thread.is_alive():
        print(f"Очікувано: put() заблокований вже {elapsed:.2f} с.")
    else:
        print("Неочікувано: put() не заблокувався")

    stop_put_attempt = True

# ---------- Головна логіка ----------

if __name__ == "__main__":
    print("Запуск демо з Producer та Consumers")

    producer_thread = threading.Thread(target=queue_producer, name="Producer")
    consumer_thread_1 = threading.Thread(target=queue_consumer, args=(1,), name="Consumer-1")
    consumer_thread_2 = threading.Thread(target=queue_consumer, args=(2,), name="Consumer-2")

    # Старт потоків
    producer_thread.start()
    consumer_thread_1.start()
    consumer_thread_2.start()

    # Очікуємо завершення
    producer_thread.join()
    consumer_thread_1.join()
    consumer_thread_2.join()

    # Тест поведінки при повній черзі
    test_queue_blocking_behavior()

    hz_client.shutdown()
    print("\nДемонстрація завершена")
