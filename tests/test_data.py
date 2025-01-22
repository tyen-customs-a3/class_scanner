from pathlib import Path

# Define root path for sample data - use actual path
SAMPLE_DATA_ROOT = Path(__file__).parent.parent / "sample_data"

# Update PBO paths to match actual structure
PBO_PATHS = {
    'babe_em': SAMPLE_DATA_ROOT / "@em/addons/babe_em.pbo",
    'mirrorform': SAMPLE_DATA_ROOT / "@tc_mirrorform/addons/mirrorform.pbo",
    'rhs_headband': SAMPLE_DATA_ROOT / "@tc_rhs_headband/addons/rhs_headband.pbo"
}

# Sample class definitions for testing
CLASS_TEST_DATA = """
class ObjectBase {
    scope = 0;
    model = "";
};

class ItemBase: ObjectBase {
    displayName = "Item";
    weight = 1;
};

class Container {
    items[] = {
        "Item1",
        "Item2"
    };
};

enum DamageType {
    KINETIC = 1,
    EXPLOSIVE = 2,
    FIRE = 3
};
"""

def create_sample_data(root_dir: Path) -> None:
    """Create sample data structure for testing"""
    # Create directories
    root_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample PBOs with content
    for name, content in {
        "core.pbo": CLASS_TEST_DATA,
        "items.pbo": """
            class Inventory_Base: ObjectBase {
                inventorySlots = 10;
            };
        """,
        "weapons.pbo": """
            class Weapon_Base: ItemBase {
                caliber = "5.56";
            };
        """
    }.items():
        pbo_path = root_dir / name
        pbo_path.write_text(content)
