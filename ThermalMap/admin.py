from django.contrib import admin
from django.utils.html import format_html
from .models import DeviceStatus


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'phone_number',
        'temperature_display',
        'status',
        'coordinates_display',
        'update_datetime',
        'map_link'
    ]

    list_filter = ['status', 'update_datetime']
    search_fields = ['name', 'phone_number']
    readonly_fields = ['update_datetime', 'map_preview']
    list_editable = ['status']

    # Порядок полей в форме редактирования
    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'phone_number', 'status']
        }),
        ('Температуры', {
            'fields': ['temperature1', 'temperature2'],
            'classes': ['collapse']
        }),
        ('Географические координаты', {
            'fields': ['latitude', 'longitude', 'map_preview'],
            'description': 'Координаты для отображения на карте'
        }),
        ('Временные метки', {
            'fields': ['update_datetime'],
            'classes': ['collapse']
        }),
    ]

    # Кастомные методы для отображения
    def temperature_display(self, obj):
        if obj.temperature1 and obj.temperature2:
            return f"{obj.temperature1}°C / {obj.temperature2}°C"
        return "-"

    temperature_display.short_description = 'Температуры'

    def status_display(self, obj):
        status_map = {0: '🔴 Отключено (нет питания)', 1: '🟢 ОК', 2: '🟡 Перегрев датчик 1', 3: '🟡 Перегрев датчик 2',
                      4: '🔵 Включено (питание подано)'}
        return status_map.get(obj.status, 'Неизвестно')

    status_display.short_description = 'Статус'

    def coordinates_display(self, obj):
        if obj.has_coordinates:
            return f"{obj.latitude:.6f}, {obj.longitude:.6f}"
        return "❌ Нет координат"

    coordinates_display.short_description = 'Координаты'

    def map_link(self, obj):
        if obj.has_coordinates:
            url = obj.get_yandex_map_url()
            return format_html(
                '<a href="{}" target="_blank" style="background: #FF0000; color: white; padding: 2px 6px; border-radius: 3px; text-decoration: none;">🗺️ На карте</a>',
                url
            )
        return "—"

    map_link.short_description = 'Карта'

    def map_preview(self, obj):
        """Превью карты в форме редактирования"""
        if obj.has_coordinates:
            # Статическая карта Яндекс (можно использовать API для превью)
            static_map_url = f"https://static-maps.yandex.ru/1.x/?ll={obj.longitude},{obj.latitude}&size=450,300&z=13&l=map&pt={obj.longitude},{obj.latitude},pm2rdm"
            return format_html(
                '''
                <div>
                    <a href="{}" target="_blank">
                        <img src="{}" style="max-width: 450px; height: auto; border: 1px solid #ccc; border-radius: 4px;" alt="Карта"/>
                    </a>
                    <p style="margin-top: 5px; font-size: 12px; color: #666;">
                        <a href="{}" target="_blank">Открыть в Яндекс.Картах</a>
                    </p>
                </div>
                ''',
                obj.get_yandex_map_url(),
                static_map_url,
                obj.get_yandex_map_url()
            )
        return "❌ Координаты не указаны"

    map_preview.short_description = 'Превью на карте'

    # Действия для массового обновления
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(status=1)

    make_active.short_description = "Перевести в статус 'Активно'"

    def make_inactive(self, request, queryset):
        queryset.update(status=0)

    make_inactive.short_description = "Перевести в статус 'Неактивно'"