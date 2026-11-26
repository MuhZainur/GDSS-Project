from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class Alternative(BaseModel):
    id: str
    name: str
    segment: Optional[str] = None
    desc: Optional[str] = None

class Criterion(BaseModel):
    id: str
    name: str
    unit: Optional[str] = None
    type: str  # "benefit" or "cost"

class DM(BaseModel):
    id: str
    role: str
    name: Optional[str] = None

class DMWeighting(BaseModel):
    mode: str = "ahp"  # "ahp" | "equal"
    pairwise: Optional[List[List[Union[str, int, float]]]] = None
    order: Optional[List[str]] = None

class DMInput(BaseModel):
    criteria: List[str]
    pairwise: List[List[Union[str, int, float]]]
    chosen_method: str = "AHP"  # "AHP", "SAW", "WP", "TOPSIS", "COPELAND"
    submitted_at: Optional[str] = None

class Session(BaseModel):
    session_id: str
    title: str
    goal: str
    company: Optional[str] = "PT NusaCompute (fictional)"
    data_note: Optional[str] = None
    alternatives: List[Alternative]
    criteria: List[Criterion]
    values: Dict[str, Dict[str, float]]
    dms: List[DM]
    dm_weighting: DMWeighting
    dm_inputs: Dict[str, DMInput]
    locked_alternatives: Optional[bool] = True
    status: Optional[str] = "ready"

class TableData(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    highlight: Optional[List[List[int]]] = None

class MatrixData(BaseModel):
    latex: Optional[str] = None

class ResultBox(BaseModel):
    text: str
    status: Optional[str] = "info"  # "info" | "ok" | "warn" | "bad"

class Step(BaseModel):
    id: str
    title: str
    explanation: Optional[str] = None
    table: Optional[TableData] = None
    matrix: Optional[MatrixData] = None
    result: Optional[ResultBox] = None
    formula: Optional[str] = None

class ModelResult(BaseModel):
    model: str
    scope: str = "individual"  # "individual" | "group"
    dm_id: Optional[str] = None
    scores: Dict[str, float]
    ranks: Dict[str, int]
    steps: List[Step] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    normalized: Optional[Dict[str, float]] = None
    contributions: Optional[Dict[str, Dict[str, float]]] = None
    extra: Optional[Dict[str, Any]] = None

class IndividualDMResult(BaseModel):
    role: str
    criteria: List[str]
    criteria_weights: Dict[str, float]
    consistency: Dict[str, Any]
    chosen_method: str
    models: Dict[str, ModelResult]

class DMWeightsResult(BaseModel):
    weights: Dict[str, float]
    lambda_max: float
    CI: float
    CR: float
    steps: List[Step] = Field(default_factory=list)

class RunResult(BaseModel):
    run_id: str
    session_id: str
    created_at: str
    app_version: str = "0.1.0"
    alternatives: List[str]
    alternative_names: Dict[str, str]
    dm_weights: DMWeightsResult
    individual: Dict[str, IndividualDMResult]
    group: Dict[str, ModelResult]
    agreement: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    winners: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
