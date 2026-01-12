#!/usr/bin/env python3
"""
Analyze Trace Relationships in OpenTelemetry Dataset

This script analyzes the parent-child span relationships and trace structure
in the extracted OpenTelemetry dataset to verify distributed tracing integrity.

Checks:
1. Parent-child span relationships (span_id ↔ parent_span_id)
2. Trace ID uniqueness and consistency
3. Orphaned spans (parent_span_id points to non-existent span_id)
4. Root spans (spans with no parent)
5. Trace tree depth and breadth
"""

import pandas as pd
import sys
from pathlib import Path
from collections import defaultdict, Counter

def analyze_span_relationships(df):
    """Analyze parent-child relationships between spans"""
    print("=" * 80)
    print("SPAN RELATIONSHIP ANALYSIS")
    print("=" * 80)

    # Basic counts
    total_spans = len(df)
    unique_span_ids = df['span_id'].nunique()
    unique_parent_ids = df[df['parent_span_id'] != '']['parent_span_id'].nunique()

    print(f"\n1. Basic Counts:")
    print(f"   Total spans: {total_spans:,}")
    print(f"   Unique span_id values: {unique_span_ids:,}")
    print(f"   Unique parent_span_id values: {unique_parent_ids:,}")

    # Check for duplicate span_ids (should be unique)
    duplicate_span_ids = df[df.duplicated(subset=['span_id'], keep=False)]
    if len(duplicate_span_ids) > 0:
        print(f"\n   ⚠️  WARNING: Found {len(duplicate_span_ids)} duplicate span_id entries!")
        print(f"   Example duplicates:")
        print(duplicate_span_ids[['trace_id', 'span_id', 'service_name', 'span_name']].head())
    else:
        print(f"   ✅ All span_id values are unique")

    # Root spans (no parent)
    root_spans = df[df['parent_span_id'] == '']
    child_spans = df[df['parent_span_id'] != '']

    print(f"\n2. Span Hierarchy:")
    print(f"   Root spans (no parent): {len(root_spans):,} ({len(root_spans)/total_spans*100:.1f}%)")
    print(f"   Child spans (has parent): {len(child_spans):,} ({len(child_spans)/total_spans*100:.1f}%)")

    # Root spans by service
    print(f"\n   Root spans by service:")
    root_by_service = root_spans['service_name'].value_counts()
    for service, count in root_by_service.items():
        print(f"      {service}: {count:,}")

    # Root spans by span_kind
    print(f"\n   Root spans by span_kind:")
    root_by_kind = root_spans['span_kind'].value_counts().sort_index()
    kind_names = {0: 'UNSPECIFIED', 1: 'INTERNAL', 2: 'SERVER', 3: 'CLIENT', 4: 'PRODUCER', 5: 'CONSUMER'}
    for kind, count in root_by_kind.items():
        kind_name = kind_names.get(kind, f'UNKNOWN({kind})')
        print(f"      {kind_name} ({kind}): {count:,} ({count/len(root_spans)*100:.1f}%)")

    # Child spans by span_kind
    print(f"\n   Child spans by span_kind:")
    child_by_kind = child_spans['span_kind'].value_counts().sort_index()
    for kind, count in child_by_kind.items():
        kind_name = kind_names.get(kind, f'UNKNOWN({kind})')
        print(f"      {kind_name} ({kind}): {count:,} ({count/len(child_spans)*100:.1f}%)")

    return root_spans, child_spans

def analyze_orphaned_spans(df):
    """Check for orphaned spans (parent_span_id doesn't exist)"""
    print("\n" + "=" * 80)
    print("ORPHANED SPAN ANALYSIS")
    print("=" * 80)

    # Get all span_ids in the dataset
    all_span_ids = set(df['span_id'].unique())

    # Get child spans
    child_spans = df[df['parent_span_id'] != '']

    # Check if parent_span_id exists in the dataset
    orphaned_spans = []
    for idx, row in child_spans.iterrows():
        parent_id = row['parent_span_id']
        if parent_id not in all_span_ids:
            orphaned_spans.append(row)

    if len(orphaned_spans) > 0:
        orphaned_df = pd.DataFrame(orphaned_spans)
        print(f"\n⚠️  Found {len(orphaned_df)} orphaned spans (parent_span_id not in dataset)")
        print(f"\nOrphaned spans by service:")
        print(orphaned_df['service_name'].value_counts())
        print(f"\nOrphaned spans by span_kind:")
        orphaned_by_kind = orphaned_df['span_kind'].value_counts().sort_index()
        kind_names = {0: 'UNSPECIFIED', 1: 'INTERNAL', 2: 'SERVER', 3: 'CLIENT', 4: 'PRODUCER', 5: 'CONSUMER'}
        for kind, count in orphaned_by_kind.items():
            kind_name = kind_names.get(kind, f'UNKNOWN({kind})')
            print(f"   {kind_name} ({kind}): {count:,}")

        print(f"\nSample orphaned spans:")
        print(orphaned_df[['trace_id', 'span_id', 'parent_span_id', 'service_name', 'span_name', 'span_kind']].head(10))

        return orphaned_df
    else:
        print(f"\n✅ No orphaned spans found! All parent_span_id values exist in the dataset.")
        return None

def analyze_trace_structure(df):
    """Analyze trace-level structure"""
    print("\n" + "=" * 80)
    print("TRACE STRUCTURE ANALYSIS")
    print("=" * 80)

    # Group by trace_id
    trace_groups = df.groupby('trace_id')

    print(f"\n1. Trace Statistics:")
    print(f"   Unique traces: {df['trace_id'].nunique():,}")

    # Spans per trace
    spans_per_trace = trace_groups.size()
    print(f"\n   Spans per trace:")
    print(f"      Min: {spans_per_trace.min()}")
    print(f"      Max: {spans_per_trace.max()}")
    print(f"      Mean: {spans_per_trace.mean():.2f}")
    print(f"      Median: {spans_per_trace.median():.0f}")

    # Trace span distribution
    print(f"\n   Distribution of spans per trace:")
    span_distribution = spans_per_trace.value_counts().sort_index()
    for span_count, trace_count in span_distribution.head(15).items():
        print(f"      {span_count} span(s): {trace_count:,} traces")
    if len(span_distribution) > 15:
        print(f"      ... ({len(span_distribution) - 15} more)")

    # Services per trace
    services_per_trace = trace_groups['service_name'].nunique()
    print(f"\n   Services per trace:")
    print(f"      Min: {services_per_trace.min()}")
    print(f"      Max: {services_per_trace.max()}")
    print(f"      Mean: {services_per_trace.mean():.2f}")
    print(f"      Median: {services_per_trace.median():.0f}")

    # Root spans per trace
    root_spans_per_trace = trace_groups.apply(lambda x: (x['parent_span_id'] == '').sum())
    print(f"\n   Root spans per trace:")
    print(f"      Min: {root_spans_per_trace.min()}")
    print(f"      Max: {root_spans_per_trace.max()}")
    print(f"      Mean: {root_spans_per_trace.mean():.2f}")
    print(f"      Median: {root_spans_per_trace.median():.0f}")

    # Traces with multiple roots
    multi_root_traces = root_spans_per_trace[root_spans_per_trace > 1]
    if len(multi_root_traces) > 0:
        print(f"\n   ⚠️  {len(multi_root_traces):,} traces have multiple root spans")
        print(f"      This may indicate disconnected span trees within the same trace")

    return trace_groups

def analyze_trace_depth(df):
    """Calculate trace tree depth by building parent-child relationships"""
    print("\n" + "=" * 80)
    print("TRACE DEPTH ANALYSIS")
    print("=" * 80)

    print(f"\nBuilding span hierarchy trees for all traces...")

    # Build a mapping of span_id -> children
    span_to_children = defaultdict(list)
    span_to_info = {}

    for idx, row in df.iterrows():
        span_id = row['span_id']
        parent_id = row['parent_span_id']

        span_to_info[span_id] = {
            'trace_id': row['trace_id'],
            'service': row['service_name'],
            'span_name': row['span_name'],
            'span_kind': row['span_kind']
        }

        if parent_id and parent_id != '':
            span_to_children[parent_id].append(span_id)

    # Calculate depth for each span
    def calculate_depth(span_id, visited=None):
        """Recursively calculate depth of span tree"""
        if visited is None:
            visited = set()

        if span_id in visited:
            return 0  # Circular reference protection

        visited.add(span_id)
        children = span_to_children.get(span_id, [])

        if not children:
            return 1

        max_child_depth = max(calculate_depth(child, visited.copy()) for child in children)
        return 1 + max_child_depth

    # Find root spans
    root_spans = df[df['parent_span_id'] == '']

    trace_depths = {}
    trace_breadths = {}

    for _, root in root_spans.iterrows():
        trace_id = root['trace_id']
        span_id = root['span_id']

        depth = calculate_depth(span_id)
        breadth = len(span_to_children.get(span_id, []))

        if trace_id not in trace_depths:
            trace_depths[trace_id] = depth
            trace_breadths[trace_id] = breadth
        else:
            # Multiple roots in same trace - take max depth
            trace_depths[trace_id] = max(trace_depths[trace_id], depth)
            trace_breadths[trace_id] = max(trace_breadths[trace_id], breadth)

    if trace_depths:
        depths = list(trace_depths.values())
        breadths = list(trace_breadths.values())

        print(f"\n   Trace tree depth (max levels from root to leaf):")
        print(f"      Min: {min(depths)}")
        print(f"      Max: {max(depths)}")
        print(f"      Mean: {sum(depths)/len(depths):.2f}")
        print(f"      Median: {sorted(depths)[len(depths)//2]}")

        print(f"\n   Depth distribution:")
        depth_dist = Counter(depths)
        for depth, count in sorted(depth_dist.items()):
            print(f"      Depth {depth}: {count:,} traces")

        print(f"\n   Root span breadth (immediate children):")
        print(f"      Min: {min(breadths)}")
        print(f"      Max: {max(breadths)}")
        print(f"      Mean: {sum(breadths)/len(breadths):.2f}")
        print(f"      Median: {sorted(breadths)[len(breadths)//2]}")

        # Find deepest trace
        deepest_trace_id = max(trace_depths, key=trace_depths.get)
        deepest_depth = trace_depths[deepest_trace_id]
        print(f"\n   Deepest trace: {deepest_trace_id} (depth: {deepest_depth})")

def analyze_cross_service_calls(df):
    """Analyze cross-service span relationships"""
    print("\n" + "=" * 80)
    print("CROSS-SERVICE CALL ANALYSIS")
    print("=" * 80)

    # Build span_id -> service mapping
    span_to_service = dict(zip(df['span_id'], df['service_name']))

    # Find parent-child relationships where service differs
    child_spans = df[df['parent_span_id'] != '']

    cross_service_calls = []

    for idx, row in child_spans.iterrows():
        parent_id = row['parent_span_id']
        child_service = row['service_name']

        if parent_id in span_to_service:
            parent_service = span_to_service[parent_id]
            if parent_service != child_service:
                cross_service_calls.append({
                    'parent_service': parent_service,
                    'child_service': child_service,
                    'trace_id': row['trace_id'],
                    'parent_span_id': parent_id,
                    'child_span_id': row['span_id']
                })

    if cross_service_calls:
        cross_df = pd.DataFrame(cross_service_calls)
        print(f"\n   Found {len(cross_df):,} cross-service span relationships")

        print(f"\n   Service-to-service call matrix:")
        call_matrix = cross_df.groupby(['parent_service', 'child_service']).size().unstack(fill_value=0)
        print(call_matrix)

        print(f"\n   Most common cross-service patterns:")
        pattern_counts = cross_df.groupby(['parent_service', 'child_service']).size().sort_values(ascending=False)
        for (parent, child), count in pattern_counts.head(10).items():
            print(f"      {parent} → {child}: {count:,} calls")
    else:
        print(f"\n   No cross-service calls found in parent-child relationships")

def visualize_example_traces(df, num_examples=10):
    """Visualize example trace chains showing the complete request flow"""
    print("\n" + "=" * 80)
    print("EXAMPLE TRACE CHAINS")
    print("=" * 80)

    from datetime import datetime

    # Group by anomaly type
    anomaly_types = df['anomaly_type'].unique()

    for anomaly_type in sorted(anomaly_types):
        print(f"\n{'─' * 80}")
        print(f"Anomaly Type: {anomaly_type}")
        print(f"{'─' * 80}")

        # Get traces for this anomaly type
        type_df = df[df['anomaly_type'] == anomaly_type]
        unique_traces = type_df['trace_id'].unique()

        if len(unique_traces) == 0:
            print("  No traces found for this anomaly type")
            continue

        # Prioritize traces with multiple services (more interesting)
        trace_stats = []
        for trace_id in unique_traces:
            # Use full dataframe to get complete trace statistics
            trace_data = df[df['trace_id'] == trace_id]
            num_spans = len(trace_data)
            num_services = trace_data['service_name'].nunique()
            trace_stats.append((trace_id, num_services, num_spans))

        # Sort by: 1) number of services (descending), 2) number of spans (descending)
        trace_stats.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # Filter for complex traces with 3+ services
        complex_traces = [(tid, ns, nsp) for tid, ns, nsp in trace_stats if ns >= 3]

        if len(complex_traces) == 0:
            # Fallback to any multi-service traces
            complex_traces = [(tid, ns, nsp) for tid, ns, nsp in trace_stats if ns >= 2]

        if len(complex_traces) == 0:
            # Show top traces regardless of service count
            complex_traces = trace_stats[:5]

        # Take top 5 most complex traces (no randomness, always show the best examples)
        num_samples = min(5, len(complex_traces))
        sampled_traces = [t[0] for t in complex_traces[:num_samples]]

        for trace_idx, trace_id in enumerate(sampled_traces, 1):
            print(f"\n  Example {trace_idx}: Trace {trace_id[:16]}...")

            # Get all spans for this trace from full dataframe (not filtered by anomaly type)
            trace_spans = df[df['trace_id'] == trace_id].copy()

            # Build parent-child mapping
            span_map = {}
            for _, span in trace_spans.iterrows():
                span_map[span['span_id']] = {
                    'service': span['service_name'],
                    'span_id': span['span_id'],
                    'parent_span_id': span['parent_span_id'],
                    'timestamp': span['timestamp'],
                    'duration_ms': span['duration_ms'],
                    'span_kind': span['span_kind'],
                    'span_name': span['span_name'],
                    'http_method': span['http_method'],
                    'http_target': span['http_target']
                }

            # Find root span(s)
            root_spans = trace_spans[trace_spans['parent_span_id'] == '']

            if len(root_spans) == 0:
                print("    ⚠️  No root span found (incomplete trace)")
                continue

            # Traverse tree from each root
            def print_span_tree(span_id, depth=0, is_last=False, prefix=""):
                """Recursively print the span tree"""
                if span_id not in span_map:
                    return

                span = span_map[span_id]

                # Format timestamp
                try:
                    ts = datetime.fromisoformat(span['timestamp'])
                    time_str = ts.strftime("%H:%M:%S.%f")[:-3]  # milliseconds
                except:
                    time_str = "unknown"

                # Build span info
                kind_map = {0: 'UNSPEC', 1: 'INTERNAL', 2: 'SERVER', 3: 'CLIENT', 4: 'PRODUCER', 5: 'CONSUMER'}
                kind_str = kind_map.get(span['span_kind'], str(span['span_kind']))

                # Format operation name
                op_name = span['span_name']
                if span['http_method'] and span['http_target']:
                    op_name = f"{span['http_method']} {span['http_target']}"
                elif not op_name:
                    op_name = "unknown"

                # Truncate long names
                if len(op_name) > 40:
                    op_name = op_name[:37] + "..."

                # Tree drawing characters
                if depth == 0:
                    connector = "┌─"
                else:
                    connector = "└─" if is_last else "├─"

                # Print span info
                duration_str = f"{span['duration_ms']:.2f}ms"
                print(f"{prefix}{connector} [{span['service']:10s}] {op_name:40s} | {time_str} | {duration_str:10s} | {kind_str}")

                # Find children
                children = [sid for sid, s in span_map.items() if s['parent_span_id'] == span_id]

                # Print children
                for idx, child_id in enumerate(children):
                    is_last_child = (idx == len(children) - 1)
                    child_prefix = prefix + ("   " if is_last or depth == 0 else "│  ")
                    print_span_tree(child_id, depth + 1, is_last_child, child_prefix)

            # Print each root span tree
            for root_idx, (_, root) in enumerate(root_spans.iterrows()):
                print_span_tree(root['span_id'])

            print(f"\n    Total spans in trace: {len(trace_spans)}")

def main():
    # Get input file
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        raise FileNotFoundError(
            "Usage: python3 analyze_trace_relationships.py <path_to_extracted_dataset.csv>"
        )

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    print(f"Loading dataset from: {input_file}")
    df = pd.read_csv(input_file, keep_default_na=False)  # Don't convert empty strings to NaN

    print(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
    print(f"Columns: {', '.join(df.columns)}")

    # Run all analyses
    root_spans, child_spans = analyze_span_relationships(df)
    orphaned_spans = analyze_orphaned_spans(df)
    trace_groups = analyze_trace_structure(df)
    analyze_trace_depth(df)
    analyze_cross_service_calls(df)

    # Visualize example traces
    visualize_example_traces(df)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✅ Dataset integrity:")
    print(f"   - Total spans: {len(df):,}")
    print(f"   - Unique traces: {df['trace_id'].nunique():,}")
    print(f"   - Root spans: {len(root_spans):,}")
    print(f"   - Child spans: {len(child_spans):,}")
    print(f"   - Child spans with valid parents: {len(child_spans) - (len(orphaned_spans) if orphaned_spans is not None else 0):,}")

    if orphaned_spans is None:
        print(f"\n✅ All parent-child relationships are valid!")
        print(f"   The W3CTraceContextPropagator and AsyncLocalStorageContextManager")
        print(f"   are working correctly for distributed tracing.")
    else:
        print(f"\n⚠️  Found {len(orphaned_spans)} orphaned spans that need investigation")

if __name__ == '__main__':
    main()
