from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from pathlib import Path
from datetime import datetime
from ..models import ClassHierarchy

@dataclass(frozen=True)
class ScanResult:
    """Results from scanning operation"""
    hierarchies: Dict[str, ClassHierarchy]
    errors: Dict[str, str] = field(default_factory=dict)  # path -> error message
    skipped: Set[Path] = field(default_factory=set)  # skipped files
    scan_time: datetime = field(default_factory=datetime.now)
    
    @property
    def total_classes(self) -> int:
        """Get total number of classes found"""
        return sum(len(h.classes) for h in self.hierarchies.values())
    
    @property
    def success(self) -> bool:
        """Check if scan was successful"""
        return bool(self.hierarchies) and not self.errors

    @classmethod
    def from_scan(cls, hierarchies: Dict[str, ClassHierarchy], 
                 errors: Dict[str, str], skipped: Set[Path]) -> 'ScanResult':
        """Create scan result from scan operation"""
        return cls(
            hierarchies=hierarchies,
            errors=errors,
            skipped=skipped,
            scan_time=datetime.now()
        )

    @classmethod
    def error(cls, error_path: Path, error_msg: str) -> 'ScanResult':
        """Create error result"""
        return cls(
            hierarchies={},
            errors={str(error_path): error_msg},
            skipped=set()
        )

@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation issue"""
    class_name: str
    issue_type: str  # 'missing_parent', 'invalid_inheritance', 'invalid_property'
    message: str
    suggested_fixes: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class ValidationResult:
    """Results from validation operation"""
    valid: bool
    addon_name: str
    issues: List[ValidationIssue] = field(default_factory=list)
    missing_parents: Set[str] = field(default_factory=set)
    invalid_inheritance: Dict[str, List[str]] = field(default_factory=dict)
    validation_time: datetime = field(default_factory=datetime.now)
    
    @property
    def has_issues(self) -> bool:
        """Check if validation found any issues"""
        return not self.valid or bool(self.issues)
    
    def get_issues_by_type(self, issue_type: str) -> List[ValidationIssue]:
        """Get all issues of a specific type"""
        return [i for i in self.issues if i.issue_type == issue_type]

@dataclass(frozen=True)
class BatchValidationResult:
    """Results from validating multiple addons"""
    results: Dict[str, ValidationResult]  # addon_name -> result
    total_addons: int
    valid_addons: int
    start_time: datetime
    end_time: datetime = field(default_factory=datetime.now)
    
    @property
    def validation_duration(self) -> float:
        """Get validation duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Get percentage of valid addons"""
        return (self.valid_addons / self.total_addons * 100) if self.total_addons else 0
    
    def get_invalid_addons(self) -> Dict[str, ValidationResult]:
        """Get results for invalid addons only"""
        return {
            name: result for name, result in self.results.items()
            if result.has_issues
        }

@dataclass(frozen=True)
class ScanStats:
    """Statistical information about a scan operation"""
    total_files: int
    processed_files: int
    error_count: int
    total_classes: int
    unique_classes: int
    scan_duration: float
    memory_usage: float  # in MB
    start_time: datetime
    end_time: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, start_time: datetime, **stats) -> 'ScanStats':
        """Create stats with end time and duration calculation"""
        end_time = datetime.now()
        return cls(
            start_time=start_time,
            end_time=end_time,
            scan_duration=(end_time - start_time).total_seconds(),
            **stats
        )
