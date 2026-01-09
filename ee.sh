#!/bin/bash

# print usage information
hp_tmp() {
    echo "Usage: $0 {rm|ls|k6|cp|et|hu|hi|an}"
    echo "  rm   - Remove trace and metric logs in the debug pod"
    echo "  ls   - List contents of the debug pod log directory"
    echo "  k6   - Run k6 load test (args: [mode] [baseline_duration] [duration] [ramp_duration] [anomaly_rate])"
    echo "  cp   - Copy logs from debug pod to local machine"
    echo "  et   - Extract labeled dataset from logs (args: [traces_log_path] [metrics_log_path] [output_log_path])"
    echo "  hu   - Helm uninstall robot-shop"
    echo "  hi   - Helm install robot-shop (args: [version])"
    echo "  an   - Analyze trace relationships (args: [input_file])"
}
rm_tmp() {
	kubectl exec -n robot-shop2 -it deployments/debug-deployment -- sh -c 'echo "{}" > /mnt/otel-logs/traces.json; echo "{}" > /mnt/otel-logs/metrics.json'
}
ls_tmp() {
  kubectl exec -n robot-shop2 -it deployments/debug-deployment -- sh -lc 'LS_COLORS= ls --color=never -lah /mnt/otel-logs/ 2>/dev/null || ls -lah /mnt/otel-logs/'
}
k6_tmp() {
  local mode=${1:-simple}
  local baseline_duration=${2:-10}
  local duration=${3:-5}
  local ramp_duration=${4:-5}
  local anomaly_rate=${5:-0.1}
  echo "Starting k6 load test with baseline_duration=$baseline_duration duration=$duration, ramp_duration=$ramp_duration, anomaly_rate=$anomaly_rate"
	
  kubectl port-forward svc/web 8080:8080 > /dev/null 2>&1 &
	PF_PID=$!
  sleep 5

	k6 run -e BASELINE_DURATION="$baseline_duration" -e DURATION="$duration" -e RAMP_DURATION="$ramp_duration" -e ANOMALY_RATE="$anomaly_rate" /Users/ji/OtherProjects/robot-shop/k6-scripts/"$mode"-trace-scenarios.js
	kill $PF_PID
	wait $PF_PID 2>/dev/null
  echo "Load test completed."
}
cp_tmp() {
  rm -rf /Users/ji/OtherProjects/robot-shop/data/*
  DEBUG_POD=$(kubectl get pods -n robot-shop2 -l app=debug -o jsonpath="{.items[0].metadata.name}")
  kubectl cp -n robot-shop2 "$DEBUG_POD":/mnt/otel-logs/ /Users/ji/OtherProjects/robot-shop/data/
}
et_tmp() {
  TRACES_LOG_PATH=${1:-/Users/ji/OtherProjects/robot-shop/data/traces.json}
  METRICS_LOG_PATH=${2:-/Users/ji/OtherProjects/robot-shop/data/metrics.json}
  OUTPUT_LOG_PATH=${3:-/Users/ji/OtherProjects/robot-shop/data}
  python3 python-scripts/extract-labeled-dataset.py --traces "$TRACES_LOG_PATH" --metrics "$METRICS_LOG_PATH" --output "$OUTPUT_LOG_PATH"
}
an_tmp() {
  python3 python-scripts/analyze_trace_relationships.py "$1"
}
helm_uninstall_tmp() {
  helm uninstall robot-shop -n robot-shop2 --no-hooks
}
helm_install_tmp() {
  VERSION=${1:-"1.0"}
  helm install robot-shop /Users/ji/OtherProjects/robot-shop/K8s/helm -n robot-shop2 --set image.version="$VERSION"
}

# Take one argument(rm, ls, k6, cp, et) to run the corresponding function
case $1 in
    "" | help | -h | --help)
        hp_tmp
        ;;
    rm)
        rm_tmp
        ;;
    ls)
        ls_tmp
        ;;
    k6)
        k6_tmp "$2" "$3" "$4" "$5" 
        ;;
    cp)
        cp_tmp
        ;;
    et)
        et_tmp "$2" "$3" "$4"
        ;;
    hu)
        helm_uninstall_tmp
        ;;
    hi)
        helm_install_tmp "$2"
        ;;
    an)
        an_tmp "$2"
        ;;
    *)
        echo "Invalid option: $1"
        hp_tmp
        exit 1
        ;;
esac
