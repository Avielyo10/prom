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

    class Metric():
        """
        Represents a metric result (mildly parsed)
        """

        def __init__(self, json):
            self.json = json
            self.name = json['metric']
            self.time = json['value'][0]
            self.value = json['value'][1]

        def __repr__(self):
            return f"{self.name}: {self.value} @{self.time}"
