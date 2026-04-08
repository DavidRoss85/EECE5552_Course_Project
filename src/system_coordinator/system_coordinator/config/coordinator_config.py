"""
Coordinator Configuration
-------------------------
Preset positions, orientations, and other parameters for the orchestrator node.

All coordinates are in the 'world' frame unless otherwise noted.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Pose type definitions
# ---------------------------------------------------------------------------

# (x, y, z) position tuple
Position = Tuple[float, float, float]

# (x, y, z, w) quaternion tuple (w last, ROS convention)
Orientation = Tuple[float, float, float, float]

# Combined pose: (position, orientation)
Pose = Tuple[Position, Orientation]


# ---------------------------------------------------------------------------
# Standard orientations
# ---------------------------------------------------------------------------

class StandardOrientations:
    """Common orientations for robot poses."""
    
    # Identity quaternion (no rotation)
    IDENTITY = (0.0, 0.0, 0.0, 1.0)
    
    # Gripper pointing straight down (90-deg rotation around Y axis)
    GRIPPER_DOWN = (0.0, 0.7071068, 0.0, 0.7071068)
    
    # Gripper pointing forward (no rotation from world frame)
    GRIPPER_FORWARD = (0.0, 0.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Coordinator configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CoordinatorConfig:
    """
    Configuration for the orchestrator node.
    
    All preset positions and operational parameters are defined here
    to keep the main node logic clean and maintainable.
    """
    
    # ── Timing parameters ────────────────────────────────────────────────────
    handoff_timeout_s: float = 30.0      # Max time for handoff phase
    home_timeout_s: float = 15.0         # Max time to return home
    retreat_pause_s: float = 2.0         # Pause after VLA before handoff actions
    homing_pause_s: float = 3.0          # Time to complete homing motion
    
    # ── Gripper positions ────────────────────────────────────────────────────
    gripper_open_pos: float = 1.0        # Open gripper command value
    gripper_closed_pos: float = 0.0      # Closed gripper command value
    
    # ── Behavior flags ───────────────────────────────────────────────────────
    auto_handoff: bool = True             # Auto proceed to handoff, or wait for user
    safety_open_gripper_on_error: bool = True  # Open gripper in error states
    
    # ── Preset positions ─────────────────────────────────────────────────────
    
    # Home position — safe neutral pose for the arm
    home_position: Position = (0.0, -0.3, 0.6)
    home_orientation: Orientation = StandardOrientations.GRIPPER_FORWARD
    
    # Safe retreat position — move here after VLA is done, before specific actions
    retreat_position: Position = (0.0, 0.0, 0.5)
    retreat_orientation: Orientation = StandardOrientations.GRIPPER_DOWN
    
    # Place/drop positions — where to put objects after picking them up
    place_positions: Dict[str, Pose] = None  # Will be set in __post_init__
    
    # Inspection position — move here to get a better view of the workspace
    inspect_position: Position = (0.2, 0.0, 0.4)
    inspect_orientation: Orientation = StandardOrientations.GRIPPER_DOWN
    
    # Emergency stop position — safe position if something goes wrong
    emergency_position: Position = (0.0, 0.0, 0.7)
    emergency_orientation: Orientation = StandardOrientations.IDENTITY
    
    def __post_init__(self):
        """Set up place_positions dictionary after initialization."""
        if self.place_positions is None:
            # Default place positions — can be overridden in launch files or configs
            object.__setattr__(self, 'place_positions', {
                'bin': ((0.3, -0.2, 0.4), StandardOrientations.GRIPPER_DOWN),
                'shelf': ((-0.2, 0.3, 0.5), StandardOrientations.GRIPPER_DOWN),
                'table_center': ((0.0, 0.2, 0.35), StandardOrientations.GRIPPER_DOWN),
                'drop_zone': ((0.4, 0.0, 0.3), StandardOrientations.GRIPPER_DOWN),
            })
    
    # ── Pose access helpers ──────────────────────────────────────────────────
    
    @property
    def home_pose(self) -> Pose:
        """Complete home pose (position + orientation)."""
        return (self.home_position, self.home_orientation)
    
    @property
    def retreat_pose(self) -> Pose:
        """Complete retreat pose (position + orientation)."""
        return (self.retreat_position, self.retreat_orientation)
    
    @property
    def inspect_pose(self) -> Pose:
        """Complete inspection pose (position + orientation)."""
        return (self.inspect_position, self.inspect_orientation)
    
    @property
    def emergency_pose(self) -> Pose:
        """Complete emergency pose (position + orientation)."""
        return (self.emergency_position, self.emergency_orientation)
    
    def get_place_pose(self, location: str) -> Pose:
        """
        Get a place pose by name.
        
        Args:
            location: Key from place_positions dict ('bin', 'shelf', etc.)
            
        Returns:
            (position, orientation) tuple
            
        Raises:
            KeyError: If location is not defined
        """
        if location not in self.place_positions:
            available = list(self.place_positions.keys())
            raise KeyError(f"Unknown place location '{location}'. Available: {available}")
        return self.place_positions[location]


# ---------------------------------------------------------------------------
# Default configuration instance
# ---------------------------------------------------------------------------

STD_COORDINATOR_CFG = CoordinatorConfig()