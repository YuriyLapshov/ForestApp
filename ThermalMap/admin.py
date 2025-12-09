from django.apps import apps
from django.contrib import admin
from django import forms
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse, path
from django.utils.html import format_html
from .models import DeviceStatus


# Изменяем заголовки
admin.site.site_header = 'Администрирование ThermalForest'  # Заголовок на странице входа
admin.site.site_title = 'Управление устройствами'  # Заголовок вкладки браузера
admin.site.index_title = 'Администрирование ThermalForest'  # Заголовок на главной странице админки

class DeviceStatusForm(forms.ModelForm):
    map_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    map_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = DeviceStatus
        fields = '__all__'


class DeviceStatusAdmin(admin.ModelAdmin):
    form = DeviceStatusForm
    # change_form_template = 'admin/device_status_change_form.html'

    # Используем только реальные поля модели + один кастомный метод
    list_display = [
        'name',
        'phone_number',
        'temperature1',  # прямое поле модели
        'temperature2',  # прямое поле модели
        'status',  # автоматический метод Django для choices
        'coordinates_display',  # кастомный метод
        'update_datetime',
        'request_datetime',
        'action_buttons',  # НОВОЕ: кнопки действий
        'map_link'  # кастомный метод
    ]

    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'phone_number', 'status']
        }),
        ('Температуры', {
            'fields': ['temperature1', 'temperature2'],
            'classes': ['collapse']
        }),
        ('Выбор местоположения на карте', {
            'fields': ['map_latitude', 'map_longitude'],
            'description': 'Кликните на карте для выбора местоположения'
        }),
        ('Географические координаты', {
            'fields': ['latitude', 'longitude'],
            'classes': ['collapse'],
            'description': 'Автоматически заполняются при выборе на карте'
        }),
        ('Временные метки', {
            'fields': ['update_datetime', 'request_datetime'],
            'classes': ['collapse']
        }),
    ]

    readonly_fields = ['update_datetime', 'request_datetime']
    list_filter = ['status', 'update_datetime']
    search_fields = ['name', 'phone_number']

    class Media:
        js = (
            'https://api-maps.yandex.ru/2.1/?apikey=ваш_api_ключ&lang=ru_RU',
            'admin/js/yandex_map.js',  # наш кастомный JS файл
        )
        css = {
            'all': ('admin/css/yandex_map.css',)
        }

    # Минимальные кастомные методы
    def coordinates_display(self, obj):
        if obj.latitude is not None and obj.longitude is not None:
            return f"{obj.latitude:.6f}, {obj.longitude:.6f}"
        return "❌ Нет координат"

    coordinates_display.short_description = 'Координаты'

    def map_link(self, obj):
        if obj.latitude is not None and obj.longitude is not None:
            url = obj.get_yandex_map_url()
            return format_html(
                '<a href="{}" target="_blank">🗺️</a>',
                url
            )
        return "—"

    map_link.short_description = 'Карта'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/register/',
                 self.admin_site.admin_view(self.register_device),
                 name='register_device'),
        ]
        return custom_urls + urls

    def action_buttons(self, obj):
        register_button = format_html(
            '<a class="button" href="{}" style="background-color: #4CAF50; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;">'
            'Прописать в системе'
            '</a>',
            reverse('admin:register_device', args=[obj.id])
        )
        return format_html(
            '<div style="display: flex; gap: 5px; white-space: nowrap;">'
            '{}'
            '</div>',
            register_button
        )

    action_buttons.short_description = 'Действия'
    action_buttons.allow_tags = True

    def register_device(self, request, object_id):
        try:
            device = DeviceStatus.objects.get(id=object_id)
            app_config = apps.get_app_config('ThermalMap')
            if not hasattr(app_config, 'sms_listener') or app_config.sms_listener is None:
                return JsonResponse({"error": "SMS listener not initialized"}, status=500)
            sms_listener = app_config.sms_listener
            sms_listener.init_device(device.phone_number)
        except DeviceStatus.DoesNotExist:
            pass


    # Возвращаемся на страницу списка устройств
        return HttpResponseRedirect(
            reverse('admin:ThermalMap_devicestatus_changelist')
        )
    def save_model(self, request, obj, form, change):
        map_lat = form.cleaned_data.get('map_latitude')
        map_lon = form.cleaned_data.get('map_longitude')

        if map_lat and map_lon:
            obj.latitude = map_lat
            obj.longitude = map_lon

        super().save_model(request, obj, form, change)


admin.site.register(DeviceStatus, DeviceStatusAdmin)
