from typing import Dict, Any, List, TypedDict, Optional

class ClassInfo(TypedDict):
    name: str
    parent: str
    properties: Dict[str, Any]
    config_type: str
    category: str
    container: str
    display_name: Optional[str]

class PboInfo(TypedDict):
    name: str
    class_count: int
    classes: List[ClassInfo]

class ReportData(TypedDict):
    timestamp: str
    total_pbos: int
    total_classes: int
    total_properties: int
    pbos: List[PboInfo]
