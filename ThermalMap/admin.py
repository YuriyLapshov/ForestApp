from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import DeviceStatus


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
        'get_status_display',  # автоматический метод Django для choices
        'coordinates_display',  # кастомный метод
        'update_datetime',
        'request_datetime',
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

    def save_model(self, request, obj, form, change):
        map_lat = form.cleaned_data.get('map_latitude')
        map_lon = form.cleaned_data.get('map_longitude')

        if map_lat and map_lon:
            obj.latitude = map_lat
            obj.longitude = map_lon

        super().save_model(request, obj, form, change)


admin.site.register(DeviceStatus, DeviceStatusAdmin)
