"""
Incident scenarios: 5 easy, 3 medium, 2 hard.
Each has alert data (shown to agent) and correct_answer (used for grading).
"""

AVAILABLE_TEAMS = ["backend", "frontend", "database", "network", "security", "devops"]

SCENARIOS = {
    # ═══════════════════════════════════════════════════════════════
    #  EASY — single alert, classify severity only
    # ═══════════════════════════════════════════════════════════════
    "easy": [
        {
            "id": "easy_01",
            "alerts": [{
                "id": "A",
                "title": "Payment service completely down",
                "message": (
                    "CRITICAL: All payment processing has stopped. "
                    "Transaction success rate: 0%. "
                    "Customer-facing error: 'Unable to process payment'. "
                    "Duration: 25 minutes and counting."
                ),
                "service": "payment-service",
                "timestamp": "2024-03-15T02:34:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P1"},
        },
        {
            "id": "easy_02",
            "alerts": [{
                "id": "A",
                "title": "Elevated 404 errors on blog pages",
                "message": (
                    "WARNING: 404 error rate on /blog/* endpoints "
                    "increased from 0.5% to 3.2%. "
                    "All other services operating normally. "
                    "No customer complaints received."
                ),
                "service": "content-service",
                "timestamp": "2024-03-15T10:15:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P4"},
        },
        {
            "id": "easy_03",
            "alerts": [{
                "id": "A",
                "title": "Login failures spiking",
                "message": (
                    "ALERT: Login failure rate jumped to 40%. "
                    "Users reporting 'unable to sign in' on social media. "
                    "Approximately 12,000 users affected in last 10 minutes."
                ),
                "service": "auth-service",
                "timestamp": "2024-03-15T18:00:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P1"},
        },
        {
            "id": "easy_04",
            "alerts": [{
                "id": "A",
                "title": "Disk usage warning on logging server",
                "message": (
                    "INFO: Disk usage on log-aggregator-02 reached 72%. "
                    "Growth rate: 2% per day. "
                    "Estimated time to full: 14 days. "
                    "No impact on production services."
                ),
                "service": "logging-infra",
                "timestamp": "2024-03-15T06:00:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P4"},
        },
        {
            "id": "easy_05",
            "alerts": [{
                "id": "A",
                "title": "Search service degraded",
                "message": (
                    "ALERT: Search response times increased 5x "
                    "(from 200ms to 1000ms). Search results still "
                    "returning but very slowly. "
                    "Affects product search on main site. "
                    "~30% of users likely experiencing delays."
                ),
                "service": "search-service",
                "timestamp": "2024-03-15T14:20:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P2"},
        },
    ],

    # ═══════════════════════════════════════════════════════════════
    #  MEDIUM — alert + logs + metrics → severity + root cause + team
    # ═══════════════════════════════════════════════════════════════
    "medium": [
        {
            "id": "medium_01",
            "alerts": [{
                "id": "A",
                "title": "Checkout service response time spike",
                "message": (
                    "ALERT: p99 response time on checkout-service "
                    "jumped from 500ms to 12,000ms. "
                    "Error rate: 15% and climbing."
                ),
                "service": "checkout-service",
                "timestamp": "2024-03-15T02:34:00Z",
            }],
            "logs": [
                "checkout-service: WARN  - DB query took 8500ms (usually 50ms)",
                "checkout-service: ERROR - Connection pool exhausted, 200 waiting",
                "PostgreSQL: LOG  - max_connections (100) reached, rejecting new",
                "checkout-service: WARN  - Falling back to read replica... failed",
            ],
            "metrics": {
                "db_cpu": "95%",
                "db_connections": "100/100",
                "app_cpu": "12%",
                "app_memory": "45%",
            },
            "correct_answer": {
                "severity": "P2",
                "root_cause": "database_connection_pool_exhaustion",
                "assigned_team": "database",
            },
        },
        {
            "id": "medium_02",
            "alerts": [{
                "id": "A",
                "title": "Spike in 403 Forbidden responses",
                "message": (
                    "ALERT: 403 response rate on /api/* increased "
                    "from 0.1% to 25% in last 5 minutes. "
                    "Multiple geographic regions affected."
                ),
                "service": "api-gateway",
                "timestamp": "2024-03-15T11:45:00Z",
            }],
            "logs": [
                "api-gateway: WARN  - Rate limiter triggered for 850 unique IPs",
                "api-gateway: INFO  - WAF rule 'sql-injection-detect' blocking",
                "api-gateway: ERROR - GeoIP database update at 11:40 changed 12 rules",
                "api-gateway: WARN  - Legitimate user tokens rejected post-update",
            ],
            "metrics": {
                "blocked_requests_per_sec": "2400",
                "legitimate_traffic_estimate": "85%",
                "waf_false_positive_rate": "high",
            },
            "correct_answer": {
                "severity": "P2",
                "root_cause": "waf_geoip_misconfiguration",
                "assigned_team": "security",
            },
        },
        {
            "id": "medium_03",
            "alerts": [{
                "id": "A",
                "title": "Memory leak on recommendation engine",
                "message": (
                    "ALERT: recommendation-service memory usage grew "
                    "from 2GB to 14GB over 6 hours. "
                    "OOMKill expected within 1 hour. "
                    "Recommendations still serving but degraded."
                ),
                "service": "recommendation-service",
                "timestamp": "2024-03-15T08:00:00Z",
            }],
            "logs": [
                "recommendation-service: WARN  - Heap usage 87%, GC pause 800ms",
                "recommendation-service: INFO  - Model cache size: 11.2GB (limit 16GB)",
                "recommendation-service: DEBUG - New model loaded at 02:00, old not evicted",
                "recommendation-service: WARN  - Response latency p99: 3200ms (SLA: 500ms)",
            ],
            "metrics": {
                "memory_usage": "14GB/16GB",
                "gc_pause_time": "800ms",
                "model_cache_entries": "2 (expected: 1)",
                "service_uptime": "6h since last deploy",
            },
            "correct_answer": {
                "severity": "P3",
                "root_cause": "memory_leak_from_unevicted_model_cache",
                "assigned_team": "backend",
            },
        },
    ],

    # ═══════════════════════════════════════════════════════════════
    #  HARD — multiple alerts, cascading failure
    # ═══════════════════════════════════════════════════════════════
    "hard": [
        {
            "id": "hard_01",
            "alerts": [
                {
                    "id": "A",
                    "title": "Payment service 500 errors spiking",
                    "message": (
                        "CRITICAL: payment-service returning 500 errors. "
                        "Error rate: 78%. Revenue impact estimated."
                    ),
                    "service": "payment-service",
                    "timestamp": "2024-03-15T02:30:00Z",
                },
                {
                    "id": "B",
                    "title": "Redis cache memory critical",
                    "message": (
                        "ALERT: redis-cache-01 memory at 99%. "
                        "Key eviction rate: 5000/sec. "
                        "Cache hit ratio dropped from 95% to 12%."
                    ),
                    "service": "redis-cache",
                    "timestamp": "2024-03-15T02:28:00Z",
                },
                {
                    "id": "C",
                    "title": "Auth service timeouts",
                    "message": (
                        "ALERT: user-auth-service experiencing timeouts. "
                        "p99 latency: 30,000ms. Token validation failing."
                    ),
                    "service": "auth-service",
                    "timestamp": "2024-03-15T02:31:00Z",
                },
            ],
            "logs": [
                "redis-cache-01: WARN  - maxmemory reached, evicting volatile keys",
                "redis-cache-01: ERROR - Background save failed: not enough memory",
                "payment-service: ERROR - Cache miss, falling back to PostgreSQL",
                "payment-service: ERROR - DB query timeout after 10000ms",
                "auth-service: WARN  - Token cache unavailable, validating via DB",
                "auth-service: ERROR - upstream connect timeout to payment-service",
            ],
            "metrics": {
                "redis_memory": "99%",
                "redis_eviction_rate": "5000/sec",
                "payment_error_rate": "78%",
                "auth_timeout_rate": "45%",
                "db_connections": "95/100",
                "db_cpu": "88%",
            },
            "correct_answer": {
                "root_cause_alert": "B",
                "severity": "P1",
                "priority_order": ["B", "A", "C"],
                "actions": {
                    "B": "increase_redis_memory_and_flush_stale_keys",
                    "A": "monitor_will_recover_after_redis_fix",
                    "C": "monitor_will_recover_after_redis_fix",
                },
                "assigned_team": "database",
            },
        },
        {
            "id": "hard_02",
            "alerts": [
                {
                    "id": "A",
                    "title": "CDN origin pull errors",
                    "message": (
                        "ALERT: CDN reporting 40% origin pull failures. "
                        "Static assets failing to load for users."
                    ),
                    "service": "cdn",
                    "timestamp": "2024-03-15T15:00:00Z",
                },
                {
                    "id": "B",
                    "title": "Load balancer health check failures",
                    "message": (
                        "ALERT: 3 of 8 backend servers failing health checks. "
                        "Traffic redistributed to remaining 5."
                    ),
                    "service": "load-balancer",
                    "timestamp": "2024-03-15T14:58:00Z",
                },
                {
                    "id": "C",
                    "title": "Deployment pipeline completed",
                    "message": (
                        "INFO: Deployment v2.4.1 rolled out to production. "
                        "Canary passed. Full rollout completed at 14:55."
                    ),
                    "service": "deploy-pipeline",
                    "timestamp": "2024-03-15T14:55:00Z",
                },
            ],
            "logs": [
                "web-server-03: ERROR - Segfault in new image processing module",
                "web-server-05: ERROR - Segfault in new image processing module",
                "web-server-07: ERROR - Segfault in new image processing module",
                "deploy-pipeline: INFO  - v2.4.1 includes new image-resize library",
                "load-balancer: INFO  - Removed web-server-03,05,07 from pool",
                "cdn: WARN  - Origin returning 502 for /static/images/* paths",
            ],
            "metrics": {
                "healthy_servers": "5/8",
                "error_rate": "35%",
                "deploy_time": "14:55 UTC",
                "first_error_time": "14:56 UTC",
            },
            "correct_answer": {
                "root_cause_alert": "C",
                "severity": "P1",
                "priority_order": ["C", "B", "A"],
                "actions": {
                    "C": "rollback_deployment_v2.4.1",
                    "B": "will_recover_after_rollback",
                    "A": "will_recover_after_rollback",
                },
                "assigned_team": "backend",
            },
        },
    ],
}
