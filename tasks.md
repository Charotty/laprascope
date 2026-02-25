# 🏥 AR Laparoscopy Project — Production Plan

## 📋 Блок 1. Инфраструктура и окружение

### Подблок 1.1. Подготовка системы
**Задачи:**
- [x] Установить Python 3.10+ (рекомендуется 3.11)
- [x] Установить CUDA 11.8 или 12.1
- [x] Проверить `nvidia-smi` и версию драйвера
- [x] Создать venv: `python -m venv venv`
- [x] Активировать: `source venv/bin/activate` (Linux) или `venv\Scripts\activate` (Windows)
- [x] Установить PyTorch с CUDA: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
- [x] Проверить: `python -c "import torch; print(torch.cuda.is_available())"`

### Подблок 1.2. ML-инструментарий
**Задачи:**
- [x] Установить TotalSegmentator v2: `pip install TotalSegmentator`
- [x] Проверить CLI: `totalsegmentator --help`
- [x] Скачать тестовый DICOM dataset (например, с KiTS19 sample)
- [x] Прогнать вручную: `totalsegmentator -i input/ -o output/ --roi_subset kidney_left kidney_right --fast`
- [x] Замерить время (ожидается 20-40 сек на --fast)
- [x] Проверить наличие файлов: `kidney_left.nii.gz`, `kidney_right.nii.gz`

### Подблок 1.3. Геометрическая обработка
**Задачи:**
- [x] Установить: `pip install nibabel scikit-image trimesh`
- [x] Написать функцию `nifti_to_stl(nifti_path, stl_path, target_faces=50000)`
- [x] Использовать `skimage.measure.marching_cubes` для mesh extraction
- [x] Добавить `trimesh.smoothing.filter_laplacian` для сглаживания
- [x] Добавить `mesh.simplify_quadric_decimation()` до 50-100k треугольников
- [x] Проверить STL в MeshLab или любом viewer
- [x] Проверить размер файла (должен быть 2-5 МБ)

---

## 📦 Блок 2. Архитектура Backend

### Подблок 2.1. Структура проекта
**Задачи:**
- [x] Создать структуру (см. ниже)
- [x] Добавить `config.py` с путями
- [x] Создать `.gitignore` (исключить venv, jobs/, __pycache__)
- [x] Инициализировать git

**Структура:**
```
ar-laparoscopy-project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py        # POST /upload
│   │   │   ├── status.py        # GET /status/{job_id}
│   │   │   └── download.py      # GET /stl/{job_id}/{organ}
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── segmentation.py  # TotalSegmentator wrapper
│   │   │   ├── conversion.py    # NIfTI → STL
│   │   │   └── pipeline.py      # Orchestrator
│   │   └── models/
│   │       ├── __init__.py
│   │       └── job.py           # Job status enum
│   ├── data/
│   │   └── jobs/
│   │       └── {job_id}/
│   │           ├── status.json
│   │           ├── dicom/
│   │           ├── nifti/
│   │           └── stl/
│   ├── config.py
│   ├── requirements.txt
│   └── run.sh                   # Startup script
├── unity/
│   └── ARLaparoscopy/
│       ├── Assets/
│       │   ├── Scripts/
│       │   │   ├── NetworkManager.cs
│       │   │   ├── ModelLoader.cs
│       │   │   └── UIController.cs
│       │   ├── Materials/
│       │   ├── Scenes/
│       │   └── Plugins/         # TriLib
│       └── Packages/
├── docs/
│   ├── architecture.md
│   └── api_spec.md
└── README.md
```

### Подблок 2.2. Модуль сегментации
**Файл:** `backend/app/services/segmentation.py`

**Задачи:**
- [x] Функция `segment_kidneys(job_id: str) -> dict`
- [x] Вызов: `subprocess.run(['totalsegmentator', ...])`
- [x] Обработка ошибок (CUDA OOM, invalid DICOM)
- [x] Логирование с `logging.info()`
- [x] Возврат: `{'kidney_left': 'path/to/left.nii.gz', 'kidney_right': '...'}`

### Подблок 2.3. Модуль конвертации
**Файл:** `backend/app/services/conversion.py`

**Задачи:**
- [x] Функция `convert_to_stl(nifti_path: str, stl_path: str, simplify: int = 50000)`
- [x] Чтение NIfTI: `nib.load(nifti_path).get_fdata()`
- [x] Marching cubes: `measure.marching_cubes(volume, level=0.5)`
- [x] Создание mesh: `trimesh.Trimesh(vertices, faces)`
- [x] Упрощение: `mesh.simplify_quadric_decimation(simplify)`
- [x] Сохранение: `mesh.export(stl_path)`
- [x] Возврат: путь к STL

### Подблок 2.4. Оркестратор pipeline
**Файл:** `backend/app/services/pipeline.py`

**Задачи:**
- [x] Функция `run_pipeline(job_id: str)`
- [x] Шаг 1: Обновить статус → `processing`
- [x] Шаг 2: Вызвать `segment_kidneys(job_id)`
- [x] Шаг 3: Для каждой почки вызвать `convert_to_stl()`
- [x] Шаг 4: Обновить статус → `done` или `error`
- [x] Логирование времени каждого шага
- [x] Обработка исключений с сохранением traceback

---

## 🌐 Блок 3. API слой

### Подблок 3.1. Upload
**Файл:** `backend/app/api/upload.py`

**Задачи:**
- [x] `@router.post("/upload")`
- [x] Принять `UploadFile` (zip с DICOM)
- [x] Генерировать `job_id = uuid.uuid4().hex`
- [x] Создать папки: `data/jobs/{job_id}/dicom/`
- [x] Распаковать zip: `zipfile.ZipFile()`
- [x] Создать `status.json`: `{"status": "queued", "created_at": "..."}`
- [x] Запустить `background_tasks.add_task(run_pipeline, job_id)`
- [x] Вернуть: `{"job_id": "...", "status": "queued"}`

### Подблок 3.2. Статус
**Файл:** `backend/app/api/status.py`

**Задачи:**
- [x] `@router.get("/status/{job_id}")`
- [x] Прочитать `data/jobs/{job_id}/status.json`
- [x] Вернуть: `{"job_id": "...", "status": "processing", "progress": 50}`
- [x] Если job_id не найден → 404

### Подблок 3.3. Получение STL
**Файл:** `backend/app/api/download.py`

**Задачи:**
- [ ] `@router.get("/stl/{job_id}/{organ}")`
- [ ] `organ` in ['kidney_left', 'kidney_right']
- [ ] Проверить существование файла
- [ ] Вернуть: `FileResponse(path, media_type="model/stl")`
- [ ] Добавить заголовок `Content-Disposition: attachment`

### Подблок 3.4. Обработка ошибок
**Задачи:**
- [ ] Добавить exception handler для CUDA OOM
- [ ] Добавить exception handler для invalid DICOM
- [ ] Логировать в файл: `logs/app.log`
- [ ] Возвращать понятные JSON ошибки

---

## 🚀 Блок 4. Подготовка к развертыванию

### Подблок 4.1. Зависимости
**Файл:** `backend/requirements.txt`

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
TotalSegmentator==2.0.5
torch==2.1.2
torchvision==0.16.2
nibabel==5.2.0
scikit-image==0.22.0
trimesh==4.0.10
numpy==1.24.3
```

**Задачи:**
- [ ] Создать файл
- [ ] Протестировать установку: `pip install -r requirements.txt`

### Подблок 4.2. Конфигурация
**Файл:** `backend/config.py`

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "jobs"
LOGS_DIR = BASE_DIR / "logs"

# Segmentation
FAST_MODE = True
ROI_SUBSET = ["kidney_left", "kidney_right"]

# Conversion
TARGET_FACES = 50000
SMOOTHING_ITERATIONS = 3

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
```

### Подблок 4.3. GPU-проверка
**Файл:** `backend/app/main.py` (в startup event)

**Задачи:**
- [ ] Проверить `torch.cuda.is_available()`
- [ ] Логировать GPU name: `torch.cuda.get_device_name(0)`
- [ ] Логировать VRAM: `torch.cuda.get_device_properties(0).total_memory`
- [ ] Если GPU нет → warning, но не падать

---

## 🎮 Блок 5. Unity интеграция

### Подблок 5.1. Сетевой слой
**Файл:** `unity/Assets/Scripts/NetworkManager.cs`

**Задачи:**
- [ ] Метод `UploadDICOM(byte[] zipData)` → POST /upload
- [ ] Использовать `UnityWebRequest.Post()`
- [ ] Парсить JSON ответ для получения job_id
- [ ] Метод `CheckStatus(string jobId)` → GET /status/{job_id}
- [ ] Polling каждые 2 секунды
- [ ] Метод `DownloadSTL(string jobId, string organ)` → GET /stl/{job_id}/{organ}

### Подблок 5.2. Загрузка модели
**Файл:** `unity/Assets/Scripts/ModelLoader.cs`

**Задачи:**
- [ ] Установить TriLib 2 из Asset Store
- [ ] Метод `LoadSTL(byte[] stlData)`
- [ ] Создать временный файл: `Path.GetTempFileName() + ".stl"`
- [ ] Загрузить через TriLib: `AssetLoader.LoadModelFromFile(path)`
- [ ] Удалить временный файл
- [ ] Вернуть GameObject

### Подблок 5.3. Визуализация
**Файл:** `unity/Assets/Scripts/VisualizationController.cs`

**Задачи:**
- [ ] Создать Material с shader Standard (или AR-specific)
- [ ] Применить к загруженной модели
- [ ] Добавить компонент для вращения (mouse drag)
- [ ] Добавить pinch-to-zoom для AR
- [ ] Проверить FPS на target device (должно быть 60+)

---

## 🎬 Блок 6. Демонстрационный сценарий

### Подблок 6.1. Demo flow
**Задачи:**
- [ ] UI: кнопка "Upload DICOM"
- [ ] Выбрать zip файл
- [ ] Показать loading indicator
- [ ] Отобразить статус: "Segmenting... 50%"
- [ ] При завершении: появление 3D почки в AR
- [ ] Возможность вращения/масштабирования
- [ ] Кнопка "Screenshot" → сохранить результат

### Подблок 6.2. Защита проекта
**Задачи:**
- [ ] Нарисовать схему архитектуры (draw.io или Miro)
- [ ] Подготовить слайды с объяснением pipeline
- [ ] Сравнительная таблица: TotalSegmentator vs кастомная модель
- [ ] Таблица времени: локально (GPU) vs сервер (CPU) vs сервер (GPU)
- [ ] Демо видео 2-3 минуты

---

## 🚫 Блок 7. Что НЕ делать (экономия времени)

- [ ] ❌ **Не обучать свою модель** — используй TotalSegmentator
- [ ] ❌ **Не качать весь KiTS dataset** — достаточно 1-2 samples для теста
- [ ] ❌ **Не писать распределённую систему** — один сервер достаточен
- [ ] ❌ **Не оптимизировать преждевременно** — сначала работающий MVP
- [ ] ❌ **Не добавлять аутентификацию** — это demo, не production
- [ ] ❌ **Не делать web UI** — фокус на Unity
- [ ] ❌ **Не поддерживать все органы** — только почки

---

## 📅 Рекомендуемый timeline (3 дня)

### День 1: Backend + ML
- [ ] Часы 1-2: Настройка окружения, установка всего
- [ ] Часы 3-5: Тест TotalSegmentator на sample DICOM
- [ ] Часы 6-8: Написать conversion.py (NIfTI → STL)

### День 2: API + интеграция
- [ ] Часы 1-4: FastAPI endpoints (upload, status, download)
- [ ] Часы 5-6: Тестирование через curl/Postman
- [ ] Часы 7-8: Unity networking (upload + download)

### День 3: Визуализация + demo
- [ ] Часы 1-3: TriLib загрузка в Unity
- [ ] Часы 4-5: AR placement и взаимодействие
- [ ] Часы 6-8: Полировка UI, запись demo видео

---

## ✅ Чек-лист готовности

**К концу Дня 1:**
- [ ] TotalSegmentator работает локально
- [ ] Есть функция NIfTI → STL
- [ ] Один тестовый STL файл открывается в viewer

**К концу Дня 2:**
- [ ] API принимает zip, возвращает job_id
- [ ] Можно скачать STL через curl
- [ ] Unity может загрузить файл с локального диска

**К концу Дня 3:**
- [ ] Unity загружает модель с сервера
- [ ] Модель отображается в AR
- [ ] Можно показать на защите

---
