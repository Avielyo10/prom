from .validators import validate_time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Prometheus():
    """
    Represents a Prometheus server we can query
    """

    def __init__(self, host, token):
        self.token = token
        self.host = host
        self._sanitize_host()

    def _sanitize_host(self):
        if self.host.startswith("https://"):
            self.host = self.host[8:]
        if self.host.startswith("api."):
            self.host = self.host[4:]
        if self.host.endswith(":6443"):
            self.host = self.host[:-5]
        if not self.host.startswith("prometheus-k8s-openshift-monitoring.apps"):
            self.host = f"prometheus-k8s-openshift-monitoring.apps.{self.host}"

    def api_for(self, api):
        return f"https://{self.host}/api/v1/{api}"

    def auth_header(self):
        return {'Authorization': f"Bearer {self.token}"}

    def query(self, query, time=None):
        params = {'query': query}
        time = validate_time(time)
        params['time'] = time.isoformat("T") + "Z"
        response = requests.get(self.api_for(
            'query'), headers=self.auth_header(), params=params, verify=False)
        if not response.ok:
            raise RuntimeError(f"Request failed: {response}")
        return [Prometheus.Metric(x) for x in response.json()['data']['result']]

    # Collect a set of metrics with a common function, interval, and time, combining them all into a single list.
    def collect_metrics(self, base_metrics, fn=None, interval=None, time=None):
        time = validate_time(time)
        result = []
        for metric in base_metrics:
            if fn is None:
                query = metric
            else:
                query = fn(metric, interval)
            result += self.query(query, time=time)
        return result


    # Given a dictionary of {fnname: [metric1, metric2]}, re-combobulate into {metric1.name: {fnname: metric1.value, fnname2: metric1.value, ...}}
    @staticmethod
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
    def multicollect(self, metric_set, functions, interval=None, time=None):
        time = validate_time(time)
        return Prometheus.join_metrics({name: self.collect_metrics(metric_set, fn=fn, interval=interval, time=time) for name, fn in functions.items()})


    class Metric():
        """
        Represents a metric result (mildly parsed)
        """

        def __init__(self, json):
            self.json = json
            self.name = {'uniqueId': ':'.join(map(str, json['metric'].values()))}
            self.time = json['value'][0]
            self.value = json['value'][1]

        def __repr__(self):
            return f"{self.name}: {self.value} @{self.time}"


    @staticmethod
    def filtered_metric(base_metric, *filters):
        result = base_metric
        validFilters = list(f for f in filters if f is not None and len(f) > 0)
        if len(validFilters) > 0:
            result += '{' + ",".join(validFilters) + '}'
        return result


    @staticmethod
    def filter_out(labelname, *patterns):
        result = None
        validPatterns = list(p for p in patterns if p is not None and len(p) > 0)
        if len(validPatterns) > 0:
            result = f"{labelname}!~\"{'|'.join(validPatterns)}\""
        return result
