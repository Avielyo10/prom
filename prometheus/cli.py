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

import openshift as oc

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
@click.option('--skip-namespaces', '-S', default=None, multiple=True, show_default=True)
@click.option('--output', '-o', type=click.Choice(['csv', 'json', 'yaml']), default='csv')
@click.option('--sort-by', '-s', type=click.Choice(['min', 'max', 'avg']), default=None)
def metrics(host, token, interval, time, skip_namespaces, output, sort_by):
    prometheus = Prometheus(host, token)

    metric_set = [
        Prometheus.filtered_metric("namedprocess_namegroup_cpu_rate",
                                   Prometheus.filter_out("groupname", "conmon")),
        Prometheus.filtered_metric("pod:container_cpu_usage:sum",
                                   Prometheus.filter_out(
                                       "podname", "process-exp.*"),
                                   Prometheus.filter_out("namespace", *skip_namespaces))
    ]
    combined_metrics = prometheus.multicollect(metric_set, {
        f'avg over {interval}': lambda metric, interval: f"avg_over_time({metric}[{interval}])",
        f'min over {interval}': lambda metric, interval: f"min_over_time({metric}[{interval}])",
        f'max over {interval}': lambda metric, interval: f"max_over_time({metric}[{interval}])",
    }, interval=interval, time=time)

    df = pd.DataFrame(combined_metrics.values())
    df['uniqueId'] = combined_metrics.keys()
    df.set_index('uniqueId', inplace=True)

    if sort_by is not None:
        df.sort_values(by=f'{sort_by} over {interval}', inplace=True)

    if output == 'json':
        df.to_json(sys.stdout, orient='index')
    elif output == 'yaml':
        std = StringIO()
        df.to_json(std, orient='index')
        std.seek(0, os.SEEK_SET)
        print(yaml.dump(json.loads(std.read()), sort_keys=False))
    else:
        df.to_csv(sys.stdout)


@main.command(help="Deploy process-exporter resources")
def deploy():
    oc_handler(oc.apply, "deployed.")


@main.command(help="Delete process-exporter resources")
def delete():
    oc_handler(oc.delete, "deleted.")


def oc_handler(func, msg):
    files_path, list_of_files = get_data_file_dir()
    for file in list_of_files:
        with open(os.path.join(files_path, file), 'r') as resource:
            try:
                func(yaml.load(resource, Loader=yaml.FullLoader))
                print(file.split('.')[0], msg)
            except oc.model.OpenShiftPythonException as e:
                print(e.msg, file.split('.')[0])


def get_data_file_dir():
    files_path = os.path.join(sys.exec_prefix, 'local', '.prom')
    if not os.path.isdir(files_path):
        files_path = os.path.join(sys.exec_prefix, '.prom')
        if not os.path.isdir(files_path):
            raise Exception("[ERROR] Couldn't find data files")
    list_of_files = ["prometheusRules.yaml", "configmap.yaml",
                     "service.yaml", "servicemonitor.yaml", "daemonset.yaml"]

    return files_path, list_of_files
