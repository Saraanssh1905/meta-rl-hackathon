"""
Incident scenarios: 6 easy, 3 medium, 2 hard.
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
                    "CRITICAL: All payment processing has stopped. Affects all users. "
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
                    "INFO: Minor issue detected. Informational only. No user impact. "
                    "404 error rate on /blog/* endpoints increased slightly "
                    "No user impact. No action required. "
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
                    "Critical outage: Login system failing. "
                    "Failure rate at 40%. Users unable to sign in. "
                    "High business impact."
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
                    "INFO: Informational only. No user impact. "
                    "Disk usage at 72%, expected to fill in 14 days. "
                    "Monitoring recommended. "
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
                    "ALERT: Major degradation in search service. Affects ~30% of users. "
                    "Latency increased from 200ms to 1000ms. "
                    "Affects ~30% of users. Service still operational."
                    ),
                "service": "search-service",
                "timestamp": "2024-03-15T14:20:00Z",
            }],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P2"},
        },
        {
            "id": "easy_06",
            "alerts": [{
                "id": "A",
                "title": "Slight increase in API latency",
                "message": (
                    "Minor issue. Limited user impact. "
                    "API latency increased from 200ms to 350ms. "
                    "Affects less than 5% of users. "
                    "No immediate action required."
                    ),
                "service": "api-service",
                "timestamp": "2024-03-15T12:00:00Z",
            }
            ],
            "logs": [],
            "metrics": {},
            "correct_answer": {"severity": "P3"},
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
                "PostgreSQL: ERROR - connection_pool_exhaustion detected",
                "PostgreSQL: WARN  - rejecting new connections",
                "checkout-service: ERROR - DB query took 8500ms (normal: 50ms)",
                "checkout-service: ERROR - Connection pool exhausted (200 waiting)",
            ],
            "metrics": {
                "db_cpu": "95%",
                "db_connections": "100/100",
                "app_cpu": "12%",
                "app_memory": "45%",
            },
            "correct_answer": {
                "severity": "P2",
                "root_cause": "db_connection_pool_exhaustion",
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
                "api-gateway: ERROR - false positives detected in GeoIP rule",
                "api-gateway: INFO  - WAF rule update applied at 11:40",
                "api-gateway: WARN  - sudden spike in blocked legitimate traffic",
                "api-gateway: WARN  - valid user tokens rejected",
            ],
            "metrics": {
                "blocked_requests_per_sec": "2400",
                "legitimate_traffic_estimate": "85%",
                "waf_false_positive_rate": "high",
            },
            "correct_answer": {
                "severity": "P2",
                "root_cause": "geoip_waf_misconfiguration",
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
                "recommendation-service: ERROR - mdoel_cache_memory_leak detected",
                "recommendation-service: DEBUG - New model loaded at 02:00, old not evicted",
                
                "recommendation-service: WARN  - Heap usage 87%, GC pause 800ms",
                "recommendation-service: INFO  - Model cache size: 11.2GB (limit 16GB)",
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
                "root_cause": "model_cache_memory_leak",
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
            # CAUSE
                "redis-cache-01: ERROR - maxmemory reached, evictions increasing rapidly",
                "redis-cache-01: WARN  - cache hit ratio dropped from 95% to 12%",
                "redis-cache-01: INFO  - cache instability detected (PRIMARY FAILURE)",

                # EFFECT
                "payment-service: INFO - failures started AFTER redis degradation",
                "payment-service: ERROR - cache unavailable, falling back to DB",
                "auth-service: INFO  - latency spike correlates with redis failure",
                "auth-service: WARN  - token cache unavailable (redis)",

                # CASCADE
                "payment-service: ERROR - DB overloaded, query timeout 10000ms",
                "auth-service: ERROR - increased DB dependency causing timeouts",

                # REASONING HINT (subtle, inside logs)
                "SYSTEM: Primary root cause occurs BEFORE cascading failures",
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
                # CAUSE
                "deploy-pipeline: INFO  - v2.4.1 deployed new image processing module",
                "deploy-pipeline: INFO  - deployment completed at 14:55 (PRIMARY EVENT)",

                # EFFECT
                "web-server-03: ERROR - segfault after deployment",
                "web-server-05: ERROR - segfault after deployment",
                "web-server-07: ERROR - segfault after deployment",
                "load-balancer: INFO  - failures began AFTER deployment",

                # CASCADE
                "load-balancer: WARN  - removing unhealthy servers",
                "cdn: INFO  - origin errors started AFTER backend crash",
                "cdn: ERROR - origin returning 502 due to backend failures",

                # REASONING HINT
                "SYSTEM: Root cause typically appears before downstream failures",
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
