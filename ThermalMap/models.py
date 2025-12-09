from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class DeviceStatus(models.Model):
    # Статусы устройств (можно расширить по необходимости)
    STATUS_CHOICES = [
        (0, 'Отключено (нет питания)'),
        (1, 'ОК'),
        (2, 'Перегрев датчик 1'),
        (3, 'Перегрев датчик 2'),
        (4, 'Включено (питание подано)')
    ]

    name = models.CharField(
        max_length=255,
        verbose_name='Имя устройства',
        unique=True  # если имена должны быть уникальными
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='Номер телефона',
        blank=True,
        null=True
    )
    temperature1 = models.FloatField(
        verbose_name='Температура 1',
        blank=True,
        null=True
    )
    temperature2 = models.FloatField(
        verbose_name='Температура 2',
        blank=True,
        null=True
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        verbose_name='Статус',
        default=0
    )

    # Географические координаты
    latitude = models.FloatField(
        verbose_name='Широта',
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        blank=True,
        null=True,
        help_text='Широта в градусах от -90 до 90'
    )
    longitude = models.FloatField(
        verbose_name='Долгота',
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        blank=True,
        null=True,
        help_text='Долгота в градусах от -180 до 180'
    )

    update_datetime = models.DateTimeField(
        verbose_name='Дата и время обновления',
        default=timezone.now
    )

    request_datetime = models.DateTimeField(
        verbose_name='Дата и время запроса',
        default=timezone.now
    )

    class Meta:
        verbose_name = 'Термальное устройство'
        verbose_name_plural = 'Термальные устройства'
        ordering = ['-update_datetime']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['update_datetime']),
        ]

    def __str__(self):
        return f"{self.name} (статус: {self.get_status_display()})"

    @property
    def coordinates(self):
        """Возвращает координаты в формате для Яндекс.Карт"""
        if self.latitude and self.longitude:
            return f"{self.latitude},{self.longitude}"
        return None

    @property
    def has_coordinates(self):
        """Проверяет, есть ли координаты"""
        return self.latitude is not None and self.longitude is not None

    def get_yandex_map_url(self):
        """Генерирует URL для Яндекс.Карт"""
        if self.has_coordinates:
            return f"https://yandex.ru/maps/?pt={self.longitude},{self.latitude}&z=15&l=map"
        return None

    def save(self, *args, **kwargs):
        """Автоматическое обновление времени"""
        if not self.pk:
            self.update_datetime = timezone.now()
            self.request_datetime = timezone.now()
        super().save(*args, **kwargs)
