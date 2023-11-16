import argparse
import itertools
import logging
import multiprocessing
from  multiprocessing import shared_memory
import numpy as np
import random
import time
import yaml
import json
import sys
from datetime import datetime

try:
    import posix_ipc
except ImportError:
    posix_ipc = None

def ipc_worker(data, process_id, message_size, message_pattern, args, latencies, mps, throughput, timestamps):
    num_messages = args.message_count

    if message_pattern == "request-response":
        request = bytearray([random.randint(0, 255) for _ in range(message_size)])
        response = bytearray(message_size)

        for _ in range(num_messages):
            # Write request to shared memory
            data[:message_size] = request
            start_time = time.time()

            # Read response from shared memory
            response[:] = data[:message_size]

            end_time = time.time()

            latency = end_time - start_time
            latencies.append(latency)
            mps_value = 1 / latency
            mps.append(mps_value)
            throughput_value = (message_size * 2) / (latency * 1024 * 1024)
            throughput.append(throughput_value)
            timestamps.append(end_time)

            # Release shared memory
            data.release()

    elif message_pattern == "publish-subscribe":
        for _ in range(num_messages):
            message = bytearray([random.randint(0, 255) for _ in range(message_size)])
            
            # Write message to shared memory
            data[:message_size] = message
            start_time = time.time()
            end_time = time.time()

            latency = end_time - start_time
            latencies.append(latency)
            mps_value = 1 / latency
            mps.append(mps_value)
            throughput_value = (message_size) / (latency * 1024 * 1024)
            throughput.append(throughput_value)
            timestamps.append(end_time)

            # Release shared memory
            data.release()

    log_message = f"{datetime.utcfromtimestamp(timestamps[-1]).strftime('%Y-%m-%dT%H:%M:%S.%f')}," \
                  f"{process_id},{latency:.6f},{mps_value:.2f},{throughput_value:.2f}"
    logging.info(log_message)

def create_shared_memory(size, posix=False):
    if posix:
        try:
            shm_name = "/shm_" + str(random.randint(1, 1000000))
            shm = posix_ipc.SharedMemory(shm_name, flags=posix_ipc.O_CREAT, size=size * 1024 * 1024)
            shared_memory = multiprocessing.shared_memory.SharedMemory(shm_name)
            shm.close_fd()
        except posix_ipc.ExistentialError:
            # Handle the case where shared memory with the same name already exists
            shm = posix_ipc.SharedMemory(None, flags=posix_ipc.O_RDWR)
            shared_memory = multiprocessing.shared_memory.SharedMemory(shm_name)
    else:
        shared_memory = multiprocessing.shared_memory.SharedMemory(create=True, size=size * 1024 * 1024)
    return shared_memory

def run_ipc_benchmark(args):
    if args.posix and posix_ipc is None:
        raise ImportError("posix_ipc module is not available. Install it or run without POSIX shared memory.")

    shared_memory = create_shared_memory(args.data_size, posix=args.posix)
    logging.basicConfig(filename=args.log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
    data = multiprocessing.shared_memory.SharedMemory(name=shared_memory.name)

    if args.message_pattern == "request-response":
        shared_data = data.buf
        shared_data[:args.data_size * 1024 * 256] = bytes([0] * (args.data_size * 1024 * 256))
    elif args.message_pattern == "publish-subscribe":
        shared_data = data.buf[:args.data_size * 1024 * 1024]

    num_processes = args.process_count
    latencies = multiprocessing.Manager().list()
    mps = multiprocessing.Manager().list()
    throughput = multiprocessing.Manager().list()
    timestamps = multiprocessing.Manager().list()

    all_results = []

    for run in range(args.runs):
        processes = []

        for _ in range(num_processes):
            start_time = time.time()

            if args.duration:
                while (time.time() - start_time) < args.duration:
                    for i in range(num_processes):
                        process = multiprocessing.Process(target=ipc_worker, args=(shared_data, i, args.message_size, args.message_pattern, args, latencies, mps, throughput, timestamps))
                        processes.append(process)
                        process.start()
                    time.sleep(0.1)
            elif args.message_count:
                for i in range(num_processes):
                    process = multiprocessing.Process(target=ipc_worker, args=(shared_data, i, args.message_size, args.message_pattern, args, latencies, mps, throughput, timestamps))
                    processes.append(process)
                    process.start()

            for process in processes:
                process.join()

        latencies = list(latencies)
        p50_latency = np.percentile(latencies, 50)
        p90_latency = np.percentile(latencies, 90)
        p99_latency = np.percentile(latencies, 99)
        average_latency = np.mean(latencies)

        mps = list(mps)
        throughput = list(throughput)
        avg_mps = sum(mps) / len(mps)
        avg_throughput = sum(throughput) / len(throughput)
        max_throughput = max(throughput)
        min_throughput = min(throughput)

        percent_deviation = np.std(latencies) / np.mean(latencies) * 100
        jitter = max(latencies) - min(latencies)

        options = {
            'Data Size (MB)': args.data_size,
            'Duration (s)': args.duration if args.duration else 'Not Applicable',
            'Message Count': args.message_count if args.message_count else 'Not Applicable',
            'Log File': args.log_file,
            'POSIX Shared Memory': args.posix,
            'Message Size (bytes)': args.message_size,
            'Message Pattern': args.message_pattern,
            'Process Count': args.process_count,
            'Output Format': 'Human-Readable' if args.human_readable else 'JSON',
            'Runs': args.runs
        }

        summary = {
            'Run': run + 1,  # Adding a "Run" counter
            'Options': options,
            'Latency Statistics': {
                '50th Percentile (P50) Latency': p50_latency,
                '90th Percentile (P90) Latency': p90_latency,
                '99th Percentile (P99) Latency': p99_latency,
                'Average Latency': average_latency
            },
            'Throughput Statistics': {
                'Average MPS': avg_mps,
                'Average Throughput': avg_throughput,
                'Maximum Throughput': max_throughput,
                'Minimum Throughput': min_throughput
            },
            'Percent Deviation': percent_deviation,
            'Jitter': jitter
        }

        all_results.append(summary)

    if args.output_json:
        with open('ipc_benchmark_results.json', 'w') as json_file:
            json.dump(all_results, json_file, indent=4)

def main():
    
    print(sys.version)
    parser = argparse.ArgumentParser(description='IPC Benchmark with Data Size, Duration, Logging, Shared Memory, Message Size, Process Count, Message Pattern, Message Count, Number of Runs, and Output JSON Options')
    parser.add_argument('--config', type=str, help='Path to the YAML config file. It allows specifying multiple values for each option.')
    parser.add_argument('--show-help', action='store_true', help='Show this help message and exit')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--yaml', type=str, help='Path to the YAML config file (alternative to --config)')
    
    parser.add_argument('--data_size', type=int, help='Data Size (in MB). The size of the shared memory.')
    parser.add_argument('--duration', type=int, help='Duration (in seconds). The time to run the benchmark.')
    parser.add_argument('--log_file', type=str, help='Log File. The file to store benchmark logs.')
    parser.add_argument('--posix', action='store_true', help='Use POSIX Shared Memory. Use POSIX shared memory instead of multiprocessing shared memory.')
    parser.add_argument('--message_size', type=int, help='Message Size (in bytes). The size of each message.')
    parser.add_argument('--message_pattern', choices=['request-response', 'publish-subscribe'], help='Message Pattern. The communication pattern between processes.')
    parser.add_argument('--process_count', type=int, help='Process Count. The number of processes participating in the benchmark.')
    parser.add_argument('--message_count', type=int, help='Message Count. The number of messages to exchange between processes.')
    parser.add_argument('--human_readable', action='store_true', help='Human-Readable Output Format. Output results in a human-readable format.')
    parser.add_argument('--output_json', action='store_true', help='Output JSON Format. Output results in JSON format.')
    parser.add_argument('--runs', type=int, help='Number of Runs. The number of times to run the benchmark with the same configuration.')

    args = parser.parse_args()

    if args.show_help:
        print("IPC Benchmark Options:")
        print("--config: Path to the YAML config file. It allows specifying multiple values for each option.")
        print("--yaml: Path to the YAML config file (alternative to --config).")
        print("--data_size: Data Size (in MB). The size of the shared memory.")
        print("--duration: Duration (in seconds). The time to run the benchmark.")
        print("--log_file: Log File. The file to store benchmark logs.")
        print("--posix: Use POSIX Shared Memory. Use POSIX shared memory instead of multiprocessing shared memory.")
        print("--message_size: Message Size (in bytes). The size of each message.")
        print("--message_pattern: Message Pattern. The communication pattern between processes. Choose between 'request-response' and 'publish-subscribe'.")
        print("--process_count: Process Count. The number of processes participating in the benchmark.")
        print("--message_count: Message Count. The number of messages to exchange between processes.")
        print("--human_readable: Human-Readable Output Format. Output results in a human-readable format.")
        print("--output_json: Output JSON Format. Output results in JSON format.")
        print("--runs: Number of Runs. The number of times to run the benchmark with the same configuration.")
        exit()

    if args.yaml:
        with open(args.yaml, 'r') as config_file:
            config = yaml.safe_load(config_file)
    elif args.config:
        with open(args.config, 'r') as config_file:
            config = yaml.safe_load(config_file)
    else:
        config = {
            'data_size': [args.data_size],
            'duration': [args.duration],
            'log_file': [args.log_file],
            'posix': [args.posix],
            'message_size': [args.message_size],
            'message_pattern': [args.message_pattern],
            'process_count': [args.process_count],
            'message_count': [args.message_count],
            'human_readable': [args.human_readable],
            'output_json': [args.output_json],
            'runs': [args.runs]
        }

    option_permutations = list(itertools.product(*config.values()))

    for options in option_permutations:
        parsed_args = argparse.Namespace(**dict(zip(config.keys(), options)))
        run_ipc_benchmark(parsed_args)

if __name__ == "__main__":
    main()
