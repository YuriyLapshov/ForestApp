import os
from django.apps import AppConfig


class ThermalmapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ThermalMap"
    sms_listener = None  # ⭐ Добавляем атрибут для хранения ссылки

    def ready(self):
        # ⭐ Запускаем только в основном процессе сервера
        if os.environ.get('RUN_MAIN') != 'true':
            print("⏸️ Reloader process detected - skipping SMS listener")
            return

        print("🔄 Main server process - starting SMS Listener")

        from ThermalMap.sms_listener import sms_listener
        self.sms_listener = sms_listener  # ⭐ Сохраняем ссылку!

        if not sms_listener.running:
            sms_listener.start_listening()
            print("✅ SMS Listener started successfully")