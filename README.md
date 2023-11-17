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

    
    data_size: [1024]
    duration: [60]
    log_file: "benchmark.log"
    posix: true
    message_size: [256]
    message_pattern: "request-response"
    process_count: 4
    message_count: 0
    human_readable: true
    output_json: true
    runs: 3


