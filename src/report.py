from pydantic import BaseModel
from typing import Literal, List, Optional

class StrategicAlignment(BaseModel):
    objective: str
    status: Literal["On Track", "At Risk", "Off Track"]

class Recommendation(BaseModel):
    priority: Literal["immediate", "short-term", "mid-term", "long-term"]
    action: str
    alternative: Optional[str] = None
    impact: str

class Topic(BaseModel):
    topic: str
    observation: str
    implication: str
    strategic_alignment: StrategicAlignment
    recommendation: Recommendation
    decision_required: str

class ExecutiveSummaryItem(BaseModel):
    objective: str
    status: Literal["On Track", "At Risk", "Off Track"]
    key_decision_needed: str

class Report(BaseModel):
    title: str
    topics: List[Topic]
    executive_summary: List[ExecutiveSummaryItem]
    overall_takeaway: str