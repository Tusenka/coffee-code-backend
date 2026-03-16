import functools
import time

from agent.metrics.config import get_meter

_meter = get_meter("agent")
cache_histogramms = {}


def perf(name=None):
    """
    Декоратор для замера времени работы функции в секундах. По замерам составляется гистограмма.
    """

    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            histo_name = name or func.__name__
            if name not in cache_histogramms:
                cache_histogramms[histo_name] = _meter.create_counter(
                    name=name,
                    description=f"Длительность работы {name} в секундах.",
                    unit="s",
                )

            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            cache_histogramms[histo_name].add(duration)

            return result

        return wrapper

    return actual_decorator
