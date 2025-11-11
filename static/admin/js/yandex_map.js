document.addEventListener('DOMContentLoaded', function() {
    // Ждем загрузки API Яндекс.Карт
    if (typeof ymaps !== 'undefined') {
        ymaps.ready(initMap);
    } else {
        console.log('Yandex Maps API not loaded');
    }
});

function initMap() {
    // Создаем контейнер для карты
    const mapContainer = document.createElement('div');
    mapContainer.id = 'yandex-map-container';
    mapContainer.style.marginTop = '10px';
    mapContainer.style.marginBottom = '10px';

    const mapElement = document.createElement('div');
    mapElement.id = 'yandex-map';
    mapElement.style.width = '100%';
    mapElement.style.height = '400px';
    mapElement.style.border = '1px solid #ccc';
    mapElement.style.borderRadius = '4px';

    mapContainer.appendChild(mapElement);

    // Находим поле map_latitude и вставляем карту после него
    const latField = document.querySelector('#id_map_latitude').closest('.form-row');
    if (latField) {
        latField.parentNode.insertBefore(mapContainer, latField.nextSibling);
    }

    // Создаем элементы управления
    const controls = document.createElement('div');
    controls.className = 'map-controls';
    controls.innerHTML = `
        <button type="button" id="map-find-address" style="margin-right: 10px; padding: 5px 10px;">Найти по адресу</button>
        <button type="button" id="map-clear" style="margin-right: 10px; padding: 5px 10px;">Убрать метку</button>
        <button type="button" id="map-current" style="padding: 5px 10px;">Текущее местоположение</button>
        <div style="margin-top: 10px; font-family: monospace;">
            <strong>Выбранные координаты:</strong>
            <span id="coordinates-display">Не выбраны</span>
        </div>
    `;

    mapContainer.insertBefore(controls, mapElement);

    // Получаем текущие координаты
    const currentLat = document.getElementById('id_map_latitude').value || document.getElementById('id_latitude').value;
    const currentLon = document.getElementById('id_map_longitude').value || document.getElementById('id_longitude').value;

    // Инициализируем карту
    const map = new ymaps.Map('yandex-map', {
        center: currentLat && currentLon ? [parseFloat(currentLat), parseFloat(currentLon)] : [55.7558, 37.6173],
        zoom: currentLat && currentLon ? 15 : 10,
        controls: ['zoomControl', 'typeSelector']
    });

    let placemark = null;

    // Если есть координаты, ставим метку
    if (currentLat && currentLon) {
        createPlacemark([parseFloat(currentLat), parseFloat(currentLon)]);
        updateCoordinates([parseFloat(currentLat), parseFloat(currentLon)]);
    }

    // Обработчик клика по карте
    map.events.add('click', function(e) {
        const coords = e.get('coords');
        createPlacemark(coords);
        updateCoordinates(coords);
    });

    // Кнопка "Найти по адресу"
    document.getElementById('map-find-address').addEventListener('click', function() {
        const address = prompt('Введите адрес для поиска:');
        if (address) {
            ymaps.geocode(address).then(function(res) {
                const firstGeoObject = res.geoObjects.get(0);
                if (firstGeoObject) {
                    const coords = firstGeoObject.geometry.getCoordinates();
                    map.setCenter(coords, 15);
                    createPlacemark(coords);
                    updateCoordinates(coords);
                } else {
                    alert('Адрес не найден');
                }
            });
        }
    });

    // Кнопка "Убрать метку"
    document.getElementById('map-clear').addEventListener('click', function() {
        if (placemark) {
            map.geoObjects.remove(placemark);
            placemark = null;
        }
        document.getElementById('id_map_latitude').value = '';
        document.getElementById('id_map_longitude').value = '';
        document.getElementById('id_latitude').value = '';
        document.getElementById('id_longitude').value = '';
        document.getElementById('coordinates-display').textContent = 'Не выбраны';
    });

    // Кнопка "Текущее местоположение"
    document.getElementById('map-current').addEventListener('click', function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const coords = [position.coords.latitude, position.coords.longitude];
                map.setCenter(coords, 15);
                createPlacemark(coords);
                updateCoordinates(coords);
            }, function(error) {
                alert('Не удалось получить местоположение: ' + error.message);
            });
        } else {
            alert('Геолокация не поддерживается вашим браузером');
        }
    });

    function createPlacemark(coords) {
        // Удаляем старую метку
        if (placemark) {
            map.geoObjects.remove(placemark);
        }

        // Создаем новую метку
        placemark = new ymaps.Placemark(coords, {
            hintContent: 'Местоположение устройства',
            balloonContent: 'Выбранное местоположение'
        }, {
            preset: 'islands#redIcon',
            draggable: true
        });

        map.geoObjects.add(placemark);

        // При перемещении метки обновляем координаты
        placemark.events.add('dragend', function() {
            const newCoords = placemark.geometry.getCoordinates();
            updateCoordinates(newCoords);
        });
    }

    function updateCoordinates(coords) {
        document.getElementById('id_map_latitude').value = coords[0].toFixed(6);
        document.getElementById('id_map_longitude').value = coords[1].toFixed(6);
        document.getElementById('id_latitude').value = coords[0].toFixed(6);
        document.getElementById('id_longitude').value = coords[1].toFixed(6);
        document.getElementById('coordinates-display').textContent =
            `Широта: ${coords[0].toFixed(6)}, Долгота: ${coords[1].toFixed(6)}`;
    }
}