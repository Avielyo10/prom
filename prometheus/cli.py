"""
prome cli
"""

import click
import os
import sys
import json
import yaml
import pandas as pd
from io import StringIO

from .prometheus import Prometheus


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
@click.option('--filter-out', '-f', type=click.Path(), help="Path to metric set yaml")
def metrics(host, token, interval, time, skip_namespaces, output, filter_out):
    prometheus = Prometheus(host, token)

    metric_set = [
        Prometheus.filtered_metric("namedprocess_namegroup_cpu_rate",
                                   Prometheus.filter_out("groupname", "conmon")),
        Prometheus.filtered_metric("pod:container_cpu_usage:sum",
                                   Prometheus.filter_out(
                                       "podname", "process-exp.*"),
                                   Prometheus.filter_out("namespace", *skip_namespaces))
    ]
    if filter_out:
        metric_set = metric_set + prometheus.get_metrics_from_file(filter_out) 
    combined_metrics = prometheus.multicollect(metric_set, {
        f'avg over {interval}': lambda metric, interval: f"avg_over_time({metric}[{interval}])",
        f'min over {interval}': lambda metric, interval: f"min_over_time({metric}[{interval}])",
        f'max over {interval}': lambda metric, interval: f"max_over_time({metric}[{interval}])",
    }, interval=interval, time=time)

    df = pd.DataFrame(combined_metrics.values())
    df['uniqueId'] = combined_metrics.keys()
    df.set_index('uniqueId', inplace=True)

    if output == 'json':
        df.to_json(sys.stdout, orient='index')
    elif output == 'yaml':
        std = StringIO()
        df.to_json(std, orient='index')
        std.seek(0, os.SEEK_SET)
        print(yaml.dump(json.loads(std.read())))
    else:
        df.to_csv(sys.stdout)
