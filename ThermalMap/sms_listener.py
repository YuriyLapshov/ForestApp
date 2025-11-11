import queue
import threading
import time
import serial
import logging
from django.apps import AppConfig
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from ThermalMap.models import DeviceStatus
import re


class SMSListener:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            print("🆕 Creating NEW SMSListener instance")
            cls._instance = super(SMSListener, cls).__new__(cls)
        else:
            print(f"♻️ Returning EXISTING SMSListener instance: {id(cls._instance)}")
        return cls._instance

    def __init__(self):
        if self._initialized:
            print(f"♻️ SMSListener already initialized: {id(self)}")
            return

        print(f"🆕 Initializing SMSListener: {id(self)}")
        self._initialized = True
        self.running = False
        self.thread = None
        self.ser = None
        self.send_queue = []
        self.lock = threading.Lock()

    def start_listening(self):
        """Запуск прослушивания SMS в фоне"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("SMS listener started")

    def stop_listening(self):
        """Остановка прослушивания"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("SMS listener stopped")

    def _listen_loop(self):
        """Основной цикл прослушивания - БЕЗОПАСНАЯ ВЕРСИЯ"""
        try:
            # Инициализация соединения с SIM800C
            self.ser = serial.Serial('COM3', 9600, timeout=1)
            time.sleep(2)

            # Настройка модуля для приема SMS
            self._setup_sms_reception()

            # Счетчик для периодической очистки
            last_cleanup = time.time()

            while self.running:
                self._process_send_queue()
                # Шаг 1: Читаем и ОБРАБАТЫВАЕМ новые SMS
                new_sms = self._check_new_sms()
                if new_sms:
                    self._process_sms(new_sms)
                    # Удаляем ТОЛЬКО обработанные SMS
                    self._delete_processed_sms(new_sms)

                # Шаг 2: Периодическая очистка ТОЛЬКО старых SMS (раз в 30 минут)
                current_time = time.time()
                if current_time - last_cleanup > 1800:  # 30 минут
                    self._cleanup_old_sms_only()
                    last_cleanup = current_time

                time.sleep(2)

        except Exception as e:
            logging.error(f"Error in SMS listener: {e}")

    def _setup_sms_reception(self):
        """Настройка модуля для приема SMS"""
        try:
            # Текстовый режим
            self.ser.write(b'AT+CMGF=1\r\n')
            time.sleep(1)

            # Устанавливаем режим уведомлений о новых SMS
            self.ser.write(b'AT+CNMI=2,1,0,0,0\r\n')
            time.sleep(1)

            print("SMS reception configured")
        except Exception as e:
            logging.error(f"Error setting up SMS reception: {e}")

    def _check_new_sms(self):
        """Проверка новых SMS - БЕЗ автоматического удаления"""
        try:
            # Читаем все непрочитанные SMS
            self.ser.write(b'AT+CMGL="REC UNREAD"\r\n')
            time.sleep(1)

            response = self.ser.read(1000).decode('utf-8', errors='ignore')

            if '+CMGL:' in response:
                return self._parse_sms_with_index(response)  # Сохраняем индексы!
            return None

        except Exception as e:
            logging.error(f"Error checking SMS: {e}")
            return None

    def _parse_sms_with_index(self, response):
        """Парсинг SMS с сохранением индексов для последующего удаления"""
        sms_list = []
        lines = response.split('\r\n')

        i = 0
        while i < len(lines):
            if '+CMGL:' in lines[i]:
                # Парсим информацию о SMS, включая ИНДЕКС
                # Формат: +CMGL: <index>,<status>,<phone>,...
                parts = lines[i].split(',')
                sms_index = parts[0].split(':')[1].strip()

                i += 1
                if i < len(lines):
                    sms_text = lines[i]
                    sms_list.append({
                        'index': sms_index,  # ⭐ Сохраняем индекс!
                        'info': lines[i - 1],
                        'text': sms_text,
                        'timestamp': time.time()
                    })
            i += 1

        return sms_list

    def _delete_processed_sms(self, sms_list):
        """Удаляем ТОЛЬКО обработанные SMS по их индексам"""
        try:
            for sms in sms_list:
                # Удаляем конкретное SMS по индексу
                self.ser.write(f'AT+CMGD={sms["index"]}\r\n'.encode())
                time.sleep(0.5)
                response = self.ser.read(100).decode('utf-8', errors='ignore')

                if 'OK' in response:
                    print(f"SMS index {sms['index']} deleted")
                else:
                    print(f"Failed to delete SMS index {sms['index']}")

        except Exception as e:
            logging.error(f"Error deleting processed SMS: {e}")

    def _cleanup_old_sms_only(self):
        """Очистка ТОЛЬКО старых ПРОЧИТАННЫХ SMS (не трогаем непрочитанные)"""
        try:
            # Удаляем только прочитанные SMS старше 1 часа
            # Сначала помечаем старые непрочитанные как прочитанные
            self._mark_old_as_read()

            # Затем удаляем только прочитанные
            self.ser.write(b'AT+CMGDA="DEL READ"\r\n')
            time.sleep(2)
            response = self.ser.read(100).decode('utf-8', errors='ignore')

            if 'OK' in response:
                print("Old read SMS cleaned up")
            else:
                print("Failed to clean up old SMS")

        except Exception as e:
            print(f"Error during old SMS cleanup: {e}")

    def _mark_old_as_read(self):
        """Помечаем старые непрочитанные SMS как прочитанные"""
        try:
            # Читаем все SMS (включая непрочитанные)
            self.ser.write(b'AT+CMGL="ALL"\r\n')
            time.sleep(1)
            response = self.ser.read(1000).decode('utf-8', errors='ignore')

            # Здесь можно добавить логику для пометки старых SMS как прочитанных
            # если они висят дольше определенного времени

        except Exception as e:
            print(f"Error marking old SMS as read: {e}")

    def _process_sms(self, sms_list):
        """Обработка полученных SMS"""
        for sms in sms_list:
            print(f"New SMS received: {sms}")
            print(f"Phone Number: {self._extract_phone_number(sms['info'])}")

            try:
                device = DeviceStatus.objects.get(phone_number=self._extract_phone_number(sms['info']))
                print(f"Message received: {sms}")
                if sms['text'].startswith('equipment is power on'):
                    print(f"Status message received! device: {device}")
                    device.status = 4
                    device.save()
                if sms['text'].startswith('equipment is power off'):
                    print(f"Status message received! device: {device}")
                    device.status = 0
                    device.save()
                if sms['text'].startswith('STATUS IS ALL'):
                    print(f"Status IS ALL message received! device: {device}")
                    t1_match = re.search(r'T1:\s*([-+]?\d*\.?\d+)', sms['text'])
                    print(f"t1_match: {t1_match}")
                    t2_match = re.search(r'T2:\s*([-+]?\d*\.?\d+)', sms['text'])
                    print(f"t2_match: {t1_match}")

                    t1 = float(t1_match.group(1)) if t1_match else None
                    print(f"t1: {t1}")
                    t2 = float(t2_match.group(1)) if t2_match else None
                    print(f"t2: {t2}")
                    if t1 is not None:
                        device.temperature1 = t1
                    else:
                        device.temperature1 = -100
                    if t2 is not None:
                        device.temperature2 = t2
                    else:
                        device.temperature2 = -100
                    device.status = 1
                    device.update_datetime = timezone.now()
                    device.save()
                    print("Status saved.")
                if sms['text'].startswith('1st temp'):
                    match = re.search(r'([-+]?\d+\.?\d*)C', sms['text'])
                    if match:
                        temp = float(match.group(1))
                        device.status = 2
                        device.temperature1 = temp
                        device.update_datetime = timezone.now()
                        device.save()
                    if sms['text'].startswith('2nd temp'):
                        match = re.search(r'([-+]?\d+\.?\d*)C', sms['text'])
                        if match:
                            temp = float(match.group(1))
                            device.status = 3
                            device.temperature2 = temp
                            device.update_datetime = timezone.now()
                            device.save()
            except ObjectDoesNotExist:
                print("SMS received from device not in database")
                pass

            # Здесь можно добавить логику обработки:
            # - Сохранение в базу данных
            # - Отправка уведомлений
            # - Вызов других функций Django
            # - Автоматический ответ и т.д.

            # Пример: автоматический ответ
            # self._send_auto_reply(sms)

    def _extract_phone_number(self, sms_info):
        """Извлечение номера телефона из информации о SMS"""
        # Упрощенный парсинг - нужно доработать под ваш формат

        match = re.search(r'\"(\+?\d+)\"', sms_info)
        return match.group(1) if match else None

    def _process_send_queue(self):
        """Обработка очереди отправки SMS"""
        with self.lock:  # ⭐ Блокировка на ВСЮ операцию
            print(f"🔍 DEBUG: Queue length = {len(self.send_queue)}")

            if not self.send_queue:
                print("🔍 DEBUG: Queue is EMPTY")
                return

            # Берем первую SMS из очереди
            phone, message = self.send_queue[0]
            print(f"🔍 DEBUG: Processing {phone}: {message}")

            try:
                print(f"📤 Отправка SMS на {phone}: {message}")

                # Отправка SMS
                self.ser.reset_input_buffer()
                self.ser.write(b'AT+CMGF=1\r\n')
                time.sleep(1)

                self.ser.write(f'AT+CMGS="{phone}"\r\n'.encode())
                time.sleep(1)
                self.ser.write(message.encode() + b'\r\n')
                time.sleep(0.5)
                self.ser.write(bytes([26]))
                time.sleep(3)

                response = self.ser.read(200).decode('utf-8', errors='ignore')
                print(f"🔍 DEBUG Send response: {response}")

                if 'OK' in response or '+CMGS' in response:
                    print(f"✅ SMS отправлено на {phone}")
                    # Удаляем из очереди при успехе
                    self.send_queue.pop(0)
                    print(f"🔍 DEBUG: Removed from queue, new length: {len(self.send_queue)}")
                else:
                    print(f"❌ Ошибка отправки: {response}")
                    # Можно реализовать повторные попытки или удалить при ошибке
                    self.send_queue.pop(0)  # или оставить для повторной попытки

            except Exception as e:
                print(f"❌ Ошибка при отправке: {e}")

    def clear_number(self, dirty_number):
        phone_number = ''.join(filter(str.isdigit, dirty_number))
        if not phone_number.startswith('7') and not phone_number.startswith('8'):
            phone_number = '7' + phone_number

        # Форматируем номер в международный формат
        if phone_number.startswith('8'):
            phone_number = '7' + phone_number[1:]
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        return phone_number

    def poll_all_devices(self):
        devices = DeviceStatus.objects.all()
        for device in devices:
            device.request_datetime = timezone.now()
            device.save()
            self.send(self.clear_number(device.phone_number), 'SN0000OFF')

    def send(self, phone, message):
        """Добавление SMS в очередь отправки"""
        with self.lock:  # ⭐ Блокировка при добавлении
            self.send_queue.append((phone, message))
            print(f"📨 SMS добавлено в очередь для {phone}: {message}")
            print(f"📊 В очереди: {len(self.send_queue)} сообщений")
            print(f"🔍 DEBUG Queue contents: {self.send_queue}")  # ⭐ Для отладки


# Глобальный экземпляр слушателя
sms_listener = SMSListener()
