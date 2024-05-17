
FROM python:3.12-slim

ENV APP_DIR /application

# Завдання робочої директорії в контейнері
WORKDIR $APP_DIR

# Копіювання файлів залежностей і встановлення залежностей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання всього іншого в робочу директорію
COPY . .

EXPOSE 8000

# Запуск програми при старті контейнера
CMD [ "python", "main.py" ]