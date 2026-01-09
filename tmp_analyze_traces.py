#!/usr/bin/env python3
"""
Temporary script to analyze trace relationships in the labeled dataset
"""

import pandas as pd
import sys

def analyze_traces(csv_file):
    print(f"Analyzing: {csv_file}")
    print("="*80)

    # Read the CSV
    df = pd.read_csv(csv_file)

    print(f"\n1. BASIC DATASET INFO")
    print(f"   Total rows (spans): {len(df)}")
    print(f"   Columns: {list(df.columns)}")

    # Check unique trace_ids
    print(f"\n2. TRACE_ID ANALYSIS")
    unique_traces = df['trace_id'].nunique()
    print(f"   Unique trace_ids: {unique_traces}")
    print(f"   Total spans: {len(df)}")
    print(f"   Avg spans per trace: {len(df) / unique_traces:.2f}")

    # Show sample trace_ids
    print(f"\n   Sample trace_ids (first 5):")
    for tid in df['trace_id'].unique()[:5]:
        count = len(df[df['trace_id'] == tid])
        print(f"     - {tid}: {count} spans")

    # Check parent_span_id relationships
    print(f"\n3. PARENT-CHILD RELATIONSHIPS")
    total_spans = len(df)
    root_spans = df['parent_span_id'].isna().sum()
    child_spans = total_spans - root_spans

    print(f"   Root spans (no parent): {root_spans}")
    print(f"   Child spans (has parent): {child_spans}")

    # Check if parent_span_id values match any span_id values
    all_span_ids = set(df['span_id'].dropna())
    all_parent_ids = set(df['parent_span_id'].dropna())

    matching_parents = all_parent_ids.intersection(all_span_ids)
    orphan_parents = all_parent_ids - all_span_ids

    print(f"\n   Total unique span_ids: {len(all_span_ids)}")
    print(f"   Total unique parent_span_ids (excluding NaN): {len(all_parent_ids)}")
    print(f"   Parent IDs that match span IDs: {len(matching_parents)}")
    print(f"   Parent IDs with NO matching span (orphans): {len(orphan_parents)}")

    if len(matching_parents) > 0:
        print(f"\n   ✅ GOOD: Found {len(matching_parents)} valid parent-child relationships")
    else:
        print(f"\n   ⚠️  WARNING: No valid parent-child relationships found!")

    # Analyze a specific trace in detail
    print(f"\n4. DETAILED TRACE EXAMPLE")
    # Find a trace with multiple spans
    trace_counts = df.groupby('trace_id').size()
    multi_span_traces = trace_counts[trace_counts > 1]

    if len(multi_span_traces) > 0:
        example_trace = multi_span_traces.index[0]
        trace_data = df[df['trace_id'] == example_trace][
            ['trace_id', 'span_id', 'parent_span_id', 'service_name', 'span_name', 'duration_ms']
        ].sort_values('parent_span_id', na_position='first')

        print(f"\n   Example trace: {example_trace}")
        print(f"   Number of spans: {len(trace_data)}")
        print("\n   Spans in this trace:")
        print(trace_data.to_string(index=False))

        # Check if relationships exist within this trace
        trace_span_ids = set(trace_data['span_id'])
        trace_parent_ids = set(trace_data['parent_span_id'].dropna())
        internal_relationships = trace_parent_ids.intersection(trace_span_ids)

        print(f"\n   Internal parent-child links: {len(internal_relationships)}")
        if len(internal_relationships) > 0:
            print(f"   ✅ Trace shows proper MSA service chain")
        else:
            print(f"   ⚠️  Trace spans appear isolated (no internal links)")
    else:
        print("   No traces with multiple spans found")

    # Check anomaly labels
    print(f"\n5. ANOMALY LABEL DISTRIBUTION")
    label_dist = df['anomaly_label'].value_counts()
    print(label_dist.to_string())

    type_dist = df['anomaly_type'].value_counts()
    print(f"\n   Anomaly type distribution:")
    print(type_dist.to_string())

    # Check service distribution
    print(f"\n6. SERVICE DISTRIBUTION")
    service_dist = df['service_name'].value_counts()
    print(service_dist.to_string())

    print("\n" + "="*80)
    print("Analysis complete!")

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "dataset/traces_labeled_20260109_160426.csv"
    analyze_traces(csv_file)
