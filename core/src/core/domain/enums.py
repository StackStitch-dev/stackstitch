from __future__ import annotations

from enum import Enum


class StreamType(str, Enum):
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    REVIEW = "review"


class MetricType(str, Enum):
    PR_CYCLE_TIME = "pr_cycle_time"
    PR_THROUGHPUT = "pr_throughput"
    REVIEW_TURNAROUND_TIME = "review_turnaround_time"


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationTrigger(str, Enum):
    ANOMALY = "anomaly"
    ADHOC = "adhoc"


class InsightType(str, Enum):
    ANOMALY_EXPLANATION = "anomaly_explanation"
    PATTERN_DETECTION = "pattern_detection"
    AD_HOC_RESPONSE = "ad_hoc_response"


class InvocationSource(str, Enum):
    USER_MESSAGE = "user_message"
    INSIGHT = "insight"


class InvocationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"


class InvestigationStepType(str, Enum):
    TOOL_CALL = "tool_call"
    REASONING = "reasoning"
    OBSERVATION = "observation"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AnomalySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
