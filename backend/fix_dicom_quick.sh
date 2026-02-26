#!/bin/bash
# Быстрое исправление для проблемы с DICOM ориентацией

echo "🔧 Исправляю DICOM файлы..."

# Находим последнюю задачу
LATEST_JOB=$(ls -t /root/laprascope/data/jobs/ | head -1)

if [ -z "$LATEST_JOB" ]; then
    echo "❌ Не найдено задач"
    exit 1
fi

echo "📁 Найдена задача: $LATEST_JOB"

# Проверяем наличие DICOM файлов
DICOM_DIR="/root/laprascope/data/jobs/$LATEST_JOB/dicom_organized"
if [ ! -d "$DICOM_DIR" ]; then
    echo "❌ DICOM директория не найдена: $DICOM_DIR"
    exit 1
fi

# Создаем исправленную версию
FIXED_DIR="/root/laprascope/data/jobs/$LATEST_JOB/dicom_fixed"
mkdir -p "$FIXED_DIR"

# Копируем только первые 50 файлов (самый надежный способ)
echo "📋 Копирую первые 50 DICOM файлов..."
find "$DICOM_DIR" -name "*.dcm" | head -50 | xargs -I {} cp {} "$FIXED_DIR/"

FILE_COUNT=$(ls "$FIXED_DIR"/*.dcm 2>/dev/null | wc -l)
echo "✅ Скопировано файлов: $FILE_COUNT"

if [ $FILE_COUNT -ge 10 ]; then
    echo "🎯 Создаю символическую ссылку для использования исправленных файлов"
    
    # Удаляем старую предобработанную директорию если есть
    rm -rf "/root/laprascope/data/jobs/$LATEST_JOB/dicom_preprocessed"
    
    # Создаем символическую ссылку
    ln -sf "$FIXED_DIR" "/root/laprascope/data/jobs/$LATEST_JOB/dicom_preprocessed"
    
    echo "✅ Готово! Теперь можно перезапустить обработку задачи"
    echo "🔄 Команда для перезапуска:"
    echo "curl -X POST http://localhost:8000/api/v1/restart/$LATEST_JOB"
else
    echo "❌ Слишком мало файлов для обработки"
    exit 1
fi
