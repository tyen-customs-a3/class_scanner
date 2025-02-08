from typing import Literal, TypeAlias

# Config section names as literals
CFG_PATCHES: Literal["CfgPatches"] = "CfgPatches"
CFG_WEAPONS: Literal["CfgWeapons"] = "CfgWeapons"
CFG_VEHICLES: Literal["CfgVehicles"] = "CfgVehicles"
CFG_GLOBAL: Literal["_global"] = "_global"

# Type alias for config sections
ConfigSectionName: TypeAlias = Literal[
    "CfgPatches",
    "CfgWeapons",
    "CfgVehicles",
    "_global"
]

ALL_CONFIG_SECTIONS = (CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES, CFG_GLOBAL)
