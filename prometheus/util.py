from .validators import validate_time


# Collect a set of metrics with a common function, interval, and time, combining them all into a single list.
def collect_metrics(prometheus, base_metrics, fn=None, interval=None, time=None):
    time = validate_time(time)
    result = []
    for metric in base_metrics:
        if fn is None:
            query = metric
        else:
            query = fn(metric, interval)
        result += prometheus.query(query, time=time)
    return result


# Given a dictionary of {fnname: [metric1, metric2]}, re-combobulate into {metric1.name: {fnname: metric1.value, fnname2: metric1.value, ...}}
def join_metrics(metric_sets):
    result = {}
    for setname, metrics in metric_sets.items():
        for m in metrics:
            metricname = repr(m.name)
            if metricname not in result:
                result[metricname] = {}
            result[metricname][setname] = m.value
    return result


# Collect a matrix of results for a common interval and time, and join them into a single dictionary of {metric-name: {fnname: value, fnname2: value2, ...}}
def multicollect(prometheus, metric_set, functions, interval=None, time=None):
    time = validate_time(time)
    return join_metrics({name: collect_metrics(prometheus, metric_set, fn=fn, interval=interval, time=time) for name, fn in functions.items()})


def filtered_metric(base_metric, *filters):
    result = base_metric
    validFilters = list(f for f in filters if f is not None and len(f) > 0)
    if len(validFilters) > 0:
        result += '{' + ",".join(validFilters) + '}'
    return result


def filter_out(labelname, *patterns):
    result = None
    validPatterns = list(p for p in patterns if p is not None and len(p) > 0)
    if len(validPatterns) > 0:
        result = f"{labelname}!~\"{'|'.join(validPatterns)}\""
    return result
