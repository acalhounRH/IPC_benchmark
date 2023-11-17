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

def ipc_worker(data, process_id, message_size, message_pattern, args, timestamps):
    print("Creating ipc worker")
    
    num_messages = args.message_count
    messages_processed = 0
    duration = args.duration
    
    if duration == 0 and num_messages == 0:
        raise ValueError("Both duration and num_messages cannot be 0. Specify a positive value for at least one of them.")
    Rstart_time = time.time()
    if message_pattern == "request-response":
        request = bytearray([random.randint(0, 255) for _ in range(message_size)])
        response = bytearray(message_size)

        while True:
            start_time = time.time()
            # Write request to shared memory
            data[:message_size] = request

            # Read response from shared memory
            response[:] = data[:message_size]
            end_time = time.time()

            timestamps.append({
                'capture_time': datetime.utcfromtimestamp(end_time).strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'process_id': process_id,
                'start_time': start_time,
                'end_time': end_time
            })

            Rend_time = time.time()
            if duration and (Rend_time - Rstart_time) >= duration:
                break  # Stop if duration is reached

            messages_processed += 1
            if num_messages and messages_processed >= num_messages:
                break

    elif message_pattern == "publish-subscribe":
        while True:
            message = bytearray([random.randint(0, 255) for _ in range(message_size)])
            
            # Write message to shared memory
            start_time = time.time()
            data[:message_size] = message
            end_time = time.time()

            timestamps.append({
                'capture_time': datetime.utcfromtimestamp(end_time).strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'process_id': process_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            Rend_time = time.time()
            if duration and (Rend_time - Rstart_time) >= duration:
                break  # Stop if duration is reached
            
            messages_processed += 1
            if num_messages and messages_processed >= num_messages:
                break

def create_shared_memory(size, posix=False):
    print("creating shared memory")
    if posix:
        print("using posix shared memory")
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
        print("using system V shared memory")
        shared_memory = multiprocessing.shared_memory.SharedMemory(create=True, size=size * 1024 * 1024)
    return shared_memory

def run_ipc_benchmark(args):
    print("running ipc benchmark")
    if args.posix and posix_ipc is None:
        raise ImportError("posix_ipc module is not available. Install it or run without POSIX shared memory.")

    shared_memory = create_shared_memory(args.data_size, posix=args.posix)
    logging.basicConfig(filename=args.log_file, level=logging.INFO, format='%(message)s')
    data = multiprocessing.shared_memory.SharedMemory(name=shared_memory.name)

    if args.message_pattern == "request-response":
        shared_data = data.buf
        shared_data[:args.data_size * 1024 * 256] = bytes([0] * (args.data_size * 1024 * 256))
    elif args.message_pattern == "publish-subscribe":
        shared_data = data.buf[:args.data_size * 1024 * 1024]

    num_processes = args.process_count


    all_results = []
    all_agg_results = []
    log_data = []
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

    for run in range(args.runs):

        latencies = multiprocessing.Manager().list()
        mps = multiprocessing.Manager().list()
        throughput = multiprocessing.Manager().list()
        timestamps = multiprocessing.Manager().list()
        processes = []
        
        start_run_time = time.time()
        
        #for each process start a ipc worker
        for i in range(num_processes):
            process = multiprocessing.Process(target=ipc_worker, args=(shared_data, i, args.message_size, args.message_pattern, args, latencies, mps, throughput, timestamps))
            processes.append(process)
            process.start()

        #wait for ipc workers to either time out or reach message count
        for process in processes:
            process.join()
        end_run_time = time.time()
        duration_runtime = end_run_time - start_run_time 

        # Calculate latency, MPS, and throughput for each timestamp
        for timestamp in timestamps:
            latency = timestamp['end_time'] - timestamp['start_time']
            latencies.append(latency)

            mps_value = 1 / latency
            mps.append(mps_value)

            throughput_value = (args.message_size * 2) / (latency * 1024 * 1024)
            throughput.append(throughput_value)
                
        # Log the calculated values for each run
        for i, timestamp in enumerate(timestamps):
            
            log_data.append({
                'capture_time': timestamp['capture_time'],
                'process_id': timestamp['process_id'],
                'latency': latencies[i],
                'mps': mps[i],
                'throughput': throughput[i],
                'options': options
            })
            
            log_message = f"{timestamp['capture_time']},{timestamp['process_id']},{latencies[i]:.6f},{mps[i]:.2f},{throughput[i]:.2f}"
            logging.info(log_message)
        
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

        summary = {
            'Run': run + 1,  # Adding a "Run" counter
            'Run Duration': duration_runtime,
            'Options': options,
            'Latency Statistics': {
                '50th Percentile (P50) Latency': p50_latency,
                '90th Percentile (P90) Latency': p90_latency,
                '99th Percentile (P99) Latency': p99_latency,
                'Average Latency': average_latency
            },
            'Throughput Statistics': {
                'Average Msg/s': avg_mps,
                'Average Throughput MB/s': avg_throughput,
                'Maximum Throughput MB/s': max_throughput,
                'Minimum Throughput MB/s': min_throughput
            },
            'Percent Deviation': percent_deviation,
            'Jitter': jitter
        }

        all_results.append(summary)

        if args.human_readable:
            print("\nIPC Benchmark Run Summary:" + str(run + 1) + " out of " + str(args.runs))
            print("\nDuration runtime:" + str(int(duration_runtime)))
            print("Options:")
            for option, value in options.items():
                print(f"{option}: {value}")
            
            print("\nLatency Statistics:")
            for stat, value in summary['Latency Statistics'].items():
                print(f"{stat}: {value:.6f} seconds")
    
            print("\nThroughput Statistics:")
            for stat, value in summary['Throughput Statistics'].items():
                print(f"{stat}: {value:.2f}")
    
            print("\nPercent Deviation: {:.3f}%".format(percent_deviation))
            print(f"Jitter: {jitter:.6f} seconds")
    
    shared_data = None
    shared_memory.close()
    shared_memory.unlink()

    aggregate_summary = {
        'Options': options,
        'Aggregate Latency Statistics': {
            '50th Percentile (P50) Latency': np.percentile([run['Latency Statistics']['50th Percentile (P50) Latency'] for run in all_results], 50),
            '90th Percentile (P90) Latency': np.percentile([run['Latency Statistics']['90th Percentile (P90) Latency'] for run in all_results], 90),
            '99th Percentile (P99) Latency': np.percentile([run['Latency Statistics']['99th Percentile (P99) Latency'] for run in all_results], 99),
            'Average Latency': np.mean([run['Latency Statistics']['Average Latency'] for run in all_results])
        },
        'Aggregate Throughput Statistics': {
            'Average Msg/s': np.mean([run['Throughput Statistics']['Average Msg/s'] for run in all_results]),
            'Average Throughput MB/s': np.mean([run['Throughput Statistics']['Average Throughput MB/s'] for run in all_results]),
            'Maximum Throughput MB/s': np.max([run['Throughput Statistics']['Maximum Throughput MB/s'] for run in all_results]),
            'Minimum Throughput MB/s': np.min([run['Throughput Statistics']['Minimum Throughput MB/s'] for run in all_results])
        },
        'Aggregate Percent Deviation': np.mean([run['Percent Deviation'] for run in all_results]),
        'Aggregate Jitter': np.mean([run['Jitter'] for run in all_results])
        }
    
    all_agg_results.append(aggregate_summary)
    
    if args.human_readable:
        print("\nAggregate Statistics Across All Runs:")
        
        print("Options:")
        for option, value in options.items():
            print(f"{option}: {value}")
        
        print("\nAggregate Latency Statistics:")
        for stat, value in aggregate_summary['Aggregate Latency Statistics'].items():
            print(f"{stat}: {value:.6f} seconds")
    
        print("\nAggregate Throughput Statistics:")
        for stat, value in aggregate_summary['Aggregate Throughput Statistics'].items():
            print(f"{stat}: {value:.2f}")
    
        print("\nAggregate Percent Deviation: "+ str(aggregate_summary['Aggregate Percent Deviation']))
        print("Aggregate Jitter: " + str(aggregate_summary['Aggregate Jitter']) + "seconds")
    
    if args.output_json:
        with open('ipc_benchmark_results.json', 'w') as json_file:
            json.dump(all_results, json_file, indent=4)
            
    if args.output_json:
        with open('ipc_benchmark_aggregate_results.json', 'w') as json_file:
            json.dump(all_agg_results, json_file, indent=4)

        # Dump log_data into JSON log file
    with open('ipc_benchmark_log.json', 'w') as json_log_file:
        json.dump(log_data, json_log_file, indent=4)

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
