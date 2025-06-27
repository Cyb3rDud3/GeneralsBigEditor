import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog
from typing import Dict, List, Tuple, Optional, Any, Set
import uuid
from dataclasses import dataclass, field
from enum import Enum
import math
class ConnectionType(Enum):
    # Existing types
    WEAPON_SLOT = "weapon_slot"
    ARMOR_SET = "armor_set"
    LOCOMOTOR_SET = "locomotor_set"
    PREREQUISITE = "prerequisite"
    UPGRADE_GRANTS = "upgrade_grants"
    DEATH_SPAWN = "death_spawn"
    PROJECTILE_REF = "projectile_ref"
    FX_REF = "fx_ref"
    SOUND_REF = "sound_ref"
    COMMAND_REF = "command_ref"
    CONFLICTS_WITH = "conflicts_with"
    TRIGGERED_BY = "triggered_by"
    
    # New relationship types
    OWNS = "owns"  # General owns unit
    PART_OF = "part_of"  # Unit is part of general
    REPLACES = "replaces"  # Upgrade replaces component
# Enhanced node types with clearer categories
class NodeCategory(Enum):
    FACTION = "faction"
    ENTITY = "entity"
    COMPONENT = "component"
    EFFECT = "effect"
    LOGIC = "logic"

class NodeType(Enum):
    # Faction nodes
    GENERAL = "general"
    
    # Entity nodes
    UNIT = "unit"
    BUILDING = "building"
    PROJECTILE = "projectile"
    
    # Component nodes
    WEAPON = "weapon"
    ARMOR = "armor"
    LOCOMOTOR = "locomotor"
    
    # Effect nodes
    PARTICLESYSTEM = "particlesystem"
    FXLIST = "fxlist"
    SOUND = "sound"
    
    # Logic nodes
    SCIENCE = "science"
    UPGRADE = "upgrade"
    SPECIALPOWER = "specialpower"
    COMMANDSET = "commandset"
    COMMANDBUTTON = "commandbutton"
    
    # System nodes
    OCL = "objectcreationlist"
    BEHAVIOR = "behavior"

# Property metadata for validation
@dataclass
class PropertyMetadata:
    name: str
    display_name: str
    property_type: str  # "number", "text", "choice", "boolean", "reference"
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: List[str] = field(default_factory=list)
    description: str = ""
    category: str = "General"
    read_only: bool = False
    affects_balance: bool = False

class PropertyRegistry:
    """Registry of known properties with metadata for validation"""
    
    def __init__(self):
        self.properties = {}
        self._register_default_properties()
        
    def _register_default_properties(self):
        """Register known properties with their metadata"""
        # Unit properties
        self.register("BuildCost", PropertyMetadata(
            name="BuildCost",
            display_name="Cost",
            property_type="number",
            default_value=1000,
            min_value=0,
            max_value=10000,
            description="Cost to build this unit",
            category="Economy",
            affects_balance=True
        ))
        
        self.register("BuildTime", PropertyMetadata(
            name="BuildTime",
            display_name="Build Time",
            property_type="number",
            default_value=10.0,
            min_value=0.1,
            max_value=120.0,
            description="Time in seconds to build",
            category="Economy",
            affects_balance=True
        ))
        
        self.register("VisionRange", PropertyMetadata(
            name="VisionRange",
            display_name="Vision Range",
            property_type="number",
            default_value=150,
            min_value=50,
            max_value=500,
            description="How far the unit can see",
            category="Combat"
        ))
        
        # Weapon properties
        self.register("PrimaryDamage", PropertyMetadata(
            name="PrimaryDamage",
            display_name="Damage",
            property_type="number",
            default_value=50,
            min_value=0,
            max_value=1000,
            description="Base damage dealt",
            category="Weapon",
            affects_balance=True
        ))
        
        self.register("AttackRange", PropertyMetadata(
            name="AttackRange",
            display_name="Attack Range",
            property_type="number",
            default_value=150,
            min_value=0,
            max_value=500,
            description="Maximum attack distance",
            category="Weapon",
            affects_balance=True
        ))
        
        self.register("DamageType", PropertyMetadata(
            name="DamageType",
            display_name="Damage Type",
            property_type="choice",
            default_value="ARMOR_PIERCING",
            choices=["ARMOR_PIERCING", "SMALL_ARMS", "EXPLOSION", "FLAME", 
                    "LASER", "CRUSH", "RADIATION", "SNIPER"],
            description="Type of damage dealt",
            category="Weapon",
            affects_balance=True
        ))
        
        self.register("DelayBetweenShots", PropertyMetadata(
            name="DelayBetweenShots",
            display_name="Fire Rate (ms)",
            property_type="number",
            default_value=1000,
            min_value=100,
            max_value=10000,
            description="Milliseconds between shots",
            category="Weapon",
            affects_balance=True
        ))
        
        # Locomotor properties
        self.register("Speed", PropertyMetadata(
            name="Speed",
            display_name="Movement Speed",
            property_type="number",
            default_value=30,
            min_value=0,
            max_value=200,
            description="Movement speed in dist/sec",
            category="Movement",
            affects_balance=True
        ))
        
        self.register("Surfaces", PropertyMetadata(
            name="Surfaces",
            display_name="Movement Surfaces",
            property_type="choice",
            default_value="GROUND",
            choices=["GROUND", "WATER", "AIR", "GROUND WATER", "GROUND RUBBLE"],
            description="Where this unit can move",
            category="Movement"
        ))
        
    def register(self, name: str, metadata: PropertyMetadata):
        """Register a property with its metadata"""
        self.properties[name] = metadata
        
    def get_metadata(self, name: str) -> Optional[PropertyMetadata]:
        """Get metadata for a property"""
        return self.properties.get(name)
        
    def validate_value(self, name: str, value: Any) -> Tuple[bool, str]:
        """Validate a property value"""
        metadata = self.get_metadata(name)
        if not metadata:
            return True, ""  # Unknown properties are allowed
            
        try:
            if metadata.property_type == "number":
                num_val = float(value)
                if metadata.min_value is not None and num_val < metadata.min_value:
                    return False, f"Value must be at least {metadata.min_value}"
                if metadata.max_value is not None and num_val > metadata.max_value:
                    return False, f"Value must be at most {metadata.max_value}"
                    
            elif metadata.property_type == "choice":
                if value not in metadata.choices:
                    return False, f"Must be one of: {', '.join(metadata.choices)}"
                    
            elif metadata.property_type == "boolean":
                if value.lower() not in ["yes", "no", "true", "false", "1", "0"]:
                    return False, "Must be Yes/No or True/False"
                    
            return True, ""
            
        except ValueError:
            return False, f"Invalid value for {metadata.property_type} property"

class RelationshipVisualizer:
    """Handles comprehensive relationship visualization"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.relationship_lines = {}  # Store relationship visualizations
        
    def show_relationships(self, node_id: str):
        """Show all relationships for a node"""
        self.clear_relationships()
        
        node = self.canvas.nodes.get(node_id)
        if not node:
            return
            
        # Find all related nodes
        relationships = self._find_relationships(node)
        
        # Draw relationship lines
        for rel_type, related_nodes in relationships.items():
            for related_id in related_nodes:
                self._draw_relationship(node_id, related_id, rel_type)
                
    def _find_relationships(self, node) -> Dict[str, List[str]]:
        """Find all nodes related to this one"""
        relationships = {
            'used_by': [],      # Units/Buildings using this component
            'uses': [],         # Components used by this entity
            'required_by': [],  # Prerequisites
            'requires': [],     # Requirements
            'conflicts': [],    # Conflicting upgrades
            'part_of': [],      # Parent objects (e.g., general)
        }
        
        # Check all connections
        for conn in self.canvas.connections.values():
            if conn.from_node_id == node.id:
                relationships['uses'].append(conn.to_node_id)
            elif conn.to_node_id == node.id:
                relationships['used_by'].append(conn.from_node_id)
                
            # Special relationship types
            if conn.connection_type == ConnectionType.PREREQUISITE:
                if conn.from_node_id == node.id:
                    relationships['requires'].append(conn.to_node_id)
                else:
                    relationships['required_by'].append(conn.from_node_id)
                    
        return relationships
        
    def _draw_relationship(self, from_id: str, to_id: str, rel_type: str):
        """Draw a relationship visualization"""
        from_node = self.canvas.nodes.get(from_id)
        to_node = self.canvas.nodes.get(to_id)
        
        if not from_node or not to_node:
            return
            
        # Calculate center points
        fx = from_node.position[0] + from_node.size[0] / 2
        fy = from_node.position[1] + from_node.size[1] / 2
        tx = to_node.position[0] + to_node.size[0] / 2
        ty = to_node.position[1] + to_node.size[1] / 2
        
        # Relationship colors
        colors = {
            'used_by': "#4CAF50",
            'uses': "#2196F3", 
            'required_by': "#FF9800",
            'requires': "#F44336",
            'conflicts': "#E91E63"
        }
        
        color = colors.get(rel_type, "#666666")
        
        # Draw dashed line
        line_id = self.canvas.create_line(
            fx, fy, tx, ty,
            fill=color,
            width=2,
            dash=(5, 5),
            tags="relationship"
        )
        
        self.relationship_lines[f"{from_id}_{to_id}_{rel_type}"] = line_id
        
    def clear_relationships(self):
        """Clear all relationship visualizations"""
        self.canvas.delete("relationship")
        self.relationship_lines.clear()

class EnhancedNodeCanvas(tk.Canvas):
    """Enhanced canvas with better visualization and editing"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#1E1E1E", **kwargs)
        
        # Enhanced state
        self.nodes = {}
        self.connections = {}
        self.selected_nodes = set()
        self.generals = {}  # Track which general owns which units
        self.property_registry = PropertyRegistry()
        self.relationship_viz = RelationshipVisualizer(self)
        
        # Visual enhancements
        self.node_templates = self._create_node_templates()
        self.quick_actions = {}  # Store quick action buttons
        
        # UI state
        self.show_relationships = True
        self.show_grid = True
        self.snap_to_grid = True
        self.grid_size = 20
        
        # Interaction state
        self.dragging = False
        self.drag_start = None
        self.drag_item = None
        self.connecting = False
        self.connection_start = None
        self.temp_line = None
        self.hovered_node = None
        
        # Bind events
        self._setup_bindings()
        
        # Draw initial grid
        self.draw_grid()
        
    def draw_grid(self):
        """Draw background grid"""
        self.delete("grid")
        
        # Update canvas size if needed
        self.update()
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            # Canvas not ready yet, schedule for later
            self.after(100, self.draw_grid)
            return
        
        # Draw vertical lines
        for x in range(0, width, self.grid_size):
            self.create_line(x, 0, x, height, fill="#2A2A2A", tags="grid")
            
        # Draw horizontal lines
        for y in range(0, height, self.grid_size):
            self.create_line(0, y, width, y, fill="#2A2A2A", tags="grid")
            
        self.tag_lower("grid")
        
    def _create_node_templates(self) -> Dict[NodeType, Dict]:
        """Create visual templates for each node type"""
        return {
            NodeType.GENERAL: {
                'color': '#9C27B0',
                'icon': '★',
                'size': (250, 100),
                'category': NodeCategory.FACTION
            },
            NodeType.UNIT: {
                'color': '#2196F3',
                'icon': '⚔',
                'size': (200, 150),
                'category': NodeCategory.ENTITY
            },
            NodeType.BUILDING: {
                'color': '#607D8B',
                'icon': '🏢',
                'size': (200, 150),
                'category': NodeCategory.ENTITY
            },
            NodeType.WEAPON: {
                'color': '#F44336',
                'icon': '🔫',
                'size': (180, 120),
                'category': NodeCategory.COMPONENT
            },
            NodeType.LOCOMOTOR: {
                'color': '#4CAF50',
                'icon': '🏃',
                'size': (180, 120),
                'category': NodeCategory.COMPONENT
            },
            NodeType.ARMOR: {
                'color': '#FF9800',
                'icon': '🛡',
                'size': (180, 120),
                'category': NodeCategory.COMPONENT
            },
            NodeType.UPGRADE: {
                'color': '#00BCD4',
                'icon': '⬆',
                'size': (180, 120),
                'category': NodeCategory.LOGIC
            },
            NodeType.SCIENCE: {
                'color': '#673AB7',
                'icon': '🔬',
                'size': (180, 120),
                'category': NodeCategory.LOGIC
            }
        }
        
    def _setup_bindings(self):
        """Setup all event bindings"""
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<Control-MouseWheel>", self.on_zoom)
        self.bind("<Delete>", self.delete_selected)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-d>", self.duplicate_selected)
        
        # Hover effects
        self.bind("<Motion>", self.on_hover)
        
    def on_click(self, event):
        """Handle mouse click"""
        x, y = event.x, event.y
        clicked_item = self.find_closest(x, y)[0]
        tags = self.gettags(clicked_item)
        
        if not tags:
            # Clicked on empty space - clear selection
            self.clear_selection()
            return
            
        # Check if clicked on a quick action button
        if clicked_item in self.quick_actions:
            callback, tooltip = self.quick_actions[clicked_item]
            callback()
            return
            
        # Check if clicked on a port
        for tag in tags:
            if tag.startswith("port_") and not tag.startswith("port_label"):
                port_id = tag[5:]
                self.start_connection(port_id)
                return
                
        # Check if clicked on a node
        for tag in tags:
            if tag.startswith("node_") and len(tag) > 5:
                node_id = tag[5:]
                if node_id in self.nodes:
                    self.select_node(node_id, event.state & 0x0001)  # Check for Ctrl
                    self.drag_start = (x, y)
                    self.drag_item = node_id
                    self.dragging = False
                    return
                    
    def on_drag(self, event):
        """Handle mouse drag"""
        x, y = event.x, event.y
        
        if self.connecting and self.temp_line:
            # Update temporary connection line
            coords = self.coords(self.temp_line)
            if len(coords) >= 4:
                self.coords(self.temp_line, coords[0], coords[1], x, y)
                
        elif self.drag_item and self.drag_start:
            # Move selected nodes
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            
            # Snap to grid if enabled
            if self.snap_to_grid:
                # Calculate snapped position
                node = self.nodes.get(self.drag_item)
                if node and not self.dragging:
                    new_x = round((node.position[0] + dx) / self.grid_size) * self.grid_size
                    new_y = round((node.position[1] + dy) / self.grid_size) * self.grid_size
                    dx = new_x - node.position[0]
                    dy = new_y - node.position[1]
            
            for node_id in self.selected_nodes:
                node = self.nodes.get(node_id)
                if node:
                    # Update node position
                    node.position = (node.position[0] + dx, node.position[1] + dy)
                    
                    # Move all visual elements
                    for item in self.find_withtag(f"node_{node_id}"):
                        self.move(item, dx, dy)
                    for item in self.find_withtag(f"shadow_{node_id}"):
                        self.move(item, dx, dy)
                        
                    # Update port positions
                    self._update_port_positions(node)
                    
            # Redraw connections
            self.redraw_connections()
            
            self.drag_start = (x, y)
            self.dragging = True
            
    def on_release(self, event):
        """Handle mouse release"""
        if self.connecting:
            # Try to complete connection
            x, y = event.x, event.y
            clicked_item = self.find_closest(x, y)[0]
            tags = self.gettags(clicked_item)
            
            for tag in tags:
                if tag.startswith("port_") and not tag.startswith("port_label"):
                    end_port_id = tag[5:]
                    self.complete_connection(end_port_id)
                    break
                    
            # Clean up temporary line
            if self.temp_line:
                self.delete(self.temp_line)
                self.temp_line = None
                
            self.connecting = False
            self.connection_start = None
            
        self.dragging = False
        self.drag_start = None
        self.drag_item = None
        
    def on_right_click(self, event):
        """Show context menu"""
        # Create context menu if not exists
        if not hasattr(self, 'context_menu'):
            self.setup_context_menu()
            
        if self.context_menu:
            self.context_menu.post(event.x_root, event.y_root)
            
        # Store cursor position for adding nodes
        self.cursor_position = (event.x, event.y)
        
    def on_double_click(self, event):
        """Handle double click - open node properties"""
        x, y = event.x, event.y
        clicked_item = self.find_closest(x, y)[0]
        tags = self.gettags(clicked_item)
        
        for tag in tags:
            if tag.startswith("node_") and len(tag) > 5:
                node_id = tag[5:]
                if node_id in self.nodes:
                    self.open_node_properties(node_id)
                    break
                    
    def on_zoom(self, event):
        """Handle mouse wheel for zooming"""
        # Zoom functionality - simplified for now
        scale = 1.1 if event.delta > 0 else 0.9
        self.scale("all", event.x, event.y, scale, scale)
        
    def on_hover(self, event):
        """Handle mouse hover"""
        # Find what we're hovering over
        item = self.find_closest(event.x, event.y)[0]
        tags = self.gettags(item)
        
        # Track currently hovered node
        current_hover = getattr(self, 'hovered_node', None)
        new_hover = None
        
        # Check if hovering over a node
        for tag in tags:
            if tag.startswith("node_") and len(tag) > 5:
                node_id = tag[5:]
                if node_id in self.nodes:
                    new_hover = node_id
                    break
                    
        # Update hover effects if changed
        if current_hover != new_hover:
            if current_hover:
                self.hide_node_hover_effects(current_hover)
            if new_hover:
                self.show_node_hover_effects(new_hover)
            self.hovered_node = new_hover
            
    def delete_selected(self, event=None):
        """Delete selected nodes and their connections"""
        for node_id in list(self.selected_nodes):
            self.delete_node(node_id)
        self.clear_selection()
        
    def select_all(self, event=None):
        """Select all nodes"""
        for node_id, node in self.nodes.items():
            self.selected_nodes.add(node_id)
            node.selected = True
            self.redraw_node(node)
            
    def duplicate_selected(self, event=None):
        """Duplicate selected nodes"""
        new_nodes = {}
        offset = 50
        
        for node_id in self.selected_nodes:
            node = self.nodes.get(node_id)
            if node:
                # Create new node
                new_pos = (node.position[0] + offset, node.position[1] + offset)
                new_node = self.create_enhanced_node(
                    node.node_type, 
                    node.name + "_copy", 
                    new_pos
                )
                new_node.properties = node.properties.copy()
                new_nodes[node_id] = new_node.id
                
        # Clear selection and select new nodes
        self.clear_selection()
        for new_id in new_nodes.values():
            self.select_node(new_id, True)
            
    def clear_selection(self, event=None):
        """Clear all selected nodes"""
        for node_id in list(self.selected_nodes):
            node = self.nodes.get(node_id)
            if node:
                node.selected = False
                self.redraw_node(node)
        self.selected_nodes.clear()
        
        # Fire selection changed event
        self.event_generate("<<SelectionChanged>>")
        
    def select_node(self, node_id: str, add_to_selection: bool = False):
        """Select a node"""
        if not add_to_selection:
            self.clear_selection()
            
        self.selected_nodes.add(node_id)
        node = self.nodes.get(node_id)
        if node:
            node.selected = True
            self.redraw_node(node)
            
        # Fire selection changed event
        self.event_generate("<<SelectionChanged>>")
        
    def redraw_node(self, node: 'EnhancedNode'):
        """Redraw a single node"""
        # Delete old node visuals
        self.delete(f"node_{node.id}")
        self.delete(f"shadow_{node.id}")
        # Redraw
        self.draw_enhanced_node(node)
        
    def delete_node(self, node_id: str):
        """Delete a node and its connections"""
        node = self.nodes.get(node_id)
        if not node:
            return
            
        # Delete visual elements
        self.delete(f"node_{node_id}")
        self.delete(f"shadow_{node_id}")
        
        # Delete connections
        connections_to_delete = []
        for conn_id, conn in self.connections.items():
            if conn.from_node_id == node_id or conn.to_node_id == node_id:
                connections_to_delete.append(conn_id)
                
        for conn_id in connections_to_delete:
            self.delete_connection(conn_id)
            
        # Remove from nodes dict
        del self.nodes[node_id]
        
    def delete_connection(self, conn_id: str):
        """Delete a connection"""
        conn = self.connections.get(conn_id)
        if not conn:
            return
            
        # Remove from port references
        from_node = self.nodes.get(conn.from_node_id)
        to_node = self.nodes.get(conn.to_node_id)
        
        if from_node:
            from_port = self._get_port(from_node, conn.from_port_id)
            if from_port and conn_id in from_port.connected_to:
                from_port.connected_to.remove(conn_id)
                
        if to_node:
            to_port = self._get_port(to_node, conn.to_port_id)
            if to_port and conn_id in to_port.connected_to:
                to_port.connected_to.remove(conn_id)
                
        # Delete visual
        self.delete(f"connection_{conn_id}")
        
        # Remove from connections dict
        del self.connections[conn_id]
        
    def _get_port(self, node: 'EnhancedNode', port_id: str):
        """Get a port from a node"""
        for port in node.input_ports + node.output_ports:
            if port.id == port_id:
                return port
        return None
        
    def _update_port_positions(self, node: 'EnhancedNode'):
        """Update port positions for a node"""
        x, y = node.position
        width, height = node.size
        
        # Input ports on the left
        if node.input_ports:
            spacing = height / (len(node.input_ports) + 1)
            for i, port in enumerate(node.input_ports):
                port.position = (x, y + spacing * (i + 1))
                
        # Output ports on the right
        if node.output_ports:
            spacing = height / (len(node.output_ports) + 1)
            for i, port in enumerate(node.output_ports):
                port.position = (x + width, y + spacing * (i + 1))
                
    def setup_context_menu(self):
        """Setup right-click context menu"""
        self.context_menu = tk.Menu(self, tearoff=0)
        
        # Add node submenu
        add_menu = tk.Menu(self.context_menu, tearoff=0)
        for node_type in NodeType:
            add_menu.add_command(
                label=node_type.value.title(),
                command=lambda nt=node_type: self.add_node_at_cursor(nt)
            )
        
        self.context_menu.add_cascade(label="Add Node", menu=add_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        self.context_menu.add_command(label="Duplicate", command=self.duplicate_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self.select_all)
        self.context_menu.add_command(label="Clear Selection", command=self.clear_selection)
        
    def add_node_at_cursor(self, node_type: NodeType):
        """Add a node at the cursor position"""
        if hasattr(self, 'cursor_position'):
            x, y = self.cursor_position
            # Snap to grid
            if self.snap_to_grid:
                x = round(x / self.grid_size) * self.grid_size
                y = round(y / self.grid_size) * self.grid_size
                
            name = f"New {node_type.value.title()}"
            self.create_enhanced_node(node_type, name, (x, y))
            
    def open_node_properties(self, node_id: str):
        """Open properties dialog for a node"""
        # This is handled by the integration layer
        pass
        
    def start_connection(self, port_id: str):
        """Start drawing a connection from a port"""
        # Find the port and node
        for node in self.nodes.values():
            port = self._get_port(node, port_id)
            if port:
                self.connecting = True
                self.connection_start = (node.id, port_id)
                
                # Create temporary line
                x, y = port.position
                self.temp_line = self.create_line(
                    x, y, x, y,
                    fill="#FFFFFF",
                    width=2,
                    dash=(5, 5),
                    tags="temp_connection"
                )
                break
                
    def complete_connection(self, end_port_id: str):
        """Complete a connection between two ports"""
        if not self.connection_start:
            return
            
        start_node_id, start_port_id = self.connection_start
        
        # Find end node and port
        end_node = None
        end_port = None
        for node in self.nodes.values():
            port = self._get_port(node, end_port_id)
            if port:
                end_node = node
                end_port = port
                break
                
        if not end_node or not end_port:
            return
            
        start_node = self.nodes.get(start_node_id)
        start_port = self._get_port(start_node, start_port_id) if start_node else None
        
        if not start_port:
            return
            
        # Validate connection
        if not self.validate_connection(start_node, start_port, end_node, end_port):
            return
            
        # Create connection
        self._create_connection(start_node, start_port, end_node, end_port)
        
    def validate_connection(self, from_node, from_port, to_node, to_port) -> bool:
        """Validate if a connection is allowed"""
        # Can't connect to same node
        if from_node.id == to_node.id:
            return False
            
        # Must connect output to input
        if from_port.port_type == to_port.port_type:
            return False
            
        # Check if compatible types
        if from_port.data_type != to_port.data_type:
            # Check if compatible
            if to_port.accepts_types and from_port.data_type not in to_port.accepts_types:
                return False
                
        # Check max connections
        if to_port.max_connections != -1 and len(to_port.connected_to) >= to_port.max_connections:
            return False
            
        return True
        
    def _create_connection(self, from_node, from_port, to_node, to_port):
        """Create a connection between two ports"""
        import uuid
        from dataclasses import dataclass
        
        @dataclass
        class Connection:
            id: str
            from_node_id: str
            from_port_id: str
            to_node_id: str
            to_port_id: str
            connection_type: ConnectionType
            
        conn_id = str(uuid.uuid4())
        connection = Connection(
            id=conn_id,
            from_node_id=from_node.id,
            from_port_id=from_port.id,
            to_node_id=to_node.id,
            to_port_id=to_port.id,
            connection_type=from_port.data_type
        )
        
        self.connections[conn_id] = connection
        from_port.connected_to.append(conn_id)
        to_port.connected_to.append(conn_id)
        
        self.draw_connection(connection)
        
    def draw_connection(self, connection):
        """Draw a connection between two ports"""
        from_node = self.nodes.get(connection.from_node_id)
        to_node = self.nodes.get(connection.to_node_id)
        
        if not from_node or not to_node:
            return
            
        from_port = self._get_port(from_node, connection.from_port_id)
        to_port = self._get_port(to_node, connection.to_port_id)
        
        if not from_port or not to_port:
            return
            
        # Draw bezier curve
        self.draw_bezier_connection(
            from_port.position, to_port.position,
            connection.id, connection.connection_type
        )
        
    def draw_bezier_connection(self, start, end, conn_id, conn_type):
        """Draw a bezier curve connection"""
        x1, y1 = start
        x2, y2 = end
        
        # Calculate control points for bezier curve
        distance = abs(x2 - x1) / 2
        cx1 = x1 + distance
        cy1 = y1
        cx2 = x2 - distance
        cy2 = y2
        
        # Create smooth curve using multiple line segments
        points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3 * x1 + 3*(1-t)**2*t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * x2
            y = (1-t)**3 * y1 + 3*(1-t)**2*t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * y2
            points.extend([x, y])
            
        # Connection color based on type
        colors = {
            ConnectionType.WEAPON_SLOT: "#E74C3C",
            ConnectionType.ARMOR_SET: "#F39C12",
            ConnectionType.LOCOMOTOR_SET: "#27AE60",
            ConnectionType.PREREQUISITE: "#9B59B6",
            ConnectionType.UPGRADE_GRANTS: "#1ABC9C",
            ConnectionType.CONFLICTS_WITH: "#C0392B",
            ConnectionType.OWNS: "#3498DB",
        }
        color = colors.get(conn_type, "#AAAAAA")
        
        self.create_line(
            points,
            fill=color,
            width=3,
            smooth=True,
            tags=(f"connection_{conn_id}", "connection")
        )
        
    def redraw_connections(self):
        """Redraw all connections"""
        self.delete("connection")
        for connection in self.connections.values():
            self.draw_connection(connection)
            
    def _setup_enhanced_ports(self, node: 'EnhancedNode'):
        """Setup ports for a node based on its type"""
        # Import at function level to avoid circular imports
        import uuid
        
        if node.node_type == NodeType.UNIT:
            # Input ports
            node.input_ports.extend([
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Prerequisites",
                    port_type="input",
                    data_type=ConnectionType.PREREQUISITE,
                    color="#9B59B6"
                ),
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="From General",
                    port_type="input",
                    data_type=ConnectionType.OWNS,
                    color="#3498DB"
                ),
            ])
            # Output ports
            node.output_ports.extend([
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Weapon",
                    port_type="output",
                    data_type=ConnectionType.WEAPON_SLOT,
                    color="#E74C3C"
                ),
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Armor",
                    port_type="output",
                    data_type=ConnectionType.ARMOR_SET,
                    color="#F39C12"
                ),
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Locomotor",
                    port_type="output",
                    data_type=ConnectionType.LOCOMOTOR_SET,
                    color="#27AE60"
                ),
            ])
            
        elif node.node_type == NodeType.WEAPON:
            # Input ports
            node.input_ports.extend([
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Used By",
                    port_type="input",
                    data_type=ConnectionType.WEAPON_SLOT,
                    color="#E74C3C"
                ),
            ])
            # Output ports
            node.output_ports.extend([
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Projectile",
                    port_type="output",
                    data_type=ConnectionType.PROJECTILE_REF,
                    color="#FF6B6B"
                ),
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Effects",
                    port_type="output",
                    data_type=ConnectionType.FX_REF,
                    color="#4ECDC4"
                ),
            ])
            
        elif node.node_type == NodeType.GENERAL:
            # Output ports only
            node.output_ports.extend([
                EnhancedPort(
                    id=str(uuid.uuid4()),
                    name="Units",
                    port_type="output",
                    data_type=ConnectionType.OWNS,
                    color="#3498DB"
                ),
            ])
            
        # Update port positions
        self._update_port_positions(node)
        
    def create_enhanced_node(self, node_type: NodeType, name: str, position: Tuple[int, int]) -> 'EnhancedNode':
        """Create an enhanced node with better visuals"""
        template = self.node_templates.get(node_type, {})
        
        node = EnhancedNode(
            id=str(uuid.uuid4()),
            node_type=node_type,
            name=name,
            position=position,
            size=template.get('size', (180, 120)),
            color=template.get('color', '#666666'),
            icon=template.get('icon', ''),
            category=template.get('category', NodeCategory.ENTITY)
        )
        
        # Setup ports based on type
        self._setup_enhanced_ports(node)
        
        self.nodes[node.id] = node
        self.draw_enhanced_node(node)
        
        return node
        
    def draw_enhanced_node(self, node: 'EnhancedNode'):
        """Draw an enhanced node with better visuals"""
        x, y = node.position
        width, height = node.size
        
        # Shadow effect
        shadow_offset = 3
        self.create_rectangle(
            x + shadow_offset, y + shadow_offset,
            x + width + shadow_offset, y + height + shadow_offset,
            fill="#000000",
            outline="",
            tags=(f"shadow_{node.id}", "shadow")
        )
        
        # Main node body with gradient effect
        node_id = self.create_rectangle(
            x, y, x + width, y + height,
            fill=node.color,
            outline="#FFFFFF" if node.selected else node.color,
            width=3 if node.selected else 0,
            tags=(f"node_{node.id}", "node", f"category_{node.category.value}")
        )
        
        # Header with icon
        header_height = 35
        self.create_rectangle(
            x, y, x + width, y + header_height,
            fill=self._darken_color(node.color, 0.3),
            outline="",
            tags=(f"node_{node.id}", "node_header")
        )
        
        # Icon
        if node.icon:
            self.create_text(
                x + 20, y + header_height / 2,
                text=node.icon,
                font=("Arial", 16),
                fill="white",
                tags=(f"node_{node.id}", "node_icon")
            )
            
        # Node name
        self.create_text(
            x + 40, y + header_height / 2,
            text=node.name,
            font=("Arial", 11, "bold"),
            fill="white",
            anchor="w",
            tags=(f"node_{node.id}", "node_title")
        )
        
        # Node type badge
        badge_width = 80
        badge_x = x + width - badge_width - 5
        self.create_rectangle(
            badge_x, y + 5,
            badge_x + badge_width, y + 25,
            fill=self._lighten_color(node.color, 0.2),
            outline="",
            tags=(f"node_{node.id}", "node_badge")
        )
        
        self.create_text(
            badge_x + badge_width / 2, y + 15,
            text=node.node_type.value.upper(),
            font=("Arial", 8),
            fill="white",
            tags=(f"node_{node.id}", "node_type")
        )
        
        # Quick stats preview
        if hasattr(node, 'quick_stats'):
            stats_y = y + header_height + 10
            for stat, value in node.quick_stats.items():
                self.create_text(
                    x + 10, stats_y,
                    text=f"{stat}: {value}",
                    font=("Arial", 9),
                    fill="#CCCCCC",
                    anchor="w",
                    tags=(f"node_{node.id}", "node_stats")
                )
                stats_y += 15
                
        # Draw ports with labels
        self._draw_enhanced_ports(node)
        
        # Quick action buttons (appear on hover)
        self._create_quick_actions(node)
        
    def _draw_enhanced_ports(self, node: 'EnhancedNode'):
        """Draw enhanced ports with better visuals"""
        for port in node.input_ports + node.output_ports:
            x, y = port.position
            
            # Port circle with glow effect
            radius = 8
            glow_radius = 12
            
            # Glow
            self.create_oval(
                x - glow_radius, y - glow_radius,
                x + glow_radius, y + glow_radius,
                fill="",
                outline=port.color,
                width=1,
                tags=(f"port_glow_{port.id}", f"node_{node.id}", "port_glow"),
                state="hidden"
            )
            
            # Main port
            port_id = self.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=port.color,
                outline="#FFFFFF",
                width=2,
                tags=(f"port_{port.id}", f"node_{node.id}", "port")
            )
            
            # Port label with background
            if port.port_type == "input":
                label_x = x - radius - 5
                anchor = "e"
            else:
                label_x = x + radius + 5
                anchor = "w"
                
            # Label background
            label_bg = self.create_rectangle(
                0, 0, 0, 0,  # Will be updated after text creation
                fill="#2C2C2C",
                outline="",
                tags=(f"port_label_bg_{port.id}", f"node_{node.id}")
            )
            
            # Label text
            label_id = self.create_text(
                label_x, y,
                text=port.name,
                font=("Arial", 9),
                fill="#FFFFFF",
                anchor=anchor,
                tags=(f"port_label_{port.id}", f"node_{node.id}")
            )
            
            # Update label background position
            bbox = self.bbox(label_id)
            if bbox:
                self.coords(label_bg, bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1)
                
    def _create_quick_actions(self, node: 'EnhancedNode'):
        """Create quick action buttons for a node"""
        x, y = node.position
        width, height = node.size
        
        actions = []
        
        # Actions based on node type
        if node.node_type == NodeType.WEAPON:
            actions.extend([
                ("➕", "Add to General", lambda: self.add_to_general(node)),
                ("🔄", "Switch Unit", lambda: self.switch_owner(node)),
                ("📋", "Duplicate", lambda: self.duplicate_node(node))
            ])
        elif node.node_type == NodeType.UNIT:
            actions.extend([
                ("🔧", "Change Weapon", lambda: self.change_component(node, "weapon")),
                ("👟", "Change Locomotor", lambda: self.change_component(node, "locomotor")),
                ("📊", "Analyze Balance", lambda: self.analyze_node_balance(node))
            ])
        elif node.node_type == NodeType.GENERAL:
            actions.extend([
                ("📈", "Faction Overview", lambda: self.show_faction_overview(node)),
                ("⚖️", "Balance Check", lambda: self.check_faction_balance(node))
            ])
            
        # Create action buttons (hidden by default)
        button_size = 25
        button_x = x + width + 5
        button_y = y
        
        for icon, tooltip, callback in actions:
            btn_id = self.create_rectangle(
                button_x, button_y,
                button_x + button_size, button_y + button_size,
                fill="#333333",
                outline="#666666",
                tags=(f"action_{node.id}", f"node_{node.id}", "quick_action"),
                state="hidden"
            )
            
            self.create_text(
                button_x + button_size / 2,
                button_y + button_size / 2,
                text=icon,
                font=("Arial", 12),
                fill="white",
                tags=(f"action_{node.id}", f"node_{node.id}", "quick_action"),
                state="hidden"
            )
            
            # Store callback
            self.quick_actions[btn_id] = (callback, tooltip)
            
            button_y += button_size + 5
            
    def show_node_hover_effects(self, node_id: str):
        """Show hover effects for a node"""
        # Show port glows
        self.itemconfig(f"port_glow_{node_id}", state="normal")
        
        # Show quick actions
        self.itemconfig(f"action_{node_id}", state="normal")
        
        # Show relationships
        if self.show_relationships:
            self.relationship_viz.show_relationships(node_id)
            
    def hide_node_hover_effects(self, node_id: str):
        """Hide hover effects for a node"""
        self.itemconfig(f"port_glow_{node_id}", state="hidden")
        self.itemconfig(f"action_{node_id}", state="hidden")
        self.relationship_viz.clear_relationships()
        
    def on_hover(self, event):
        """Handle mouse hover"""
        # Find what we're hovering over
        item = self.find_closest(event.x, event.y)[0]
        tags = self.gettags(item)
        
        # Check if hovering over a node
        for tag in tags:
            if tag.startswith("node_") and len(tag) > 5:
                node_id = tag[5:]
                if node_id in self.nodes:
                    self.show_node_hover_effects(node_id)
                    return
                    
        # Not hovering over a node - hide all effects
        for node_id in self.nodes:
            self.hide_node_hover_effects(node_id)
            
    def add_to_general(self, node: 'EnhancedNode'):
        """Add a weapon/unit to a general"""
        # Get list of generals
        generals = [n for n in self.nodes.values() if n.node_type == NodeType.GENERAL]
        
        if not generals:
            messagebox.showinfo("No Generals", "No generals found. Create a general first.")
            return
            
        # Create selection dialog
        dialog = GeneralSelectionDialog(self, generals)
        self.wait_window(dialog.dialog)
        
        if dialog.selected_general:
            # Create connection
            self.create_connection(dialog.selected_general.id, node.id, ConnectionType.OWNS)
            messagebox.showinfo("Success", f"Added {node.name} to {dialog.selected_general.name}")
            
    def switch_owner(self, node: 'EnhancedNode'):
        """Switch which unit owns this component"""
        # Find current owners
        current_owners = []
        for conn in self.connections.values():
            if conn.to_node_id == node.id and conn.connection_type == ConnectionType.WEAPON_SLOT:
                owner = self.nodes.get(conn.from_node_id)
                if owner:
                    current_owners.append(owner)
                    
        # Get list of potential new owners
        units = [n for n in self.nodes.values() 
                if n.node_type == NodeType.UNIT and n not in current_owners]
                
        if not units:
            messagebox.showinfo("No Units", "No other units available.")
            return
            
        # Create selection dialog
        dialog = UnitSelectionDialog(self, units, current_owners)
        self.wait_window(dialog.dialog)
        
        if dialog.action == "add" and dialog.selected_unit:
            self.create_connection(dialog.selected_unit.id, node.id, ConnectionType.WEAPON_SLOT)
        elif dialog.action == "remove" and dialog.selected_unit:
            # Find and remove connection
            for conn_id, conn in list(self.connections.items()):
                if conn.from_node_id == dialog.selected_unit.id and conn.to_node_id == node.id:
                    self.delete_connection(conn_id)
                    
    def change_component(self, node: 'EnhancedNode', component_type: str):
        """Change a component (weapon/locomotor) of a unit"""
        # Get available components
        if component_type == "weapon":
            components = [n for n in self.nodes.values() if n.node_type == NodeType.WEAPON]
            conn_type = ConnectionType.WEAPON_SLOT
        elif component_type == "locomotor":
            components = [n for n in self.nodes.values() if n.node_type == NodeType.LOCOMOTOR]
            conn_type = ConnectionType.LOCOMOTOR_SET
        else:
            return
            
        if not components:
            messagebox.showinfo("No Components", f"No {component_type}s found.")
            return
            
        # Find current component
        current = None
        for conn in self.connections.values():
            if conn.from_node_id == node.id and conn.connection_type == conn_type:
                current = self.nodes.get(conn.to_node_id)
                break
                
        # Create selection dialog
        dialog = ComponentSelectionDialog(self, components, current, component_type)
        self.wait_window(dialog.dialog)
        
        if dialog.selected_component:
            # Remove old connection
            if current:
                for conn_id, conn in list(self.connections.items()):
                    if conn.from_node_id == node.id and conn.to_node_id == current.id:
                        self.delete_connection(conn_id)
                        
            # Create new connection
            self.create_connection(node.id, dialog.selected_component.id, conn_type)
            
    def analyze_node_balance(self, node: 'EnhancedNode'):
        """Analyze balance of a single node"""
        # This would open a detailed balance analysis dialog
        BalanceAnalysisDialog(self, node)
        
    def show_faction_overview(self, general_node: 'EnhancedNode'):
        """Show overview of all units in a faction"""
        FactionOverviewDialog(self, general_node)
        
    def check_faction_balance(self, general_node: 'EnhancedNode'):
        """Check balance across faction"""
        # Collect all units belonging to this general
        faction_units = []
        for conn in self.connections.values():
            if conn.from_node_id == general_node.id:
                unit = self.nodes.get(conn.to_node_id)
                if unit and unit.node_type == NodeType.UNIT:
                    faction_units.append(unit)
                    
        if not faction_units:
            messagebox.showinfo("No Units", "No units found for this general.")
            return
            
        # Create balance report
        BalanceReportDialog(self, general_node, faction_units)
        
    def _darken_color(self, color: str, factor: float) -> str:
        """Darken a color by a factor"""
        r = int(color[1:3], 16)
        g = int(color[3:5], 16) 
        b = int(color[5:7], 16)
        
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def _lighten_color(self, color: str, factor: float) -> str:
        """Lighten a color by a factor"""
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"

@dataclass
class EnhancedNode:
    """Enhanced node with additional metadata"""
    id: str
    node_type: NodeType
    name: str
    position: Tuple[int, int]
    size: Tuple[int, int] = (180, 120)
    color: str = "#666666"
    icon: str = ""
    category: NodeCategory = NodeCategory.ENTITY
    properties: Dict[str, Any] = field(default_factory=dict)
    input_ports: List['EnhancedPort'] = field(default_factory=list)
    output_ports: List['EnhancedPort'] = field(default_factory=list)
    selected: bool = False
    locked: bool = False  # Prevent editing critical properties
    quick_stats: Dict[str, str] = field(default_factory=dict)  # Stats shown on node
    
@dataclass 
class EnhancedPort:
    """Enhanced port with better visuals"""
    id: str
    name: str
    port_type: str  # "input" or "output"
    data_type: ConnectionType
    color: str = "#FFFFFF"
    position: Tuple[int, int] = (0, 0)
    max_connections: int = -1
    connected_to: List[str] = field(default_factory=list)
    accepts_types: List[ConnectionType] = field(default_factory=list)  # Compatible types

# Dialog classes for intuitive operations
class GeneralSelectionDialog:
    def __init__(self, parent, generals):
        self.selected_general = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select General")
        self.dialog.geometry("400x300")
        
        ttk.Label(self.dialog, text="Select a general to add this to:").pack(pady=10)
        
        # List of generals
        self.listbox = tk.Listbox(self.dialog, height=10)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        for general in generals:
            self.listbox.insert(tk.END, general.name)
            
        self.generals = generals
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Select", command=self.select).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT)
        
    def select(self):
        selection = self.listbox.curselection()
        if selection:
            self.selected_general = self.generals[selection[0]]
        self.dialog.destroy()

class UnitSelectionDialog:
    def __init__(self, parent, available_units, current_owners):
        self.selected_unit = None
        self.action = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Unit Assignment")
        self.dialog.geometry("500x400")
        
        # Current owners section
        if current_owners:
            ttk.Label(self.dialog, text="Currently assigned to:", 
                     font=("Arial", 10, "bold")).pack(pady=5)
                     
            current_frame = ttk.Frame(self.dialog)
            current_frame.pack(fill=tk.X, padx=20, pady=5)
            
            self.current_listbox = tk.Listbox(current_frame, height=4)
            self.current_listbox.pack(fill=tk.BOTH, expand=True)
            
            for owner in current_owners:
                self.current_listbox.insert(tk.END, owner.name)
                
            ttk.Button(current_frame, text="Remove from Selected", 
                      command=self.remove_from_unit).pack(pady=5)
                      
        # Available units section
        ttk.Label(self.dialog, text="Add to unit:", 
                 font=("Arial", 10, "bold")).pack(pady=5)
                 
        self.available_listbox = tk.Listbox(self.dialog, height=8)
        self.available_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        for unit in available_units:
            self.available_listbox.insert(tk.END, unit.name)
            
        self.available_units = available_units
        self.current_owners = current_owners
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Add to Selected", 
                  command=self.add_to_unit).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.dialog.destroy).pack(side=tk.LEFT)
                  
    def add_to_unit(self):
        selection = self.available_listbox.curselection()
        if selection:
            self.selected_unit = self.available_units[selection[0]]
            self.action = "add"
        self.dialog.destroy()
        
    def remove_from_unit(self):
        selection = self.current_listbox.curselection()
        if selection:
            self.selected_unit = self.current_owners[selection[0]]
            self.action = "remove"
        self.dialog.destroy()

class ComponentSelectionDialog:
    def __init__(self, parent, components, current, component_type):
        self.selected_component = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Select {component_type.title()}")
        self.dialog.geometry("500x400")
        
        if current:
            ttk.Label(self.dialog, text=f"Current {component_type}: {current.name}",
                     font=("Arial", 10, "bold")).pack(pady=10)
                     
        ttk.Label(self.dialog, text=f"Select new {component_type}:").pack(pady=5)
        
        # Component list with preview
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Listbox
        self.listbox = tk.Listbox(list_frame)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        
        # Preview pane
        preview_frame = ttk.LabelFrame(list_frame, text="Preview", width=200)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        preview_frame.pack_propagate(False)
        
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, width=25, height=15)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Populate list
        for comp in components:
            display_name = comp.name
            if comp == current:
                display_name += " (current)"
            self.listbox.insert(tk.END, display_name)
            
        self.components = components
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Select", command=self.select).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT)
        
    def on_select(self, event):
        """Update preview when selection changes"""
        selection = self.listbox.curselection()
        if selection:
            comp = self.components[selection[0]]
            
            # Generate preview text
            preview = f"Name: {comp.name}\n"
            preview += f"Type: {comp.node_type.value}\n\n"
            
            # Add key properties
            for key, value in list(comp.properties.items())[:10]:
                preview += f"{key}: {value}\n"
                
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', preview)
            
    def select(self):
        selection = self.listbox.curselection()
        if selection:
            self.selected_component = self.components[selection[0]]
        self.dialog.destroy()

class BalanceAnalysisDialog:
    def __init__(self, parent, node):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Balance Analysis: {node.name}")
        self.dialog.geometry("600x500")
        
        # Create analysis text
        analysis = self._analyze_node(node, parent)
        
        # Display analysis
        text = scrolledtext.ScrolledText(self.dialog, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert('1.0', analysis)
        text.config(state='disabled')
        
        # Close button
        ttk.Button(self.dialog, text="Close", 
                  command=self.dialog.destroy).pack(pady=10)
                  
    def _analyze_node(self, node, canvas):
        """Generate balance analysis for a node"""
        analysis = f"=== Balance Analysis: {node.name} ===\n\n"
        
        # Get stats
        cost = int(node.properties.get('BuildCost', 0))
        build_time = float(node.properties.get('BuildTime', 0))
        
        # Find connected components
        weapon = None
        armor = None
        locomotor = None
        
        for conn in canvas.connections.values():
            if conn.from_node_id == node.id:
                connected = canvas.nodes.get(conn.to_node_id)
                if connected:
                    if connected.node_type == NodeType.WEAPON:
                        weapon = connected
                    elif connected.node_type == NodeType.ARMOR:
                        armor = connected
                    elif connected.node_type == NodeType.LOCOMOTOR:
                        locomotor = connected
                        
        # Analyze cost efficiency
        analysis += "COST EFFICIENCY:\n"
        analysis += f"- Build Cost: ${cost}\n"
        analysis += f"- Build Time: {build_time}s\n"
        
        if cost > 0:
            time_per_cost = build_time / cost * 1000
            analysis += f"- Time per $1000: {time_per_cost:.1f}s\n"
            
            if time_per_cost < 10:
                analysis += "  ✓ Good production efficiency\n"
            else:
                analysis += "  ⚠ Slow to produce for cost\n"
                
        # Analyze combat stats
        if weapon:
            analysis += f"\nWEAPON: {weapon.name}\n"
            damage = float(weapon.properties.get('PrimaryDamage', 0))
            range_val = float(weapon.properties.get('AttackRange', 0))
            rof = float(weapon.properties.get('DelayBetweenShots', 1000)) / 1000
            
            dps = damage / rof if rof > 0 else 0
            
            analysis += f"- Damage: {damage}\n"
            analysis += f"- Range: {range_val}\n"
            analysis += f"- DPS: {dps:.1f}\n"
            
            if cost > 0:
                dps_per_cost = dps / cost * 1000
                analysis += f"- DPS per $1000: {dps_per_cost:.2f}\n"
                
                if dps_per_cost > 50:
                    analysis += "  ⚠ Very high damage for cost\n"
                elif dps_per_cost < 10:
                    analysis += "  ⚠ Very low damage for cost\n"
                else:
                    analysis += "  ✓ Balanced damage output\n"
                    
        # Movement analysis
        if locomotor:
            analysis += f"\nLOCOMOTOR: {locomotor.name}\n"
            speed = float(locomotor.properties.get('Speed', 0))
            analysis += f"- Speed: {speed} dist/sec\n"
            
            if speed > 50:
                analysis += "  ✓ Fast unit\n"
            elif speed < 20:
                analysis += "  ⚠ Slow unit\n"
                
        # Role assessment
        analysis += "\nROLE ASSESSMENT:\n"
        if weapon and range_val > 200:
            analysis += "- Long range support unit\n"
        elif weapon and dps > 50:
            analysis += "- High DPS assault unit\n"
        elif locomotor and speed > 40:
            analysis += "- Fast raider/scout\n"
        else:
            analysis += "- General purpose unit\n"
            
        # Balance recommendations
        analysis += "\nRECOMMENDATIONS:\n"
        recommendations = []
        
        if cost > 0 and weapon:
            if dps_per_cost > 50:
                recommendations.append("- Consider reducing damage or increasing cost")
            elif dps_per_cost < 10:
                recommendations.append("- Consider increasing damage or reducing cost")
                
        if not recommendations:
            recommendations.append("- Unit appears reasonably balanced")
            
        analysis += "\n".join(recommendations)
        
        return analysis

class FactionOverviewDialog:
    def __init__(self, parent, general_node):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Faction Overview: {general_node.name}")
        self.dialog.geometry("800x600")
        
        # Create notebook for categories
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Collect faction units
        units = []
        buildings = []
        
        for conn in parent.connections.values():
            if conn.from_node_id == general_node.id:
                node = parent.nodes.get(conn.to_node_id)
                if node:
                    if node.node_type == NodeType.UNIT:
                        units.append(node)
                    elif node.node_type == NodeType.BUILDING:
                        buildings.append(node)
                        
        # Units tab
        units_frame = ttk.Frame(notebook)
        notebook.add(units_frame, text=f"Units ({len(units)})")
        
        # Buildings tab
        buildings_frame = ttk.Frame(notebook)
        notebook.add(buildings_frame, text=f"Buildings ({len(buildings)})")
        
        # Tech tree tab
        tech_frame = ttk.Frame(notebook)
        notebook.add(tech_frame, text="Tech Tree")
        
        # Populate tabs
        self._populate_units_tab(units_frame, units)
        self._populate_buildings_tab(buildings_frame, buildings)
        
        # Close button
        ttk.Button(self.dialog, text="Close", 
                  command=self.dialog.destroy).pack(pady=10)
                  
    def _populate_units_tab(self, frame, units):
        """Populate units tab with sortable list"""
        # Create treeview
        tree = ttk.Treeview(frame, columns=('cost', 'health', 'damage', 'speed'), 
                           show='tree headings')
        tree.heading('#0', text='Unit')
        tree.heading('cost', text='Cost')
        tree.heading('health', text='Health')
        tree.heading('damage', text='Damage')
        tree.heading('speed', text='Speed')
        
        tree.column('#0', width=200)
        tree.column('cost', width=80)
        tree.column('health', width=80)
        tree.column('damage', width=80)
        tree.column('speed', width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with units
        for unit in sorted(units, key=lambda u: u.name):
            cost = unit.properties.get('BuildCost', 0)
            # Extract other stats (simplified)
            tree.insert('', 'end', text=unit.name, 
                       values=(cost, '?', '?', '?'))
                       
    def _populate_buildings_tab(self, frame, buildings):
        """Populate buildings tab"""
        # Similar to units tab
        pass

class BalanceReportDialog:
    def __init__(self, parent, general_node, units):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Balance Report: {general_node.name}")
        self.dialog.geometry("700x500")
        
        # Generate report
        report = self._generate_report(general_node, units)
        
        # Display report
        text = scrolledtext.ScrolledText(self.dialog, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert('1.0', report)
        text.config(state='disabled')
        
        # Export button
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Export Report", 
                  command=lambda: self._export_report(report)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Close", 
                  command=self.dialog.destroy).pack(side=tk.LEFT)
                  
    def _generate_report(self, general, units):
        """Generate comprehensive balance report"""
        report = f"=== Balance Report: {general.name} ===\n\n"
        report += f"Total Units: {len(units)}\n\n"
        
        # Cost distribution
        report += "COST DISTRIBUTION:\n"
        costs = [int(u.properties.get('BuildCost', 0)) for u in units]
        if costs:
            report += f"- Average: ${sum(costs)/len(costs):.0f}\n"
            report += f"- Min: ${min(costs)}\n"
            report += f"- Max: ${max(costs)}\n\n"
            
        # Unit roles
        report += "UNIT ROLES:\n"
        # Categorize units (simplified)
        infantry = [u for u in units if 'infantry' in u.name.lower()]
        vehicles = [u for u in units if 'tank' in u.name.lower() or 'vehicle' in u.name.lower()]
        
        report += f"- Infantry: {len(infantry)}\n"
        report += f"- Vehicles: {len(vehicles)}\n"
        report += f"- Other: {len(units) - len(infantry) - len(vehicles)}\n\n"
        
        # Potential issues
        report += "POTENTIAL ISSUES:\n"
        
        # Check for gaps
        if not infantry:
            report += "- No infantry units\n"
        if not vehicles:
            report += "- No vehicle units\n"
            
        # Check cost distribution
        if costs and max(costs) > min(costs) * 10:
            report += "- Very large cost range (10x difference)\n"
            
        return report
        
    def _export_report(self, report):
        """Export report to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(report)
            messagebox.showinfo("Export Complete", f"Report saved to {filename}")

# Connection type enhancements
