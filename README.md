# Process Interrogator for OpenShift

The [process-exporter](https://github.com/ncabatoff/process-exporter) utility
adds per-process statistics to prometheus, but doesn't afford an easy way to
differentiate pod processes from non-pod processes, which we would like.

The first attempt at finding a way around this involves adding the ability to
filter processes in process-exporter by parent PID and better thread accounting
(work done [here](https://github.com/lack/process-exporter/tree/all_threads)),
and then setting up a config file to group all processes which have a PPID ==
1, meaning all top-level processes on the machine get grouped (and all
lower-level children get grouped in with their parents). With this in place, we
know that all pods will be in the groupname "conmon", and everything else are
non-pod processes.

The objects in process-exporter wrap a custom build of the PPID-filtwering
process-exporter with proper prometheus config to bring it all together.

## Additional recording rules

Prometheus recording rules basically can do a calculation at each scape as the
measurement is collected.  This lets us have better 2nd-order metrics for
things we care about, like the CPU rate over time.  Because we don't generally
care about user vs system time, we also sum these together at the same time.
So we define 2 recording rules:

- namedprocess_namegroup_cpu_rate == "sum without(mode) (irate(namedprocess_namegroup_cpu_seconds_total[30s]))"

- namedprocess_namegroup_thread_cpu_rate == "sum without(mode) (irate(namedprocess_namegroup_thread_cpu_seconds_total[30s]))"

This allows us to better arithmetic operations over the recorded rules like
"avg_over_time"

## "Rate" and Units of Measurement

The main process-exporter namedprocess_namegroup[\_thread]\_cpu_seconds_total
measures system and user CPU seconds as an increasing counter (basically
converting the raw values in /proc/_pid_/status into seconds).  The nice thing
is that calculating the rate of "CPU seconds per second" ends up with the same
metric as the main OpenShift monitoring like `pod:container_cpu_usage:sum`.  A
value of "1" means we used 1s of CPU for every second we ran, or 100% of one
core.

## Example Prometheus Filters

High-level CPU usage for all non-pod processes:

    namedprocess_namegroup_cpu_rate{groupname!~"conmon.*"}
    (previously)
    sum without(mode) (irate(namedprocess_namegroup_cpu_seconds_total{groupname!~"conmon.*"}[30s]))

The same, but splitting out all threads and sub-processes:

    namedprocess_namegroup_thread_cpu_rate{groupname!~"conmon.*"}
    (previously)
    sum without(mode) (irate(namedprocess_namegroup_thread_cpu_seconds_total{groupname!~"conmon.*"}[30s]))

All threads and sub-processes including pods, but not process-exporter itself:

    namedprocess_namegroup_thread_cpu_rate{threadname!~"process-exp.*"}
    (previously)
    sum without(mode) (irate(namedprocess_namegroup_thread_cpu_seconds_total{threadname!~"process-exp.*"}[30s]))

Smooth the threads across a 10m average:

    avg_over_time(namedprocess_namegroup_thread_cpu_rate{threadname!~"process-exp.*"}[10m])

Sum all the infrastructure pods and OS processes into a single number:

    sum(avg_over_time(namedprocess_namegroup_thread_cpu_rate{threadname!~"process-exp.*"}[10m]))

# Scraping Data Out

I have an example script, [prometheus-csv](./prometheus-csv), which will
contact a given cluster over the metrics interface, gather the average CPU,
max CPU, and min CPU over the time period specified, and produce csv output.
This intentionally excludes the 'process-exporter' pod itself, but does
include every Host OS process gathered by the process-exporter pod, plus all
the other pods on the system.  If you're running CPU-intensive workloads, it
should be easy to adapt the script to exclude those from the accounting by
filtering on namespace or something.

# Overhead

With the prometheus instance set up to scrape the metrics every 15s, the
process-exporter seems to set at around 0.50 of one CPU, and the additional
load on prometheus itself is negligible.

[This diagram](images/process-exporter-and-prometheus-CPU.png) shows a period
of time when process-exporter's pod is deleted, then when the pod is present
but the prometheus scraping is disabled (by temporarily deleting the
servicemonitor), then steady-state operation.  The avg prometheus instance CPU
is basically unchanged throughout.

# TODO
- Cleaner packaging.  Maybe a deployment or daemonset?
- Maybe adapt process-exporter to do more container-gnostic filtering, perhaps
  based on cgroup filtering?
- Add labels to differentiate "infrastructure pods" from "workload pods"
- Add a label or config change to exclude process-exporter itself
