# logdrift

> Lightweight log aggregator that watches multiple log files and surfaces anomalies using pattern matching.

---

## Installation

```bash
pip install logdrift
```

Or install from source:

```bash
git clone https://github.com/yourname/logdrift.git && cd logdrift && pip install .
```

---

## Usage

Watch one or more log files and define patterns to flag as anomalies:

```python
from logdrift import LogWatcher

watcher = LogWatcher(
    files=["/var/log/app.log", "/var/log/nginx/error.log"],
    patterns=["ERROR", "CRITICAL", "connection refused", r"5\d{2} "],
)

for anomaly in watcher.watch():
    print(f"[{anomaly.source}] {anomaly.line}")
```

Run from the command line:

```bash
logdrift watch /var/log/app.log --patterns "ERROR" "CRITICAL" --tail
```

Output:

```
[/var/log/app.log]  2024-06-01 12:03:44 ERROR  Database connection refused
[/var/log/app.log]  2024-06-01 12:03:51 CRITICAL  Disk usage above 95%
```

---

## Configuration

You can also define patterns in a `logdrift.yaml` file:

```yaml
files:
  - /var/log/app.log
  - /var/log/syslog
patterns:
  - ERROR
  - CRITICAL
  - out of memory
```

Then run:

```bash
logdrift watch --config logdrift.yaml
```

---

## License

MIT © 2024 [yourname](https://github.com/yourname)