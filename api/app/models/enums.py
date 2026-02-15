from enum import Enum


class ChannelEnum(str, Enum):
    vapi = "vapi"
    internal = "internal"
    webform = "webform"


class PainCategoryEnum(str, Enum):
    onboarding = "onboarding"
    approvals = "approvals"
    reporting = "reporting"
    comms = "comms"
    finance_ops = "finance_ops"
    sales_ops = "sales_ops"
    client_ops = "client_ops"
    access_mgmt = "access_mgmt"
    other = "other"


class AutomationTypeEnum(str, Enum):
    low_code = "low_code"
    api_integration = "api_integration"
    ai_assist = "ai_assist"
    internal_tool = "internal_tool"
    process_change = "process_change"
