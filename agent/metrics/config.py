import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def init_loki():
    # Add Loki logging for errors if LOKI_ENDPOINT is set
    loki_endpoint = os.getenv("LOKI_ENDPOINT", "http://localhost:3100")
    try:
        from logging_loki import LokiHandler

        loki_handler = LokiHandler(
            url=f"{loki_endpoint}/loki/api/v1/push",
            tags={"application": "agent"},
            version="1",
        )
        loki_handler.setLevel(logging.WARNING)
        # Add to root logger to capture all logs
        root_logger = logging.getLogger()
        # Avoid duplicate handlers
        for handler in root_logger.handlers:
            if isinstance(handler, LokiHandler):
                root_logger.removeHandler(handler)
        root_logger.addHandler(loki_handler)
        logger.warning("Логирование через Loki доступно по адресу %s.", loki_endpoint)
    except ImportError:
        logger.error(
            "Пакет logging_loki не установлен. Логирование через Loki отключено."
        )
    except Exception as e:
        logger.error("Ошибка настройки Loki.\n%s", e)


def init_metrics():
    """
    Инициализация сбора метрик OpenTelemetry через протокол OpenTelemetry (OTLP).
    Требуется переменная окружения `OTEL_EXPORTER_OTLP_ENDPOINT`.
    """

    resource = Resource.create(
        attributes={
            "service.name": "agent",
            "service.version": "1.0.0",
        }
    )

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    l = []
    readers = l

    if otlp_endpoint:
        logger.debug(
            "Экспорт метрик осуществляется OTLP-экспортёром (OTLPMetricExporter) по адресу %s.",
            otlp_endpoint,
        )
        otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        readers.append(
            PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=10000)
        )
    else:
        logger.error(
            "Переменная окружения OTEL_EXPORTER_OTLP_ENDPOINT не установлена. Метрики будут экспортироваться на консоль."
        )

    if not readers:
        logger.info(
            "OTLP-экспортёр (OTLPMetricExporter) не настроен. Используется экспортёр с выводом на консоль (ConsoleMetricExporter)."
        )
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

        readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))

    meter_provider = MeterProvider(
        metric_readers=readers,
        resource=resource,
    )
    metrics.set_meter_provider(meter_provider)

    return meter_provider


def get_meter(name="agent"):
    return metrics.get_meter(name)


def init_tracing():
    """
    Инициализация трассировки OpenTelemetry через OTLP-экспортёр.
    Требуется переменная окружения `OTEL_EXPORTER_OTLP_ENDPOINT`.
    """

    resource = Resource.create(
        attributes={
            "service.name": "agent",
            "service.version": "1.0.0",
        }
    )

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    tracer_provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        logger.info(
            "Экспорт трассировок осуществляется OTLP-экспортёром (OTLPSpanExporter) по адресу %s.",
            otlp_endpoint,
        )
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
    else:
        logger.info(
            "OTLP-экспортёр (OTLPSpanExporter) не настроен. Используется экспортёр с выводом на консоль (ConsoleSpanExporter)."
        )
        span_processor = BatchSpanProcessor(ConsoleSpanExporter())

    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider


def get_tracer(name="agent"):
    return trace.get_tracer(name)
