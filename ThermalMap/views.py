import json
import logging
import time

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
import serial.tools.list_ports
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import DeviceStatus


@login_required(login_url='/admin/login/')
def index(request):
    return redirect('devices_map')


@login_required(login_url='/admin/login/')
@csrf_exempt
@require_http_methods(["GET"])
def send_sms_view(request):
    """Django view для отправки SMS через GET-запрос"""

    # Получаем параметры из GET-запроса
    phone_number = request.GET.get('phone', '').strip()
    message = request.GET.get('message', '').strip()

    # Валидация параметров
    if not phone_number:
        return JsonResponse({
            'status': 'error',
            'message': 'Не указан номер телефона (параметр phone)'
        }, status=400)

    if not message:
        return JsonResponse({
            'status': 'error',
            'message': 'Не указан текст сообщения (параметр message)'
        }, status=400)

    # Очищаем номер телефона от лишних символов
    phone_number = ''.join(filter(str.isdigit, phone_number))
    if not phone_number.startswith('7') and not phone_number.startswith('8'):
        phone_number = '7' + phone_number

    # Форматируем номер в международный формат
    if phone_number.startswith('8'):
        phone_number = '7' + phone_number[1:]
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    print(f"Попытка отправки SMS на {phone_number}: {message[:50]}...")
    app_config = apps.get_app_config('ThermalMap')

    if not hasattr(app_config, 'sms_listener') or app_config.sms_listener is None:
        return JsonResponse({"error": "SMS listener not initialized"}, status=500)

    sms_listener = app_config.sms_listener
    sms_listener.send(phone_number, message)
    return JsonResponse({
        'status': 'success',
        'message': f'SMS поставлено на отправку {phone_number}',
        'sms_length': len(message)
    })


@login_required(login_url='/admin/login/')
def poll_devices(request):
    app_config = apps.get_app_config('ThermalMap')
    if not hasattr(app_config, 'sms_listener') or app_config.sms_listener is None:
        return JsonResponse({"error": "SMS listener not initialized"}, status=500)
    sms_listener = app_config.sms_listener
    sms_listener.poll_all_devices()
    return redirect('devices_map')


@login_required(login_url='/admin/login/')
def devices_map(request):
    # Получаем все устройства с координатами
    devices = DeviceStatus.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(latitude=0, longitude=0)

    # Подготавливаем данные для JSON
    devices_data = []
    for device in devices:
        devices_data.append({
            'id': device.id,
            'name': device.name,
            'phone_number': device.phone_number,
            'latitude': float(device.latitude),
            'longitude': float(device.longitude),
            'temperature1': device.temperature1,
            'temperature2': device.temperature2,
            'status': device.status,
            'status_display': device.get_status_display(),
            'update_datetime': device.update_datetime.strftime('%Y-%m-%d %H:%M'),
        })

    context = {
        'devices': devices,
        'devices_json': json.dumps(devices_data, ensure_ascii=False),
        'yandex_maps_api_key': '13827859-458f-45e2-a34c-cb93fa07dda9',  # опционально
    }

    return render(request, 'devices_map.html', context)
