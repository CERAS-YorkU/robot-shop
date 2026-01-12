-- OpenTelemetry Collector MySQL Permissions
-- Required for metrics collection from performance_schema

-- Grant SELECT on performance_schema tables
GRANT SELECT ON performance_schema.* TO 'shipping'@'%';

-- Grant PROCESS privilege for InnoDB metrics
GRANT PROCESS ON *.* TO 'shipping'@'%';

-- Apply changes
FLUSH PRIVILEGES;
