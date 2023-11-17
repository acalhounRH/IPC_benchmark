# IPC Benchmark

## Overview

This Python program is designed for benchmarking Inter-Process Communication (IPC) performance using shared memory. It supports benchmarking with various configurations, such as data size, duration, logging, shared memory type, message size, process count, message pattern, message count, number of runs, and output format options.

## Features

- **Flexible Configuration:** Configure the benchmark with various parameters to tailor it to your specific use case.
- **Multiple IPC Patterns:** Supports both "request-response" and "publish-subscribe" message patterns.
- **Shared Memory:** Utilizes shared memory for communication between processes.
- **Logging:** Logs benchmark results to a file for analysis and comparison.
- **Human-Readable and JSON Output:** Choose between human-readable and JSON output formats.
- **Aggregate Statistics:** Calculate aggregate statistics across multiple runs.

## Usage

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt

## Run Benchmark 
### Command line
   
   ```bash
   
   python ipc_benchmark.py --data_size 128 --duration 10 --log_file ipc_benchmark.log --posix --message_size 1024 --message_pattern request-response --process_count 4 --message_count 1000 --human_readable --output_json --runs 5
   ```

In this example:

* data_size 128: Sets the size of the shared memory to 128 MB.
* duration 10: Runs the benchmark for 10 seconds.
* log_file ipc_benchmark.log: Specifies the log file.
* posix: Uses POSIX Shared Memory.
* message_size 1024: Sets the message size to 1024 bytes.
* message_pattern request-response: Chooses the request-response communication pattern.
* process_count 4: Specifies the number of processes participating in the benchmark.
* message_count 1000: Sets the number of messages to exchange between processes.
* human_readable: Outputs results in human-readable format.
* output_json: Outputs results in JSON format.
* runs 5: Runs the benchmark five times with the same configuration.


### Yaml file
python ipc_benchmark.py --config=config.yaml

Benchmark_config.yaml Example:
```
data_size:
  - 10
  - 20
  - 50

duration:
  - 60
  - 120
  - 180

log_file: ipc_benchmark.log

posix:
  - true
  - false

message_size:
  - 512
  - 1024
  - 2048

message_pattern:
  - request-response
  - publish-subscribe

process_count:
  - 2
  - 4
  - 8

message_count:
  - 1000
  - 5000
  - 10000

human_readable:
   - true
output_json:
   - true

runs: 3
```
### Sample output

Standard output (Human-readable)

   ```
   IPC Benchmark Run Summary: 1 out of 3
   Options:
   Data Size (MB): 10
   Duration (s): 60
   Log File: ipc_benchmark.log
   POSIX Shared Memory: True
   Message Size (bytes): 512
   Message Pattern: request-response
   Process Count: 2
   Message Count: 1000
   Human-Readable Output Format: True
   Output JSON Format: True
   Runs: 3
   
   Latency Statistics:
   50th Percentile (P50) Latency: 0.005123 seconds
   90th Percentile (P90) Latency: 0.007234 seconds
   99th Percentile (P99) Latency: 0.010456 seconds
   Average Latency: 0.006789 seconds
   
   Throughput Statistics:
   Average Msg/s: 150.0
   Average Throughput: 0.000073
   Maximum Throughput: 0.000098
   Minimum Throughput: 0.000054
   
   Percent Deviation: 1.23%
   Jitter: 0.000012 seconds
   
   IPC Benchmark Run Summary: 2 out of 3
   ...
   
   IPC Benchmark Run Summary: 3 out of 3
   ...

   Aggregate Statistics:
   
   Latency:
   50th Percentile (P50): 0.006543 seconds
   90th Percentile (P90): 0.008765 seconds
   99th Percentile (P99): 0.011987 seconds
   Average: 0.009876 seconds
   
   Throughput:
   Average Msg/s: 145.0
   Average: 0.000065
   Maximum: 0.000085
   Minimum: 0.000045
   
   Percent Deviation: 1.45%
   Jitter: 0.000015 seconds
```
### Json output
``` 
   [
    {
        "Run": 1,
        "Options": {
            "Data Size (MB)": 10,
            "Duration (s)": 60,
            "Log File": "ipc_benchmark.log",
            "POSIX Shared Memory": true,
            "Message Size (bytes)": 512,
            "Message Pattern": "request-response",
            "Process Count": 2,
            "Message Count": 1000,
            "Human-Readable Output Format": true,
            "Output JSON Format": true,
            "Runs": 3
        },
        "Latency Statistics": {
            "50th Percentile (P50) Latency": 0.005123,
            "90th Percentile (P90) Latency": 0.007234,
            "99th Percentile (P99) Latency": 0.010456,
            "Average Latency": 0.006789
        },
        "Throughput Statistics": {
            "Average Msg/s": 150.0,
            "Average Throughput": 0.000073,
            "Maximum Throughput": 0.000098,
            "Minimum Throughput": 0.000054
        },
        "Percent Deviation": 1.23,
        "Jitter": 0.000012
    },
    {
        "Run": 2,
        ...
    },
    {
        "Run": 3,
        ...
    }
    {
        "Aggregate Statistics": {
            "Latency": {
                "50th Percentile (P50)": 0.006543,
                "90th Percentile (P90)": 0.008765,
                "99th Percentile (P99)": 0.011987,
                "Average": 0.009876
            },
            "Throughput": {
                "Average Msg/s": 145.0,
                "Average": 0.000065,
                "Maximum": 0.000085,
                "Minimum": 0.000045
            },
            "Percent Deviation": 1.45,
            "Jitter": 0.000015
        }
    }
]
```
