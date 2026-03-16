# Локально запущенное приложение

## Локальный запуск
```
pip install -r requirements.txt
pip install -r agent_requirements.txt
docker compose -f docker-compose-local.yaml up --remove-orphans
python agent.py
python app.py
```

## Мониторинг и логирование локального запущенного приложения

### Loki
Логи приложения отправляются в Loki (работает на порту 3100). Для отправки логов используется библиотека `python-logging-loki`. Конфигурация находится в `agent/app.py`.

### Визуализация логов (Grafana)
Для просмотра логов добавлен сервис Grafana. После запуска docker-compose Grafana доступна на порту 3000.

- URL: http://localhost:3000
- Логин: `admin`
- Пароль: `admin`

Источник данных Loki предварительно настроен и указывает на `http://loki:3100`. Вы можете создавать дашборды и запросы к логам через интерфейс Grafana.

#### Запуск только Loki и Grafana
```
docker compose -f docker-compose-local.yaml up -d loki grafana
```

#### Проверка логов через CLI
Установите `logcli` (инструмент командной строки Loki) или используйте curl для запросов к API Loki:
```bash
curl -G "http://localhost:3100/loki/api/v1/query" --data-urlencode 'query={application="agent"}'
```

### VictoriaMetrics
Для метрик используется VictoriaMetrics (порт 8428). Метрики собираются через OpenTelemetry и экспортируются в VictoriaMetrics.

#### OpenTelemetry Collector
Для приёма метрик по протоколу OTLP (gRPC/HTTP) используется OpenTelemetry Collector, который работает как промежуточный сервис. Collector принимает метрики на портах 4317 (gRPC) и 4318 (HTTP), преобразует их в формат Prometheus remote write и отправляет в VictoriaMetrics.

Конфигурация Collector находится в файле `otel-collector-config.yaml`. В docker-compose-local.yaml добавлен сервис `otel-collector`.

#### Проверка метрик
После запуска всех сервисов метрики можно запросить через API VictoriaMetrics:

```bash
curl "http://localhost:8428/api/v1/query?query=agent_users_processed_total"
```

Или через веб-интерфейс Grafana, используя источник данных Prometheus (уже настроен на `http://victoriametrics:8428`).