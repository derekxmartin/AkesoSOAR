"""Enumeration types for AkesoSOAR models."""

import enum


class UseCaseStatus(enum.StrEnum):
    DRAFT = "draft"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class Severity(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class EscalationPolicy(enum.StrEnum):
    AUTO = "auto"
    MANUAL = "manual"
    CONDITIONAL = "conditional"


class PlaybookTriggerType(enum.StrEnum):
    ALERT = "alert"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class ExecutionStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class StepType(enum.StrEnum):
    ACTION = "action"
    CONDITION = "condition"
    HUMAN_TASK = "human_task"
    TRANSFORM = "transform"
    PARALLEL = "parallel"


class ConnectorType(enum.StrEnum):
    REST = "rest"
    GRPC = "grpc"


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    SOC_MANAGER = "soc_manager"
    SOC_L3 = "soc_l3"
    SOC_L2 = "soc_l2"
    SOC_L1 = "soc_l1"
    READ_ONLY = "read_only"


class HumanTaskStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    ESCALATED = "escalated"
