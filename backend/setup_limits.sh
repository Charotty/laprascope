#!/bin/bash
# Скрипт для увеличения лимитов загрузки файлов

echo "🔧 Настраиваю лимиты для больших файлов..."

# 1. Увеличиваем лимит в nginx
if [ -f /etc/nginx/sites-available/laprascope ]; then
    echo "📝 Обновляю nginx конфигурацию..."
    sudo sed -i 's/client_max_body_size 100M;/client_max_body_size 2048M;/' /etc/nginx/sites-available/laprascope
    sudo nginx -t && sudo systemctl reload nginx
    echo "✅ Nginx обновлен"
fi

# 2. Увеличиваем системные лимиты
echo "📝 Обновляю системные лимиты..."
echo "root soft nofile 65536" >> /etc/security/limits.conf
echo "root hard nofile 65536" >> /etc/security/limits.conf

# 3. Настраиваем параметры ядра
echo "📝 Обновляю параметры ядра..."
echo "fs.file-max = 2097152" >> /etc/sysctl.conf
sysctl -p

echo "✅ Лимиты увеличены!"
echo "💡 Новый лимит: 2GB (2048MB)"
echo "🔄 Перезапусти сервер: python quick_start.py"
