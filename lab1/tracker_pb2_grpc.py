import grpc, tracker_pb2, tracker_pb2_grpc
from concurrent import futures

# ------------------- ВНУТРІШНЄ СХОВИЩЕ -------------------
# Простий словник, що використовується для зберігання надісланих записів
# Формат: {ключ: значення}, наприклад: {"abc-123": "some data"}
collected_entries = {}

# ------------------- ВИЗНАЧЕННЯ gRPC-СЕРВІСУ -------------------
# Створюємо клас, що реалізує сервіс із .proto (наслідуємо TrackerServicer)
class TrackerService(tracker_pb2_grpc.TrackerServicer):

    # Метод LogEntry — обробляє вхідні записи
    def LogEntry(self, request, context):
        entry_key = request.key
        entry_value = request.data

        # Перевірка: якщо ключ або дані порожні — відправляємо помилку клієнту
        if not (entry_key and entry_value):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)

            # Повідомлення для клієнта
            context.set_details("Missing key or data")

            # Відповідь з помилкою
            return tracker_pb2.LogResponse(status="Error")

        # Перевірка на дублікати: якщо запис із таким ключем вже існує
        if entry_key in collected_entries:
            print(f"Repeated entry skipped: {entry_key}")
            return tracker_pb2.LogResponse(status="Skipped repeat")

        # Якщо все коректно — зберігаємо запис
        collected_entries[entry_key] = entry_value
        print(f"Tracked: {entry_value} [Key: {entry_key}]")

        # Повертаємо статус "успішно записано"
        return tracker_pb2.LogResponse(status="Entry recorded")

    # Метод GetEntries — повертає всі збережені значення
    def GetEntries(self, request, context):
        # Об'єднуємо всі значення в один рядок, розділяючи комами
        all_values = ", ".join(collected_entries.values())

        #Формуємо об'єкт відповіді з цим рядком
        return tracker_pb2.EntriesResponse(entries=all_values)

# ------------------- ЗАПУСК gRPC-СЕРВЕРА -------------------
def run_grpc_server():

    # Створюємо gRPC-сервер з можливістю обробки до 10 потоків одночасно
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Реєструємо наш сервіс (TrackerService) у gRPC-сервері
    tracker_pb2_grpc.add_TrackerServicer_to_server(TrackerService(), server)

    # Призначаємо порт, на якому буде слухати сервер (50051)
    server.add_insecure_port('[::]:50051')
    print("gRPC TrackerService running on port 50051...")
    server.start()

    # Чекаємо завершення (щоб програма не завершилася відразу)
    server.wait_for_termination()

# ------------------- ТОЧКА ВХОДУ У ПРОГРАМУ -------------------
if __name__ == "__main__":
    run_grpc_server()
