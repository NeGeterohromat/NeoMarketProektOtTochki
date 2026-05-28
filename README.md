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
MODERATION_URL=http://127.0.0.1:8080
B2C_URL=http://127.0.0.1:8080
SERVICE_TOKEN=<X-Service-Key>
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
### Запуск дебаг сервера:
```sh
python manage.py runserver
```

### Запуск тестов:

Через django test:
```sh
# все тесты:
python manage.py test

# определённый класс тестов:
python manage.py test <app_name>.tests.<TestCaseClassName>
```

Через pytest:
```sh
# все тесты:
pytest

# определённый класс тестов:
pytest <app_name>/tests.py::<TestCaseClassName>
```