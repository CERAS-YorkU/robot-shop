#!/usr/bin/env python3
"""
Extract Labeled Dataset from OpenTelemetry Traces
Converts JSONL traces with anomaly labels into ML-ready datasets
"""

import json
import sys
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def extract_trace_features(trace):
    """Extract features from all spans in a trace

    Returns a list of feature dicts, one per span in the trace.
    Each span represents a service call in the distributed trace.
    """
    all_span_features = []

    # Get resource spans - each resourceSpan represents a different service
    resource_spans = trace.get('resourceSpans', [])
    if not resource_spans:
        return []

    for resource_span in resource_spans:
        # Extract service name from resource attributes
        resource_attrs = resource_span.get('resource', {}).get('attributes', [])
        service_name = 'unknown'
        for attr in resource_attrs:
            if attr.get('key') == 'service.name':
                service_name = attr.get('value', {}).get('stringValue', 'unknown')
                break

        # Get all spans for this service
        scope_spans = resource_span.get('scopeSpans', [])
        if not scope_spans:
            continue

        for scope_span in scope_spans:
            spans = scope_span.get('spans', [])

            # Process each span
            for span in spans:
                features = {}

                # Timing information - FIRST to have timestamp as first column
                start_time = int(span.get('startTimeUnixNano', 0))
                end_time = int(span.get('endTimeUnixNano', 0))

                # Convert nanoseconds to ISO 8601 timestamp for readability
                from datetime import datetime
                features['timestamp'] = datetime.fromtimestamp(start_time / 1_000_000_000).isoformat()
                features['start_time_ns'] = start_time
                features['end_time_ns'] = end_time
                features['duration_ns'] = end_time - start_time
                features['duration_ms'] = features['duration_ns'] / 1_000_000

                # Service information
                features['service_name'] = service_name

                # Span identification - CRITICAL for MSA trace analysis
                features['trace_id'] = span.get('traceId', '')  # Same for all spans in this request
                features['span_id'] = span.get('spanId', '')     # Unique ID for this service call
                features['parent_span_id'] = span.get('parentSpanId', '')  # Parent service that called this

                # Span name and kind
                features['span_name'] = span.get('name', '')
                features['span_kind'] = span.get('kind', 0)  # 1=Internal, 2=Server, 3=Client, 4=Producer, 5=Consumer

                # HTTP attributes - convert list to dict
                attributes = {attr['key']: attr['value'] for attr in span.get('attributes', [])}

                features['http_method'] = attributes.get('http.method', {}).get('stringValue', '')
                features['http_status_code'] = attributes.get('http.status_code', {}).get('intValue', 0)
                features['http_target'] = attributes.get('http.target', {}).get('stringValue', '')
                features['http_url'] = attributes.get('http.url', {}).get('stringValue', '')

                # Anomaly labels (extracted from custom headers)
                features['anomaly_type'] = attributes.get('anomaly.type', {}).get('stringValue', 'none')
                features['anomaly_label'] = attributes.get('anomaly.label', {}).get('stringValue', 'normal')
                features['anomaly_root_cause'] = attributes.get('anomaly.root_cause', {}).get('stringValue', 'none')
                features['anomaly_msg'] = attributes.get('anomaly.msg', {}).get('stringValue', '')

                # Span status
                features['span_status'] = span.get('status', {}).get('code', 0)
                features['span_status_message'] = span.get('status', {}).get('message', '')

                # Network attributes
                features['net_peer_name'] = attributes.get('net.peer.name', {}).get('stringValue', '')
                features['net_peer_port'] = attributes.get('net.peer.port', {}).get('intValue', 0)

                # Add any custom tags
                features['datacenter'] = attributes.get('custom.sdk.tags.datacenter', {}).get('stringValue', '')

                all_span_features.append(features)

    return all_span_features

def extract_metric_features(metric_line):
    """Extract features from a single metric datapoint"""
    features = {}

    resource_metrics = metric_line.get('resourceMetrics', [{}])[0]
    resource_attrs = {attr['key']: attr['value'] for attr in resource_metrics.get('resource', {}).get('attributes', [])}

    features['service_name'] = resource_attrs.get('service.name', {}).get('stringValue', 'unknown')

    scope_metrics = resource_metrics.get('scopeMetrics', [{}])
    if scope_metrics:
        metrics = scope_metrics[0].get('metrics', [])
        for metric in metrics:
            metric_name = metric.get('name', '')

            # Handle different metric types
            if 'gauge' in metric:
                datapoints = metric['gauge'].get('dataPoints', [])
            elif 'sum' in metric:
                datapoints = metric['sum'].get('dataPoints', [])
            elif 'histogram' in metric:
                datapoints = metric['histogram'].get('dataPoints', [])
            else:
                continue

            for dp in datapoints:
                # Get value
                if 'asInt' in dp:
                    features[f'metric_{metric_name}'] = dp['asInt']
                elif 'asDouble' in dp:
                    features[f'metric_{metric_name}'] = dp['asDouble']

                # Get anomaly label from attributes
                dp_attrs = {attr['key']: attr['value'] for attr in dp.get('attributes', [])}
                features['anomaly_label'] = dp_attrs.get('anomaly.label', {}).get('stringValue', 'normal')

    return features

def process_traces(input_file, output_dir):
    """Process traces JSONL file and create labeled dataset"""
    all_spans = []
    trace_count = 0

    print(f"Reading traces from {input_file}...")
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                trace = json.loads(line.strip())
                span_features_list = extract_trace_features(trace)
                if span_features_list:
                    all_spans.extend(span_features_list)  # Add all spans from this trace
                    trace_count += 1
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}")
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")

    print(f"Extracted {len(all_spans)} spans from {trace_count} traces")

    # Convert to DataFrame
    df = pd.DataFrame(all_spans)

    # Summary statistics
    print("\n=== Dataset Summary ===")
    print(f"Total spans: {len(df)}")
    print(f"Unique traces: {df['trace_id'].nunique()}")
    print(f"\nService distribution:")
    print(df['service_name'].value_counts())
    print(f"\nLabel distribution:")
    print(df['anomaly_label'].value_counts())
    print(f"\nAnomaly types:")
    print(df['anomaly_type'].value_counts())

    # Span relationship analysis
    print(f"\nSpan relationships:")
    print(f"  Root spans (no parent): {df['parent_span_id'].isna().sum() + (df['parent_span_id'] == '').sum()}")
    print(f"  Child spans (has parent): {(df['parent_span_id'] != '').sum() - df['parent_span_id'].isna().sum()}")

    # Save full dataset
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'traces_labeled_{timestamp}.csv'
    df.to_csv(output_file, index=False)
    print(f"\nSaved full dataset to: {output_file}")

    # Save separate normal and anomalous datasets
    normal_df = df[df['anomaly_label'] == 'normal']
    anomalous_df = df[df['anomaly_label'] == 'anomalous']

    normal_file = output_dir / f'traces_normal_{timestamp}.csv'
    anomalous_file = output_dir / f'traces_anomalous_{timestamp}.csv'

    normal_df.to_csv(normal_file, index=False)
    anomalous_df.to_csv(anomalous_file, index=False)

    print(f"Saved normal dataset ({len(normal_df)} spans from {normal_df['trace_id'].nunique()} traces) to: {normal_file}")
    print(f"Saved anomalous dataset ({len(anomalous_df)} spans from {anomalous_df['trace_id'].nunique()} traces) to: {anomalous_file}")

    # Save by anomaly type
    for anomaly_type in df['anomaly_type'].unique():
        if anomaly_type != 'none':
            type_df = df[df['anomaly_type'] == anomaly_type]
            type_file = output_dir / f'traces_{anomaly_type}_{timestamp}.csv'
            type_df.to_csv(type_file, index=False)
            print(f"Saved {anomaly_type} dataset ({len(type_df)} samples) to: {type_file}")

    return df

def process_metrics(input_file, output_dir):
    """Process metrics JSONL file"""
    metrics = []

    print(f"\nReading metrics from {input_file}...")
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                metric = json.loads(line.strip())
                features = extract_metric_features(metric)
                if features:
                    metrics.append(features)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}")
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")

    print(f"Extracted {len(metrics)} metric datapoints")

    if metrics:
        df = pd.DataFrame(metrics)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'metrics_labeled_{timestamp}.csv'
        df.to_csv(output_file, index=False)
        print(f"Saved metrics dataset to: {output_file}")
        return df

    return None

def main():
    parser = argparse.ArgumentParser(description='Extract labeled dataset from OTEL traces/metrics')
    parser.add_argument('--traces', type=Path, help='Path to traces JSONL file')
    parser.add_argument('--metrics', type=Path, help='Path to metrics JSONL file')
    parser.add_argument('--output', type=Path, default=Path('./dataset'),
                        help='Output directory for datasets (default: ./dataset)')

    args = parser.parse_args()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    if args.traces:
        process_traces(args.traces, args.output)

    if args.metrics:
        process_metrics(args.metrics, args.output)

    if not args.traces and not args.metrics:
        print("Error: Please provide --traces and/or --metrics file path")
        parser.print_help()
        return 1

    print("\n=== Extraction Complete ===")
    return 0

if __name__ == '__main__':
    sys.exit(main())
