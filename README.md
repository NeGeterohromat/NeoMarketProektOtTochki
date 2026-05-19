# NeoMarket

## Установка

В директории с requirements.txt установите зависимости приложения командой:

```sh
pip install -r requirements.txt
```

Создайте файл `.env` на основе `.env.example` и пропишите переменные окружения

```
# Пример
DB_NAME=mydatabase
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=localhost
DB_PORT=5432
```

Развернуть PostgreSQL можно из Docker
```sh
docker run --name my-postgres \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_DB=mydatabase \
  -p 5432:5432 \
  -d postgres:16
```

Применение миграций для БД
```sh
python manage.py migrate
```

## Запуск

```sh
python manage.py runserver
```