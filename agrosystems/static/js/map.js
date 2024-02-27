var map = L.map('map', {
    center: [
        51.505, -0.09
    ],
    zoom: 13,
    maxZoom: 100, // Устанавливаем очень высокое значение для maxZoom
});

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {}).addTo(map);

function populateSidebar(objects) {
    var list = document.getElementById('object-list');
    list.innerHTML = ''; // Очистить список перед заполнением

    var groupedObjects = {};
    objects.forEach(function(detail) {
        if (detail.class_name === "Gryadka") {
            return;
        }
        if (!groupedObjects[detail.class_name]) {
            groupedObjects[detail.class_name] = [];
        }
        groupedObjects[detail.class_name].push(detail);
    });

    for (var title in groupedObjects) {
        var group = groupedObjects[title];
        var groupItem = document.createElement('div');
        groupItem.className = 'object-group';

        var groupTitle = document.createElement('h4');
        groupTitle.style.cursor = 'pointer';
        groupTitle.onclick = function() {
            toggleGroupVisibility(this.nextElementSibling); // Изменено
        };

        var detailsContainer = document.createElement('div'); // Создаем контейнер для деталей
        detailsContainer.style.display = 'none'; // Изначально скрыт

        group.forEach(function(detail) {
            var item = document.createElement('div');
            var hideButton = document.createElement('button');
            hideButton.innerHTML = 'Hide';
            hideButton.style.padding = '2px 5px';
            hideButton.style.marginLeft = '10px';
            hideButton.style.backgroundColor = '#d9534f';
            hideButton.style.border = 'none';
            hideButton.style.color = 'white';
            hideButton.style.cursor = 'pointer';
            item.className = 'object-detail';
            item.style.padding = '10px';
            item.style.border = '1px solid #ccc';
            item.style.marginBottom = '5px';
            var gpsInfo = document.createElement('p');
            gpsInfo.textContent = `GPS: [${detail.gps_lat}, ${detail.gps_lon}]`;
            gpsInfo.style.cursor = 'pointer';
            item.appendChild(gpsInfo);
            item.appendChild(hideButton);
            detailsContainer.appendChild(item); // Добавляем элемент в контейнер деталей
            var marker = L.marker([detail.gps_lat, detail.gps_lon]).addTo(map);
            marker.bindPopup(`<b>${detail.class_name}</b><br>Track ID: ${detail.track_id}`);
            item.marker = marker;
            item.isVisible = true;
            gpsInfo.onclick = function(event) {
                var marker = item.marker;
                map.setView(marker.getLatLng(), 30);
            }
            hideButton.onclick = function(event) {
                event.stopPropagation(); // Предотвращаем всплытие события, чтобы не срабатывал обработчик item.onclick
                toggleObjectsVisibility(detail.class_name, hideButton);
            };
        });
        
        groupItem.appendChild(groupTitle);
        groupItem.appendChild(detailsContainer); // Добавляем контейнер деталей в элемент группы
        list.appendChild(groupItem);
        groupTitle.textContent = `${title} (${group.length})`;
    }
}

// Функция для скрытия/показа группы объектов
function toggleGroupVisibility(detailsContainer) {
    if (detailsContainer.style.display === 'none') {
        detailsContainer.style.display = 'block';
    } else {
        detailsContainer.style.display = 'none';
    }
}


function toggleObjectsVisibility(title) {
    var groups = document.getElementsByClassName('object-group');
    for (var i = 0; i < groups.length; i++) {
        var group = groups[i];
        var groupTitle = group.getElementsByTagName('h4')[0].textContent;
        var groupName = groupTitle.split(' (')[0];
        if (groupName === title) {
            var items = group.getElementsByClassName('object-detail');
            for (var j = 0; j < items.length; j++) {
                var item = items[j];
                var marker = item.marker; // Получаем маркер, связанный с элементом
                var hideButton = item.getElementsByTagName('button')[0]; // Получаем кнопку
                if (item.isVisible) {
                    marker.remove(); // Скрыть маркер
                    hideButton.textContent = 'Show'; // Изменить текст кнопки на "Show"
                } else {
                    marker.addTo(map); // Показать маркер
                    hideButton.textContent = 'Hide'; // Изменить текст кнопки на "Hide"
                }
                item.isVisible = !item.isVisible; // Инвертировать состояние видимости
            }
        }
    }
}


function addGeoTIFFToMapAndCalculateFieldInfo(geoTIFFUrl, map) {
    fetch(geoTIFFUrl).then(response => response.arrayBuffer()).then(arrayBuffer => {
        parseGeoraster(arrayBuffer).then(georaster => {
            const pixelValuesToColorFn = values => {
                if (values[0] === 0 && values[1] === 0 && values[2] === 0) {
                    return 'rgba(0, 0, 0, 0)'; // Полностью прозрачный
                } else {
                    return `rgb(${values[0]}, ${values[1]}, ${values[2]})`;
                }
            };

            const layer = new GeoRasterLayer({
                georaster: georaster,
                pixelValuesToColorFn: pixelValuesToColorFn,
                resolution: 64 // adjust according to your needs
            });
            layer.addTo(map);

            // Zoom to the bounds of the raster layer
            map.fitBounds(layer.getBounds());

            // Автоматическое определение UTM зоны
            const centralLongitude = (georaster.xmin + georaster.xmax) / 2;
            const utmZone = Math.floor((centralLongitude + 180) / 6) + 1;
            const utmProjection = `+proj=utm +zone=${utmZone} +datum=WGS84 +units=m +no_defs`;

            // Подсчет пустых пикселей
            let emptyPixelCount = 0;
            for (let i = 0; i < georaster.values[0].length; i++) {
                if (georaster.values[0][i] === georaster.noDataValue) {
                    emptyPixelCount++;
                }
            }

            // Преобразование координат границ в UTM
            const [xmin, ymin] = proj4("EPSG:4326", utmProjection, [georaster.xmin, georaster.ymin]);
            const [xmax, ymax] = proj4("EPSG:4326", utmProjection, [georaster.xmax, georaster.ymax]);

            // Рассчитайте размеры и площадь поля в метрах, исключая пустые пиксели
            const totalPixelCount = georaster.width * georaster.height;
            const validPixelCount = totalPixelCount - emptyPixelCount;
            const widthInMeters = Math.abs(xmax - xmin);
            const heightInMeters = Math.abs(ymax - ymin);
            const areaInSquareMeters = validPixelCount * (widthInMeters * heightInMeters / totalPixelCount);

            // Отобразите информацию о поле
            const infoList = document.getElementById('info-list');
            infoList.innerHTML = `
                <li>Field Area: ${areaInSquareMeters.toFixed(2)} sq.m.</li>
                <li>Field Width: ${widthInMeters.toFixed(2)} m</li>
                <li>Field Height: ${heightInMeters.toFixed(2)} m</li>
            `;
        });
    });
}


// Вызов функции для заполнения боковой панели
populateSidebar(objectDetails);
addGeoTIFFToMapAndCalculateFieldInfo(geoTIFFUrl, map);
