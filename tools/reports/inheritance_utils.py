from collections import defaultdict
from typing import Dict, Set, List, Tuple, Optional
from .types import ReportData


class InheritanceMapper:
    def __init__(self, report_data: ReportData):
        self.report_data = report_data
        self.inheritance_map: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
        self.container_map: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
        self.reverse_map: Dict[str, str] = {}
        self.class_info: Dict[str, Dict] = {}
        self._inheritance_chains: Dict[str, List[str]] = {}
        self._inheritance_paths: Dict[str, Set[str]] = {}
        self._inheritance_loops: Set[str] = set()  # Track classes involved in inheritance loops
        self._build_maps()
        self._precalculate_inheritance_paths()

    def _build_maps(self) -> None:
        """Build inheritance and container maps from report data with loop detection"""
        # First pass: build basic maps
        for pbo in self.report_data.get("pbos", []):
            for cls in pbo.get("classes", []):
                if not isinstance(cls, dict) or not cls.get("name"):
                    continue

                name = cls["name"]
                parent = cls.get("parent", "")
                container = cls.get("container", "")
                config_type = cls.get("config_type", "default")

                self.class_info[name] = {
                    "config_type": config_type,
                    "category": cls.get("category", "Uncategorized"),
                    "parent": parent,
                    "container": container,
                    "display_name": cls.get("display_name")
                }

                if parent:
                    self.inheritance_map[parent][config_type].add(name)
                    self.reverse_map[name] = parent
                if container:
                    self.container_map[container][config_type].add(name)

        # Second pass: detect inheritance loops
        for class_name in self.class_info:
            visited = set()
            current = class_name
            while current in self.reverse_map:
                if current in visited:
                    # Found a loop - mark all classes in the loop
                    loop_start = current
                    loop_current = self.reverse_map[current]
                    self._inheritance_loops.add(current)
                    while loop_current != loop_start:
                        self._inheritance_loops.add(loop_current)
                        loop_current = self.reverse_map[loop_current]
                    # Break the loop by removing the inheritance relationship
                    del self.reverse_map[current]
                    break
                visited.add(current)
                current = self.reverse_map[current]

    def _precalculate_inheritance_paths(self) -> None:
        """Pre-calculate all inheritance paths for faster lookups, handling loops"""
        self._inheritance_paths = {}
        for class_name in self.class_info:
            if class_name in self._inheritance_loops:
                # For classes in loops, only include the class itself
                self._inheritance_paths[class_name] = {class_name}
                continue

            path = set()
            current = class_name
            while current in self.reverse_map:
                path.add(current)
                current = self.reverse_map[current]
            path.add(current)
            self._inheritance_paths[class_name] = path

    def get_inheritance_chain(self, class_name: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Get the full inheritance chain for a class (cached), handling loops"""
        if class_name in self._inheritance_chains:
            return self._inheritance_chains[class_name].copy()

        if class_name in self._inheritance_loops:
            # For classes in loops, return only the class itself
            chain = [class_name]
            self._inheritance_chains[class_name] = chain
            return chain.copy()

        if visited is None:
            visited = set()

        if class_name in visited:
            return []

        visited.add(class_name)
        chain = [class_name]

        parent = self.reverse_map.get(class_name)
        if parent:
            parent_chain = self.get_inheritance_chain(parent, visited)
            chain.extend(parent_chain)

        self._inheritance_chains[class_name] = chain
        return chain.copy()

    def find_root_classes(self, config_type: str) -> Set[str]:
        """Find root classes for a specific config type"""
        return {
            name for name, info in self.class_info.items()
            if info["config_type"] == config_type and (
                not info["parent"] or
                info["parent"] not in self.class_info or
                self.class_info[info["parent"]]["config_type"] != config_type
            )
        }

    def get_all_children(self, class_name: str, config_type: str) -> Set[str]:
        """Get all children (inheritance and container) for a class"""
        children = set()
        if class_name in self.inheritance_map and config_type in self.inheritance_map[class_name]:
            children.update(self.inheritance_map[class_name][config_type])
        if class_name in self.container_map and config_type in self.container_map[class_name]:
            children.update(self.container_map[class_name][config_type])
        return children

    def get_config_types(self) -> List[str]:
        """Get sorted list of all config types"""
        return sorted(set(
            info["config_type"] for info in self.class_info.values()
        ))

    def inherits_from_any(self, class_name: str, root_classes: Set[str]) -> bool:
        """Check if a class inherits from any of the given root classes using pre-calculated paths"""
        return bool(self._inheritance_paths[class_name] & root_classes)

    def get_inheritance_loops(self) -> Set[str]:
        """Return set of class names involved in inheritance loops"""
        return self._inheritance_loops.copy()
