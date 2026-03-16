"""
Инструменты OpenTelemetry для сбора измерений, или метрик, агентом.
"""

from agent.metrics.config import get_meter

_meter = get_meter("agent")

# Счётчики
matches_generated_counter = _meter.create_counter(
    name="agent_matches_generated_total",
    description="Количество всех созданных агентом паросочетаний.",
    unit="1",
)

errors_counter = _meter.create_counter(
    name="agent_errors_total",
    description="Количество ошибок при работе агента.",
    unit="1",
)

users_processed_counter = _meter.create_counter(
    name="agent_users_processed_total",
    description="Количество всех пользователей, для которых агент создал паросочетание.",
    unit="1",
)

video_requests_counter = _meter.create_counter(
    name="agent_video_requests_total",
    description="Количество всех запросов к Яндексу на создание видеозвонка.",
    unit="1",
)


def record_match_generated(strict: bool = True):
    """Фиксация увеличения количества созданных агентом паросочетаний."""
    matches_generated_counter.add(1, {"strict": str(strict).lower()})


def record_error(error_type: str = "unknown"):
    """Фиксация ошибки при работе агента."""
    errors_counter.add(1, {"error_type": error_type})


def record_user_processed():
    """Фиксация увеличения количества пользователей, для которых агент создал паросочетание."""
    users_processed_counter.add(1)


def record_video_request():
    """Фиксация увеличения количества запросов к Яндексу на создание видеозвонка."""
    video_requests_counter.add(1)
