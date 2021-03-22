"""
prome cli
"""

import click
import sys
import json
import yaml
import pandas as pd
from io import StringIO

from .prometheus import Prometheus
from .util import *


@click.group()
@click.version_option()
def main():
    """
    Main click group for future commands
    """
    pass


@main.command(help="""
Compute the average, min, and max values over the given interval ending at the given timestamp

If not specified, interval defaults to 1h and timestamp defaults to now

By default, skips any pod named "process-exp.*" to exclude the process-exporter itself
Adding additional skip_namespaces will also exclude any pods that match from the pod CPU usage accounting, so we can exclude workloads if required
""")
@click.option('--host', '-h', required=True, type=str, help="Prometheus host, try \
`oc get route prometheus-k8s -n openshift-monitoring -o jsonpath='{.status.ingress[0].host}'`")
@click.option('--token', '-t', required=True, type=str, help="Token for authentication, try `oc whoami -t`")
@click.option('--interval', '-i', type=str, default="1h", show_default=True, help="")
@click.option('--time', '-T', default=None, help="")
@click.option('--skip-namespaces', '-s', default=None, multiple=True, show_default=True)
@click.option('--output', '-o', type=click.Choice(['csv', 'json', 'yaml']), default='csv')
def metrics(host, token, interval, time, skip_namespaces, output):
    prometheus = Prometheus(host, token)

    metric_set = [
        filtered_metric("namedprocess_namegroup_cpu_rate",
                        filter_out("groupname", "conmon")),
        filtered_metric("pod:container_cpu_usage:sum", filter_out(
            "podname", "process-exp.*"), filter_out("namespace", *skip_namespaces))
    ]
    combined_metrics = multicollect(prometheus, metric_set, {
        f'avg over {interval}': lambda metric, interval: f"avg_over_time({metric}[{interval}])",
        f'min over {interval}': lambda metric, interval: f"min_over_time({metric}[{interval}])",
        f'max over {interval}': lambda metric, interval: f"max_over_time({metric}[{interval}])",
    }, interval=interval, time=time)

    keys = list(json.loads(d.replace('\'', '\"'))
                for d in combined_metrics.keys())
    keys_df = pd.DataFrame(keys)
    values_df = pd.DataFrame(combined_metrics.values())
    df = keys_df.join(values_df)

    if output is 'json':
        df.to_json(sys.stdout, orient='index')
    elif output is 'yaml':
        sys.stdout = StringIO()
        y = yaml.load(df.to_json(sys.stdout), Loader=yaml.FullLoader)
        sys.stdout = sys.__stdout__
        print(y)
    else:
        df.to_csv(sys.stdout)
