import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional, Tuple
import re
import math
from enhanced_node_editor import (
    EnhancedNodeCanvas, EnhancedNode, NodeType, NodeCategory,
    ConnectionType, PropertyRegistry, PropertyMetadata
)

class SmartINIParser:
    """Enhanced INI parser that understands relationships"""
    
    def __init__(self):
        self.object_cache = {}  # Cache all parsed objects
        self.relationships = {}  # Track relationships between objects
        
    def parse_all_ini_files(self, big_editor) -> Dict[str, Any]:
        """Parse all INI files in the archive to build complete picture"""
        all_objects = {}
        
        # Get all INI files
        for entry in big_editor.archive.entries:
            if entry.path.lower().endswith('.ini'):
                try:
                    content = entry.data.decode('utf-8', errors='ignore')
                    objects = self.parse_ini_content(content, entry.path)
                    all_objects.update(objects)
                except:
                    pass
                    
        # Build relationship map
        self._build_relationships(all_objects)
        
        return all_objects
    
    def _is_object_definition(self, line: str) -> bool:
        """Check if line is an object definition"""
        keywords = ['Object', 'Weapon', 'Armor', 'Science', 'Upgrade', 
                   'Locomotor', 'CommandSet', 'CommandButton', 'FXList',
                   'ParticleSystem', 'ObjectCreationList', 'SpecialPower']
        return any(line.startswith(kw + ' ') for kw in keywords)
        
    def parse_ini_content(self, content: str, source_file: str) -> Dict[str, Any]:
        """Parse INI content with source tracking"""
        objects = {}
        current_object = None
        current_section = None
        section_stack = []
        in_section = False
        section_properties = []
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith(';'):
                continue
                
            # Object definitions
            if self._is_object_definition(line_stripped):
                obj_type, obj_name = self._parse_object_definition(line_stripped)
                if obj_type and obj_name:
                    if "=" in obj_name:
                        obj_name = obj_name.replace("=","")
                    if obj_name.startswith(" "):
                        obj_name = obj_name.split(" ")[1]
                    current_object = {
                        'type': obj_type,
                        'name': obj_name,
                        'source_file': source_file,
                        'properties': {},
                        'sections': {},
                        'line_number': line_num
                    }
                    objects[obj_name] = current_object
                    section_stack = []
                    in_section = False
                    
            # End statement
            elif line_stripped == 'End':
                if in_section and current_section:
                    # Process accumulated section properties
                    if section_properties:
                        current_section['properties']['_raw'] = section_properties
                        self._process_section_properties(current_section, section_properties)
                        section_properties = []
                    
                    if section_stack:
                        section_stack.pop()
                        current_section = section_stack[-1] if section_stack else None
                        in_section = bool(section_stack)
                    else:
                        in_section = False
                        current_section = None
                else:
                    current_object = None
                    
            # Section definitions like WeaponSet, ArmorSet, Prerequisites
            elif current_object and not in_section:
                # Check for section start
                if line_stripped in ['WeaponSet', 'ArmorSet', 'Prerequisites', 'Conditions']:
                    in_section = True
                    current_section = {
                        'type': line_stripped,
                        'properties': {}
                    }
                    current_object['sections'][line_stripped] = current_section
                    section_properties = []
                    section_stack.append(current_section)
                    
                # Module definitions (Draw = W3DTankDraw ModuleTag_01)
                elif '=' in line_stripped and 'ModuleTag_' in line_stripped:
                    parts = line_stripped.split('=')
                    section_type = parts[0].strip().split()[0]
                    module_tag = parts[0].strip().split()[-1]
                    
                    section = {
                        'type': section_type,
                        'tag': module_tag,
                        'properties': {},
                        'subsections': {}
                    }
                    
                    current_object['sections'][module_tag] = section
                    section_stack.append(section)
                    current_section = section
                    in_section = True
                    section_properties = []
                    
                # Regular property assignments
                else:
                    self._parse_property(line_stripped, current_object, None)
                    
            # Inside a section
            elif current_object and in_section and current_section:
                # Accumulate section properties
                section_properties.append(line_stripped)
                
        return objects
    
    def _parse_object_definition(self, line: str) -> Tuple[str, str]:
        """Parse object type and name from definition line"""
        parts = line.split(None, 1)
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None, None
        
    def _parse_property(self, line: str, obj: Dict, section: Optional[Dict]):
        """Parse a property line"""
        target = section if section else obj
        
        if 'properties' not in target:
            target['properties'] = {}
            
        # Regular property handling
        if '=' in line:
            parts = line.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
            
            # Special handling for Locomotor
            if key == 'Locomotor':
                # Store the full value, e.g. "SET_NORMAL HumveeLocomotor"
                target['properties'][key] = value
            else:
                target['properties'][key] = value
        else:
            # Properties without '=' 
            parts = line.split(None, 1)
            if parts:
                key = parts[0]
                value = parts[1] if len(parts) > 1 else ''
                
                # Some properties can have multiple values
                if key in ['ShowSubObject', 'HideSubObject']:
                    if key not in target['properties']:
                        target['properties'][key] = []
                    target['properties'][key].append(value)
                else:
                    target['properties'][key] = value
        
    def _process_section_properties(self, section: Dict, properties: List[str]):
        """Process properties within a section"""
        if section['type'] == 'WeaponSet':
            weapons = []
            conditions = None
            
            for prop in properties:
                if prop.startswith('Conditions'):
                    if '=' in prop:
                        conditions = prop.split('=', 1)[1].strip()
                    else:
                        conditions = 'None'
                elif prop.startswith('Weapon') and '=' in prop:
                    # Parse "Weapon = PRIMARY CrusaderTankGun" or "Weapon = SECONDARY TankMachineGun"
                    parts = prop.split('=', 1)[1].strip().split()
                    if len(parts) >= 2:
                        slot = parts[0]  # PRIMARY, SECONDARY, etc.
                        weapon_name = parts[1]
                        if "FX" in weapon_name:
                            continue
                        weapons.append({
                            'slot': slot,
                            'weapon': weapon_name
                        })
                        
            section['properties']['weapons'] = weapons
            section['properties']['conditions'] = conditions
            
        elif section['type'] == 'ArmorSet':
            armors = []
            conditions = None
            
            for prop in properties:
                if prop.startswith('Conditions'):
                    if '=' in prop:
                        conditions = prop.split('=', 1)[1].strip()
                    else:
                        conditions = 'None'
                elif prop.startswith('Armor') and '=' in prop:
                    armor_name = prop.split('=', 1)[1].strip()
                    armors.append(armor_name)
                elif prop.startswith('DamageFX') and '=' in prop:
                    section['properties']['DamageFX'] = prop.split('=', 1)[1].strip()
                    
            section['properties']['armors'] = armors
            section['properties']['conditions'] = conditions
            
        elif section['type'] == 'Prerequisites':
            prerequisites = []
            
            for prop in properties:
                if prop.startswith('Object') and '=' in prop:
                    obj_name = prop.split('=', 1)[1].strip()
                    prerequisites.append(obj_name)
                    
            section['properties']['prerequisites'] = prerequisites
            
        else:
            # Generic section processing
            for prop in properties:
                if '=' in prop:
                    key, value = prop.split('=', 1)
                    section['properties'][key.strip()] = value.strip()
                else:
                    # Store as-is
                    if '_lines' not in section['properties']:
                        section['properties']['_lines'] = []
                    section['properties']['_lines'].append(prop)
                    
    def _build_relationships(self, all_objects: Dict[str, Any]):
        """Build comprehensive relationship map"""
        self.relationships = {
            'unit_weapons': {},      # unit -> [weapons]
            'weapon_units': {},      # weapon -> [units]
            'unit_armor': {},        # unit -> armor
            'unit_locomotor': {},    # unit -> locomotor
            'unit_general': {},      # unit -> general
            'general_units': {},     # general -> [units]
            'upgrade_units': {},     # upgrade -> [units that can use it]
            'unit_upgrades': {},     # unit -> [available upgrades]
            'prerequisites': {},     # object -> [prerequisites]
            'enables': {},          # object -> [what it enables]
        }
        
        # Scan all objects for relationships
        for obj_name, obj_data in all_objects.items():
            obj_type = obj_data.get('type', '').lower()
           
            
            # Extract weapon relationships from WeaponSet section
            if 'WeaponSet' in obj_data.get('sections', {}):
                weapon_set = obj_data['sections']['WeaponSet']
               
                weapons = weapon_set.get('properties', {}).get('weapons', [])
                weapon_names = []
                for weapon_info in weapons:
                 
                    weapon_name = weapon_info.get('weapon')
                    if weapon_name:
                        weapon_names.append(weapon_name)
                        
                        # Add to weapon->units mapping
                        if weapon_name not in self.relationships['weapon_units']:
                            self.relationships['weapon_units'][weapon_name] = []
                        self.relationships['weapon_units'][weapon_name].append(obj_name)
                        
                if weapon_names:
                    self.relationships['unit_weapons'][obj_name] = weapon_names
                    
            # Extract armor relationships from ArmorSet section
            if 'ArmorSet' in obj_data.get('sections', {}):
                armor_set = obj_data['sections']['ArmorSet']
                armors = armor_set.get('properties', {}).get('armors', [])
                if armors:
                    # Usually just one armor per set
                    self.relationships['unit_armor'][obj_name] = armors[0]
                    
            # Extract locomotor from properties
            if 'Locomotor' in obj_data.get('properties', {}):
                loco_value = obj_data['properties']['Locomotor']
                # Parse "SET_NORMAL CrusaderLocomotor" format
                if isinstance(loco_value, str) and ' ' in loco_value:
                    parts = loco_value.split()
                    if len(parts) >= 2:
                        locomotor_name = parts[-1]  # Get the last part
                        self.relationships['unit_locomotor'][obj_name] = locomotor_name
                        
            # Extract prerequisites from Prerequisites section
            if 'Prerequisites' in obj_data.get('sections', {}):
                prereq_section = obj_data['sections']['Prerequisites']
                prereqs = prereq_section.get('properties', {}).get('prerequisites', [])
                if prereqs:
                    self.relationships['prerequisites'][obj_name] = prereqs
                    for prereq in prereqs:
                        if prereq not in self.relationships['enables']:
                            self.relationships['enables'][prereq] = []
                        self.relationships['enables'][prereq].append(obj_name)
                        
            # Extract general relationships from source file
            source_file = obj_data.get('source_file', '')
            if source_file.startswith("Object"):
                # Determine general from file path
                general = self._extract_general_from_path(source_file)
                if general:
                    self.relationships['unit_general'][obj_name] = general
                    if general not in self.relationships['general_units']:
                        self.relationships['general_units'][general] = []
                    
                    self.relationships['general_units'][general].append(obj_name)
                    
            # Extract upgrade relationships from behavior sections
            for section_name, section_data in obj_data.get('sections', {}).items():
                
                if section_data.get('type') == 'ObjectCreationUpgrade':
                    props = section_data.get('properties', {})
                    if 'TriggeredBy' in props:
                        upgrade_name = props['TriggeredBy']
                        if obj_name not in self.relationships['unit_upgrades']:
                            self.relationships['unit_upgrades'][obj_name] = []
                        self.relationships['unit_upgrades'][obj_name].append(upgrade_name)
                        
                        if upgrade_name not in self.relationships['upgrade_units']:
                            self.relationships['upgrade_units'][upgrade_name] = []
                        self.relationships['upgrade_units'][upgrade_name].append(obj_name)
            
           
        
    def _extract_general_from_path(self, path: str) -> Optional[str]:
        """Extract general name from file path"""
        # Map file names to generals
        general_mapping = {
            'AmericaInfantry.ini': 'America',
            'AmericaVehicle.ini': 'America',
            'AmericaAir.ini': 'America',
            'ChinaInfantry.ini': 'China',
            'ChinaVehicle.ini': 'China',
            'ChinaAir.ini': 'China',
            'GLAInfantry.ini': 'GLA',
            'GLAVehicle.ini': 'GLA',
            'AirforceGeneral.ini': 'AirforceGeneral',
            'LaserGeneral.ini': 'LaserGeneral',
            'SuperweaponGeneral.ini': 'SuperweaponGeneral',
            'InfantryGeneral.ini': 'InfantryGeneral',
            'TankGeneral.ini': 'TankGeneral',
            'DemoGeneral.ini': 'DemoGeneral',
            'ChemicalGeneral.ini': 'ChemicalGeneral',
            'StealthGeneral.ini': 'StealthGeneral',
            'BossGeneral.ini': 'BossGeneral',
        }
        
        filename = path.split('\\')[-1]
        return general_mapping.get(filename)

class EnhancedNodeEditorIntegration:
    """Enhanced integration with automatic loading and smart editing"""
    
    def __init__(self, big_editor):
        self.big_editor = big_editor
        self.node_canvas = None
        self.parser = SmartINIParser()
        self.all_objects = {}  # All parsed objects from all INI files
        self.current_view = {}  # Currently visible objects
        self.auto_load_enabled = True
        self.property_editor = None
        
    def integrate(self):
        """Integrate with the BIG editor"""
        # Parse all INI files on startup
        if self.big_editor.archive:
            self.all_objects = self.parser.parse_all_ini_files(self.big_editor)
            
        # Modify the text editor to auto-load node view
        self._setup_auto_load()
        
    def _setup_auto_load(self):
        """Setup automatic node editor loading when viewing INI files"""
        # Check if big_editor has the method we need to override
        if not hasattr(self.big_editor, 'load_file_content'):
            return
            
        original_load_content = self.big_editor.load_file_content
        
        def new_load_content(entry):
            # Call original
            original_load_content(entry)
            
            # Auto-load in node editor if INI file
            if self.auto_load_enabled and entry.path.lower().endswith('.ini'):
                # Check if node editor tab exists
                for i in range(self.big_editor.notebook.index('end')):
                    if self.big_editor.notebook.tab(i, 'text') == 'Node Editor':
                        # Switch to node editor and load
                        self.big_editor.notebook.select(i)
                        self.load_ini_to_nodes(entry)
                        break
                else:
                    # Create node editor tab
                    self.create_node_editor_tab()
                    self.load_ini_to_nodes(entry)
                    
        self.big_editor.load_file_content = new_load_content
        
    def create_node_editor_tab(self):
        """Create enhanced node editor tab"""
        node_frame = ttk.Frame(self.big_editor.notebook)
        self.big_editor.notebook.add(node_frame, text="Node Editor")
        
        # Enhanced toolbar
        toolbar = self._create_enhanced_toolbar(node_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Create paned window for canvas and property panel
        paned = ttk.PanedWindow(node_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Node canvas
        canvas_frame = ttk.Frame(paned)
        paned.add(canvas_frame, weight=3)
        
        self.node_canvas = EnhancedNodeCanvas(canvas_frame)
        self.node_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Property panel
        prop_frame = ttk.Frame(paned)
        paned.add(prop_frame, weight=1)
        
        self.property_editor = PropertyEditor(prop_frame, self)
        self.property_editor.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection changes
        self.node_canvas.bind("<<SelectionChanged>>", self._on_selection_changed)
        
        return node_frame
        
    def _create_enhanced_toolbar(self, parent):
        """Create enhanced toolbar with smart operations"""
        toolbar = ttk.Frame(parent)
        
        # View controls
        view_frame = ttk.LabelFrame(toolbar, text="View")
        view_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(view_frame, text="Show All Relations", 
                  command=self.show_all_relationships).pack(side=tk.LEFT, padx=2)
        ttk.Button(view_frame, text="Focus Current", 
                  command=self.focus_current_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(view_frame, text="Show General Overview", 
                  command=self.show_general_overview).pack(side=tk.LEFT, padx=2)
                  
        # Smart operations
        ops_frame = ttk.LabelFrame(toolbar, text="Operations")
        ops_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(ops_frame, text="Add to General", 
                  command=self.smart_add_to_general).pack(side=tk.LEFT, padx=2)
        ttk.Button(ops_frame, text="Clone to Other Faction", 
                  command=self.clone_to_faction).pack(side=tk.LEFT, padx=2)
        ttk.Button(ops_frame, text="Balance Selected", 
                  command=self.balance_selected).pack(side=tk.LEFT, padx=2)
                  
        # Layout controls
        layout_frame = ttk.LabelFrame(toolbar, text="Layout")
        layout_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(layout_frame, text="Auto Layout", 
                  command=self.auto_layout).pack(side=tk.LEFT, padx=2)
        ttk.Button(layout_frame, text="Group by Type", 
                  command=self.group_by_type).pack(side=tk.LEFT, padx=2)
        ttk.Button(layout_frame, text="Group by General", 
                  command=self.group_by_general).pack(side=tk.LEFT, padx=2)
                  
        # Search
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_changed)
        ttk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT)
        
        return toolbar
        
    def load_ini_to_nodes(self, entry):
        """Load INI content to node editor with smart relationship detection"""
        try:
            content = entry.data.decode('utf-8', errors='ignore')
            
            # Parse current file
            current_objects = self.parser.parse_ini_content(content, entry.path)
            
            # Update all_objects with current file objects
            self.all_objects.update(current_objects)
            
            # Rebuild relationships with updated objects
            self.parser._build_relationships(self.all_objects)
            
            # Clear canvas
            self.node_canvas.delete("all")
            self.node_canvas.nodes.clear()
            self.node_canvas.connections.clear()
            
            # Create general nodes first if showing overview
            generals_created = set()
            
            # Create nodes for current file objects
            x_offset = 100
            y_offset = 100
            x_spacing = 250
            y_spacing = 200
            col = 0
            row = 0
            
            # First pass: Create all nodes
            for obj_name, obj_data in current_objects.items():
                # Determine node type
                node_type = self._get_node_type(obj_data)
                
                # Check if we should create a general node
                general = self.parser.relationships['unit_general'].get(obj_name)
                if general and general not in generals_created:
                    # Create general node
                    gen_node = self.node_canvas.create_enhanced_node(
                        NodeType.GENERAL, general, (50, 50 + len(generals_created) * 150)
                    )
                    generals_created.add(general)
                    
                # Create object node
                x = x_offset + (col * x_spacing)
                y = y_offset + (row * y_spacing)
                
                node = self.node_canvas.create_enhanced_node(node_type, obj_name, (x, y))
                
                # Set properties and quick stats
                node.properties = obj_data.get('properties', {})
                self._update_node_quick_stats(node, obj_data)
                
                # Update position
                col += 1
                if col >= 4:
                    col = 0
                    row += 1
                    
            # Second pass: Create related nodes from other files if needed
            self._create_related_nodes(current_objects)
                    
            # Third pass: Create all connections
            self._create_smart_connections(current_objects)
            
            # Auto-layout if many nodes
            if len(self.node_canvas.nodes) > 10:
                self.auto_layout()
                
            self.big_editor.update_status(f"Loaded {len(current_objects)} objects with relationships")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load INI: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _create_related_nodes(self, current_objects):
        """Create nodes for related objects from other files"""
        node_map = {node.name: node for node in self.node_canvas.nodes.values()}
        
        # Check what related objects we need to create
        needed_objects = set()
        
        for obj_name in current_objects:
            # Get weapons used by this object
            weapons = self.parser.relationships['unit_weapons'].get(obj_name, [])
            for weapon_name in weapons:
                if weapon_name not in node_map and weapon_name in self.all_objects:
                    needed_objects.add(weapon_name)
                    
            # Get armor used
            armor = self.parser.relationships['unit_armor'].get(obj_name)
            if armor and armor not in node_map and armor in self.all_objects:
                needed_objects.add(armor)
                
            # Get locomotor used
            locomotor = self.parser.relationships['unit_locomotor'].get(obj_name)
            if locomotor and locomotor not in node_map and locomotor in self.all_objects:
                needed_objects.add(locomotor)
                
        # Create nodes for needed objects
        for obj_name in needed_objects:
            obj_data = self.all_objects[obj_name]
            node_type = self._get_node_type(obj_data)
            
            # Find a good position near related units
            related_positions = []
            
            # Find units using this object
            if obj_name in self.parser.relationships['weapon_units']:
                for unit_name in self.parser.relationships['weapon_units'][obj_name]:
                    if unit_name in node_map:
                        related_positions.append(node_map[unit_name].position)
                        
            # Calculate average position
            if related_positions:
                avg_x = sum(pos[0] for pos in related_positions) / len(related_positions)
                avg_y = sum(pos[1] for pos in related_positions) / len(related_positions)
                # Offset to the right
                position = (avg_x + 250, avg_y)
            else:
                # Default position
                position = (500, 100 + len(needed_objects) * 150)
                
            # Create the node
            node = self.node_canvas.create_enhanced_node(node_type, obj_name, position)
            node.properties = obj_data.get('properties', {})
            self._update_node_quick_stats(node, obj_data)
            
    def _create_smart_connections(self, current_objects):
        """Create connections including cross-file relationships"""
        # Get node mapping
        node_map = {node.name: node for node in self.node_canvas.nodes.values()}
        
        # Create connections for all visible nodes
        for node in self.node_canvas.nodes.values():
            obj_name = node.name
            
            # Weapon connections
            if obj_name in self.parser.relationships['unit_weapons']:
                weapons = self.parser.relationships['unit_weapons'][obj_name]
                for weapon_name in weapons:
                    if weapon_name in node_map:
                        weapon_node = node_map[weapon_name]
                        self._create_typed_connection(node, weapon_node, ConnectionType.WEAPON_SLOT)
                        
            # Armor connections
            if obj_name in self.parser.relationships['unit_armor']:
                armor_name = self.parser.relationships['unit_armor'][obj_name]
                if armor_name in node_map:
                    armor_node = node_map[armor_name]
                    self._create_typed_connection(node, armor_node, ConnectionType.ARMOR_SET)
                    
            # Locomotor connections
            if obj_name in self.parser.relationships['unit_locomotor']:
                loco_name = self.parser.relationships['unit_locomotor'][obj_name]
                if loco_name in node_map:
                    loco_node = node_map[loco_name]
                    self._create_typed_connection(node, loco_node, ConnectionType.LOCOMOTOR_SET)
                    
            # General connections
            if obj_name in self.parser.relationships['unit_general']:
                general_name = self.parser.relationships['unit_general'][obj_name]
                if general_name in node_map:
                    gen_node = node_map[general_name]
                    self._create_typed_connection(gen_node, node, ConnectionType.OWNS)
                    
            # Prerequisite connections
            if obj_name in self.parser.relationships['prerequisites']:
                prereqs = self.parser.relationships['prerequisites'][obj_name]
                for prereq_name in prereqs:
                    if prereq_name in node_map:
                        prereq_node = node_map[prereq_name]
                        self._create_typed_connection(prereq_node, node, ConnectionType.PREREQUISITE)
                        
    def _update_node_quick_stats(self, node: EnhancedNode, obj_data: Dict = None):
        """Update quick stats shown on node"""
        if not obj_data and node.name in self.all_objects:
            obj_data = self.all_objects[node.name]
            
        if node.node_type == NodeType.UNIT:
            node.quick_stats = {
                'Cost': f"${node.properties.get('BuildCost', '?')}",
                'Build': f"{node.properties.get('BuildTime', '?')}s",
            }
            
            # Add health if available
            for section in obj_data.get('sections', {}).values():
                if section.get('type') == 'Body':
                    health = section.get('properties', {}).get('MaxHealth')
                    if health:
                        node.quick_stats['Health'] = health
                        
        elif node.node_type == NodeType.WEAPON:
            damage = node.properties.get('PrimaryDamage', '?')
            range_val = node.properties.get('AttackRange', '?')
            damage_type = node.properties.get('DamageType', '?')
            
            node.quick_stats = {
                'Damage': damage,
                'Range': range_val,
                'Type': damage_type,
            }
            
            # Add fire rate if available
            delay = node.properties.get('DelayBetweenShots')
            if delay:
                try:
                    rof = 60000 / float(delay)  # Convert to rounds per minute
                    node.quick_stats['RPM'] = f"{rof:.0f}"
                except:
                    pass
                    
        elif node.node_type == NodeType.LOCOMOTOR:
            node.quick_stats = {
                'Speed': node.properties.get('Speed', '?'),
                'Surfaces': node.properties.get('Surfaces', '?'),
            }
            
        elif node.node_type == NodeType.ARMOR:
            # Show key armor values
            armor_values = []
            for key, value in node.properties.items():
                if key.startswith('Armor') and '=' in str(value):
                    armor_values.append(f"{key}: {value}")
                    
            if armor_values:
                # Show first few armor values
                for i, armor in enumerate(armor_values[:3]):
                    node.quick_stats[f'Armor{i+1}'] = armor
                    
        elif node.node_type == NodeType.GENERAL:
            # Count units and buildings
            units = self.parser.relationships['general_units'].get(node.name, [])
            node.quick_stats = {
                'Units': str(len(units)),
                'Faction': node.name,
            }
            
    def _create_typed_connection(self, from_node: EnhancedNode, to_node: EnhancedNode, 
                               conn_type: ConnectionType):
        """Create a properly typed connection between nodes"""
        # Find appropriate ports
        from_port = None
        to_port = None
        
        # Find output port on from_node that matches the connection type
        for port in from_node.output_ports:
            if port.data_type == conn_type:
                from_port = port
                break
                
        # Find input port on to_node that matches the connection type
        for port in to_node.input_ports:
            if port.data_type == conn_type:
                to_port = port
                break
                
        # Create ports if they don't exist
        if not from_port:
            # Create output port
            from enhanced_node_editor import EnhancedPort
            import uuid
            
            port_name = {
                ConnectionType.WEAPON_SLOT: "Weapon",
                ConnectionType.ARMOR_SET: "Armor", 
                ConnectionType.LOCOMOTOR_SET: "Locomotor",
                ConnectionType.OWNS: "Owns",
                ConnectionType.PREREQUISITE: "Enables",
            }.get(conn_type, str(conn_type.value))
            
            from_port = EnhancedPort(
                id=str(uuid.uuid4()),
                name=port_name,
                port_type="output",
                data_type=conn_type,
                color=self._get_connection_color(conn_type)
            )
            from_node.output_ports.append(from_port)
            self.node_canvas._update_port_positions(from_node)
            
        if not to_port:
            # Create input port
            from enhanced_node_editor import EnhancedPort
            import uuid
            
            port_name = {
                ConnectionType.WEAPON_SLOT: "Used By",
                ConnectionType.ARMOR_SET: "Used By",
                ConnectionType.LOCOMOTOR_SET: "Used By", 
                ConnectionType.OWNS: "Owned By",
                ConnectionType.PREREQUISITE: "Requires",
            }.get(conn_type, str(conn_type.value))
            
            to_port = EnhancedPort(
                id=str(uuid.uuid4()),
                name=port_name,
                port_type="input",
                data_type=conn_type,
                color=self._get_connection_color(conn_type)
            )
            to_node.input_ports.append(to_port)
            self.node_canvas._update_port_positions(to_node)
            
        if from_port and to_port:
            # Check if connection already exists
            for conn in self.node_canvas.connections.values():
                if (conn.from_node_id == from_node.id and 
                    conn.to_node_id == to_node.id and
                    conn.connection_type == conn_type):
                    return  # Connection already exists
                    
            # Create the actual connection
            self.node_canvas._create_connection(from_node, from_port, to_node, to_port)
            
            # Redraw nodes to show new ports
            self.node_canvas.redraw_node(from_node)
            self.node_canvas.redraw_node(to_node)
            
    def _get_connection_color(self, conn_type: ConnectionType) -> str:
        """Get color for connection type"""
        colors = {
            ConnectionType.WEAPON_SLOT: "#E74C3C",
            ConnectionType.ARMOR_SET: "#F39C12",
            ConnectionType.LOCOMOTOR_SET: "#27AE60",
            ConnectionType.PREREQUISITE: "#9B59B6",
            ConnectionType.UPGRADE_GRANTS: "#1ABC9C",
            ConnectionType.CONFLICTS_WITH: "#C0392B",
            ConnectionType.OWNS: "#3498DB",
        }
        return colors.get(conn_type, "#AAAAAA")
        
    def _get_node_type(self, obj_data: Dict) -> NodeType:
        """Determine node type from object data"""
        obj_type = obj_data.get('type', '').lower()
        
        type_mapping = {
            'weapon': NodeType.WEAPON,
            'armor': NodeType.ARMOR,
            'science': NodeType.SCIENCE,
            'upgrade': NodeType.UPGRADE,
            'locomotor': NodeType.LOCOMOTOR,
            'commandset': NodeType.COMMANDSET,
            'commandbutton': NodeType.COMMANDBUTTON,
            'fxlist': NodeType.FXLIST,
            'particlesystem': NodeType.PARTICLESYSTEM,
            'objectcreationlist': NodeType.OCL,
            'specialpower': NodeType.SPECIALPOWER,
        }
        
        if obj_type in type_mapping:
            return type_mapping[obj_type]
            
        # For Object type, check KindOf
        if obj_type == 'object':
            kindof = str(obj_data.get('properties', {}).get('KindOf', '')).upper()
            if 'STRUCTURE' in kindof:
                return NodeType.BUILDING
            elif 'PROJECTILE' in kindof:
                return NodeType.PROJECTILE
                
        return NodeType.UNIT
        
    def show_all_relationships(self):
        """Show all relationships for selected nodes"""
        if not self.node_canvas:
            messagebox.showinfo("Not Ready", "Node editor not initialized yet")
            return
            
        if not self.node_canvas.selected_nodes:
            messagebox.showinfo("No Selection", "Select nodes to show relationships")
            return
            
        # Show relationships for all selected nodes
        for node_id in self.node_canvas.selected_nodes:
            self.node_canvas.relationship_viz.show_relationships(node_id)
            
    def focus_current_file(self):
        """Focus view on objects from current file only"""
        if not self.big_editor.current_entry:
            return
            
        # Hide nodes not from current file
        current_file = self.big_editor.current_entry.path
        
        for node in self.node_canvas.nodes.values():
            if node.name in self.all_objects:
                obj_data = self.all_objects[node.name]
                if obj_data.get('source_file') != current_file:
                    # Hide node (implementation would set visibility)
                    pass
                    
    def show_general_overview(self):
        """Show overview grouped by generals"""
        # Clear and recreate with general grouping
        self.node_canvas.delete("all")
        self.node_canvas.nodes.clear()
        self.node_canvas.connections.clear()
        
        # Create general nodes
        generals = ['America', 'China', 'GLA', 'AirforceGeneral', 'LaserGeneral', 
                   'SuperweaponGeneral', 'InfantryGeneral', 'TankGeneral']
        
        general_nodes = {}
        for i, general in enumerate(generals):
            if general in self.parser.relationships['general_units']:
                node = self.node_canvas.create_enhanced_node(
                    NodeType.GENERAL, general, (100 + (i % 3) * 400, 50 + (i // 3) * 300)
                )
                general_nodes[general] = node
                
        # Add units to each general
        for general, units in self.parser.relationships['general_units'].items():
            if general in general_nodes:
                gen_node = general_nodes[general]
                
                # Create unit nodes around general
                for j, unit_name in enumerate(units[:5]):  # Limit to 5 for display
                    if unit_name in self.all_objects:
                        unit_data = self.all_objects[unit_name]
                        angle = (j / 5) * 2 * 3.14159
                        x = gen_node.position[0] + 150 * math.cos(angle)
                        y = gen_node.position[1] + 150 * math.sin(angle) + 50
                        
                        unit_node = self.node_canvas.create_enhanced_node(
                            self._get_node_type(unit_data), unit_name, (x, y)
                        )
                        
                        # Create connection
                        self._create_typed_connection(gen_node, unit_node, ConnectionType.OWNS)
                        
    def smart_add_to_general(self):
        """Smart operation to add selected unit to a general"""
        if not self.node_canvas.selected_nodes:
            messagebox.showinfo("No Selection", "Select a unit to add to a general")
            return
            
        # Get selected units
        selected_units = []
        for node_id in self.node_canvas.selected_nodes:
            node = self.node_canvas.nodes.get(node_id)
            if node and node.node_type == NodeType.UNIT:
                selected_units.append(node)
                
        if not selected_units:
            messagebox.showinfo("No Units", "Select unit nodes to add to a general")
            return
            
        # Show general selection dialog
        dialog = SmartGeneralAssignDialog(self.node_canvas, selected_units, 
                                         self.parser.relationships)
        self.node_canvas.wait_window(dialog.dialog)
        
        if dialog.result:
            # Apply changes
            self._apply_general_assignment(dialog.result)
            
    def clone_to_faction(self):
        """Clone selected units to another faction with balance adjustments"""
        if not self.node_canvas.selected_nodes:
            messagebox.showinfo("No Selection", "Select units to clone")
            return
            
        # Get selected units
        selected_units = []
        for node_id in self.node_canvas.selected_nodes:
            node = self.node_canvas.nodes.get(node_id)
            if node and node.node_type in [NodeType.UNIT, NodeType.BUILDING]:
                selected_units.append(node)
                
        if not selected_units:
            messagebox.showinfo("No Units", "Select units or buildings to clone")
            return
            
        # Show clone dialog
        dialog = CloneToFactionDialog(self.node_canvas, selected_units)
        self.node_canvas.wait_window(dialog.dialog)
        
        if dialog.result:
            self._apply_faction_clone(dialog.result)
            
    def balance_selected(self):
        """Balance selected units based on role and faction"""
        # Implementation would analyze and suggest balance changes
        pass
        
    def auto_layout(self):
        """Enhanced auto-layout with grouping"""
        # Group nodes by type
        groups = {}
        for node in self.node_canvas.nodes.values():
            if node.category not in groups:
                groups[node.category] = []
            groups[node.category].append(node)
            
        # Layout each group
        x_offset = 50
        for category, nodes in groups.items():
            self._layout_group(nodes, x_offset, 50)
            x_offset += 400
            
    def _layout_group(self, nodes: List[EnhancedNode], start_x: int, start_y: int):
        """Layout a group of nodes"""
        cols = 3
        spacing_x = 250
        spacing_y = 180
        
        for i, node in enumerate(nodes):
            col = i % cols
            row = i // cols
            
            node.position = (start_x + col * spacing_x, start_y + row * spacing_y)
            
        # Redraw all nodes
        self.node_canvas.delete("all")
        self.node_canvas.draw_grid()
        
        for node in self.node_canvas.nodes.values():
            self.node_canvas.draw_enhanced_node(node)
            
        # Redraw connections
        for conn in self.node_canvas.connections.values():
            self.node_canvas.draw_connection(conn)
            
    def group_by_type(self):
        """Group nodes by their type"""
        self.auto_layout()  # Uses category grouping
        
    def group_by_general(self):
        """Group nodes by their general/faction"""
        # Group nodes by general
        groups = {'Unknown': []}
        
        for node in self.node_canvas.nodes.values():
            general = self.parser.relationships['unit_general'].get(node.name, 'Unknown')
            if general not in groups:
                groups[general] = []
            groups[general].append(node)
            
        # Layout each group
        x_offset = 50
        for general, nodes in groups.items():
            if nodes:
                self._layout_group(nodes, x_offset, 50)
                x_offset += 400
                
    def _on_search_changed(self, *args):
        """Handle search text change"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            # Show all nodes
            for node in self.node_canvas.nodes.values():
                # Set visibility (implementation would handle this)
                pass
        else:
            # Filter nodes
            for node in self.node_canvas.nodes.values():
                visible = (search_term in node.name.lower() or 
                          search_term in node.node_type.value.lower())
                # Set visibility based on match
                
    def _on_selection_changed(self, event):
        """Handle node selection change"""
        if self.property_editor:
            selected = []
            for node_id in self.node_canvas.selected_nodes:
                node = self.node_canvas.nodes.get(node_id)
                if node:
                    selected.append(node)
                    
            self.property_editor.set_nodes(selected)

class PropertyEditor(ttk.Frame):
    """Enhanced property editor with validation and smart operations"""
    
    def __init__(self, parent, integration):
        super().__init__(parent)
        self.integration = integration
        self.current_nodes = []
        self.property_widgets = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the property editor UI"""
        # Title
        self.title_label = ttk.Label(self, text="Properties", 
                                    font=("Arial", 12, "bold"))
        self.title_label.pack(pady=5)
        
        # Scrollable frame
        canvas = tk.Canvas(self, bg="#2C2C2C")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Quick actions frame
        self.actions_frame = ttk.Frame(self)
        self.actions_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
    def set_nodes(self, nodes: List[EnhancedNode]):
        """Set nodes to edit"""
        self.current_nodes = nodes
        self.refresh_properties()
        
    def refresh_properties(self):
        """Refresh property display"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.property_widgets.clear()
        
        if not self.current_nodes:
            ttk.Label(self.scrollable_frame, text="No nodes selected").pack()
            return
            
        if len(self.current_nodes) == 1:
            self._show_single_node_properties()
        else:
            self._show_multi_node_properties()
            
        # Update actions
        self._update_actions()
        
    def _show_single_node_properties(self):
        """Show properties for a single node"""
        node = self.current_nodes[0]
        
        # Node info
        info_frame = ttk.LabelFrame(self.scrollable_frame, text="Node Info")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(info_frame, text=f"Name: {node.name}").pack(anchor=tk.W, padx=5)
        ttk.Label(info_frame, text=f"Type: {node.node_type.value}").pack(anchor=tk.W, padx=5)
        
        # Properties by category
        categories = {}
        registry = self.integration.node_canvas.property_registry
        
        # Group properties by category
        for prop_name, prop_value in node.properties.items():
            metadata = registry.get_metadata(prop_name)
            category = metadata.category if metadata else "Other"
            
            if category not in categories:
                categories[category] = []
            categories[category].append((prop_name, prop_value, metadata))
            
        # Create category frames
        for category, props in categories.items():
            cat_frame = ttk.LabelFrame(self.scrollable_frame, text=category)
            cat_frame.pack(fill=tk.X, padx=5, pady=5)
            
            for prop_name, prop_value, metadata in props:
                self._create_property_widget(cat_frame, node, prop_name, 
                                           prop_value, metadata)
                                           
    def _create_property_widget(self, parent, node, prop_name, prop_value, metadata):
        """Create appropriate widget for a property"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Label
        label_text = metadata.display_name if metadata else prop_name
        if metadata and metadata.affects_balance:
            label_text += " ⚖"
            
        ttk.Label(frame, text=label_text, width=20).pack(side=tk.LEFT)
        
        # Value widget
        if metadata and metadata.read_only:
            # Read-only
            ttk.Label(frame, text=str(prop_value)).pack(side=tk.LEFT)
            
        elif metadata and metadata.property_type == "choice":
            # Dropdown
            var = tk.StringVar(value=str(prop_value))
            combo = ttk.Combobox(frame, textvariable=var, values=metadata.choices,
                               state="readonly", width=20)
            combo.pack(side=tk.LEFT)
            combo.bind('<<ComboboxSelected>>', 
                      lambda e: self._on_property_changed(node, prop_name, var.get()))
            self.property_widgets[prop_name] = var
            
        elif metadata and metadata.property_type == "boolean":
            # Checkbox
            var = tk.BooleanVar(value=prop_value.lower() in ['yes', 'true', '1'])
            check = ttk.Checkbutton(frame, variable=var,
                                   command=lambda: self._on_property_changed(
                                       node, prop_name, 'Yes' if var.get() else 'No'))
            check.pack(side=tk.LEFT)
            self.property_widgets[prop_name] = var
            
        elif metadata and metadata.property_type == "number":
            # Spinbox with validation
            var = tk.StringVar(value=str(prop_value))
            
            def validate(value):
                if not value:
                    return True
                try:
                    num = float(value)
                    if metadata.min_value is not None and num < metadata.min_value:
                        return False
                    if metadata.max_value is not None and num > metadata.max_value:
                        return False
                    return True
                except:
                    return False
                    
            vcmd = (self.register(validate), '%P')
            spin = ttk.Spinbox(frame, textvariable=var, width=20,
                              from_=metadata.min_value or 0,
                              to=metadata.max_value or 999999,
                              validate='key', validatecommand=vcmd)
            spin.pack(side=tk.LEFT)
            spin.bind('<Return>', lambda e: self._on_property_changed(
                node, prop_name, var.get()))
            spin.bind('<FocusOut>', lambda e: self._on_property_changed(
                node, prop_name, var.get()))
            self.property_widgets[prop_name] = var
            
        else:
            # Text entry
            var = tk.StringVar(value=str(prop_value))
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT)
            entry.bind('<Return>', lambda e: self._on_property_changed(
                node, prop_name, var.get()))
            entry.bind('<FocusOut>', lambda e: self._on_property_changed(
                node, prop_name, var.get()))
            self.property_widgets[prop_name] = var
            
        # Description tooltip
        if metadata and metadata.description:
            # Would add tooltip on hover
            pass
            
    def _show_multi_node_properties(self):
        """Show properties for multiple nodes"""
        # Show common properties
        common_props = self._get_common_properties()
        
        if common_props:
            common_frame = ttk.LabelFrame(self.scrollable_frame, 
                                        text=f"Common Properties ({len(self.current_nodes)} nodes)")
            common_frame.pack(fill=tk.X, padx=5, pady=5)
            
            for prop_name, prop_values in common_props.items():
                self._create_multi_property_widget(common_frame, prop_name, prop_values)
        else:
            ttk.Label(self.scrollable_frame, 
                     text=f"{len(self.current_nodes)} nodes selected (no common properties)").pack()
                     
    def _get_common_properties(self) -> Dict[str, List]:
        """Get properties common to all selected nodes"""
        if not self.current_nodes:
            return {}
            
        # Start with first node's properties
        common = set(self.current_nodes[0].properties.keys())
        
        # Find intersection
        for node in self.current_nodes[1:]:
            common &= set(node.properties.keys())
            
        # Get values for common properties
        result = {}
        for prop in common:
            values = [node.properties.get(prop) for node in self.current_nodes]
            result[prop] = values
            
        return result
        
    def _create_multi_property_widget(self, parent, prop_name, values):
        """Create widget for editing multiple nodes"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(frame, text=prop_name, width=20).pack(side=tk.LEFT)
        
        # Check if all values are the same
        unique_values = set(str(v) for v in values)
        
        if len(unique_values) == 1:
            # All same - show single value
            var = tk.StringVar(value=values[0])
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT)
            entry.bind('<Return>', lambda e: self._on_multi_property_changed(
                prop_name, var.get()))
        else:
            # Different values - show "<multiple values>"
            var = tk.StringVar(value="<multiple values>")
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT)
            entry.bind('<Return>', lambda e: self._on_multi_property_changed(
                prop_name, var.get()))
            
            # Tooltip showing all values
            ttk.Label(frame, text=f"({len(unique_values)} different)",
                     foreground="gray").pack(side=tk.LEFT, padx=5)
                     
    def _on_property_changed(self, node, prop_name, new_value):
        """Handle single property change"""
        # Validate
        registry = self.integration.node_canvas.property_registry
        metadata = registry.get_metadata(prop_name)
        
        if metadata:
            valid, error = registry.validate_value(prop_name, new_value)
            if not valid:
                messagebox.showerror("Invalid Value", error)
                return
                
        # Update property
        old_value = node.properties.get(prop_name)
        node.properties[prop_name] = new_value
        
        # Update visual
        self.integration._update_node_quick_stats(node)
        self.integration.node_canvas.redraw_node(node)
        
        # Mark as modified
        self.integration.big_editor.current_entry.modified = True
        
        # Log change
        print(f"Changed {node.name}.{prop_name}: {old_value} -> {new_value}")
        
    def _on_multi_property_changed(self, prop_name, new_value):
        """Handle property change for multiple nodes"""
        if new_value == "<multiple values>":
            return
            
        # Update all selected nodes
        for node in self.current_nodes:
            self._on_property_changed(node, prop_name, new_value)
            
    def _update_actions(self):
        """Update quick action buttons"""
        # Clear existing
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
            
        if not self.current_nodes:
            return
            
        # Add relevant actions
        if len(self.current_nodes) == 1:
            node = self.current_nodes[0]
            
            if node.node_type == NodeType.WEAPON:
                ttk.Button(self.actions_frame, text="Find Units Using This",
                          command=lambda: self._find_units_using_weapon(node)).pack(side=tk.LEFT, padx=2)
                ttk.Button(self.actions_frame, text="Duplicate Weapon",
                          command=lambda: self._duplicate_weapon(node)).pack(side=tk.LEFT, padx=2)
                          
            elif node.node_type == NodeType.UNIT:
                ttk.Button(self.actions_frame, text="Change Faction",
                          command=lambda: self._change_unit_faction(node)).pack(side=tk.LEFT, padx=2)
                ttk.Button(self.actions_frame, text="Balance Analysis",
                          command=lambda: self._analyze_unit_balance(node)).pack(side=tk.LEFT, padx=2)
                          
    def _find_units_using_weapon(self, weapon_node):
        """Find and highlight units using this weapon"""

        units = self.integration.parser.relationships['general_units'].get(weapon_node.name, [])

        
        # Select units
        self.integration.node_canvas.selected_nodes.clear()
        for unit_name in units:
            for node in self.integration.node_canvas.nodes.values():
                if node.name == unit_name:
                    self.integration.node_canvas.selected_nodes.add(node.id)
                    
        # Redraw to show selection
        for node in self.integration.node_canvas.nodes.values():
            self.integration.node_canvas.redraw_node(node)
            
        messagebox.showinfo("Units Found", 
                           f"Found {len(units)} units using {weapon_node.name}")

class SmartGeneralAssignDialog:
    """Smart dialog for assigning units to generals"""
    
    def __init__(self, parent, units, relationships):
        self.units = units
        self.relationships = relationships
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Assign to General")
        self.dialog.geometry("600x400")
        
        # Current assignments
        ttk.Label(self.dialog, text="Current Assignments:",
                 font=("Arial", 10, "bold")).pack(pady=5)
                 
        current_frame = ttk.Frame(self.dialog)
        current_frame.pack(fill=tk.X, padx=20, pady=5)
        
        for unit in units:
            current_general = relationships['unit_general'].get(unit.name, 'None')
            ttk.Label(current_frame, 
                     text=f"{unit.name}: {current_general}").pack(anchor=tk.W)
                     
        # General selection
        ttk.Label(self.dialog, text="Assign to General:",
                 font=("Arial", 10, "bold")).pack(pady=10)
                 
        self.general_var = tk.StringVar()
        
        generals = ['America', 'China', 'GLA', 'AirforceGeneral', 'LaserGeneral',
                   'SuperweaponGeneral', 'InfantryGeneral', 'TankGeneral', 
                   'DemoGeneral', 'ChemicalGeneral', 'StealthGeneral']
                   
        for general in generals:
            ttk.Radiobutton(self.dialog, text=general, 
                           variable=self.general_var,
                           value=general).pack(anchor=tk.W, padx=40)
                           
        # Options
        options_frame = ttk.LabelFrame(self.dialog, text="Options")
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.copy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Copy instead of move",
                       variable=self.copy_var).pack(anchor=tk.W)
                       
        self.adjust_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Auto-adjust for faction balance",
                       variable=self.adjust_var).pack(anchor=tk.W)
                       
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Apply", 
                  command=self.apply).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="Cancel",
                  command=self.dialog.destroy).pack(side=tk.LEFT)
                  
    def apply(self):
        """Apply the assignment"""
        if not self.general_var.get():
            messagebox.showwarning("No Selection", "Please select a general")
            return
            
        self.result = {
            'units': self.units,
            'general': self.general_var.get(),
            'copy': self.copy_var.get(),
            'adjust': self.adjust_var.get()
        }
        
        self.dialog.destroy()

class CloneToFactionDialog:
    """Dialog for cloning units to other factions"""
    
    def __init__(self, parent, units):
        self.units = units
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Clone to Faction")
        self.dialog.geometry("500x400")
        
        # Source info
        ttk.Label(self.dialog, text=f"Cloning {len(units)} unit(s)",
                 font=("Arial", 10, "bold")).pack(pady=10)
                 
        # Target faction
        ttk.Label(self.dialog, text="Target Faction:").pack(pady=5)
        
        self.target_var = tk.StringVar()
        factions = ['America', 'China', 'GLA']
        
        for faction in factions:
            ttk.Radiobutton(self.dialog, text=faction,
                           variable=self.target_var,
                           value=faction).pack(anchor=tk.W, padx=40)
                           
        # Balance adjustments
        adjust_frame = ttk.LabelFrame(self.dialog, text="Balance Adjustments")
        adjust_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Cost modifier
        ttk.Label(adjust_frame, text="Cost Modifier:").grid(row=0, column=0, sticky=tk.W)
        self.cost_var = tk.StringVar(value="100")
        cost_spin = ttk.Spinbox(adjust_frame, textvariable=self.cost_var,
                               from_=50, to=200, width=10)
        cost_spin.grid(row=0, column=1, padx=5)
        ttk.Label(adjust_frame, text="%").grid(row=0, column=2)
        
        # Health modifier
        ttk.Label(adjust_frame, text="Health Modifier:").grid(row=1, column=0, sticky=tk.W)
        self.health_var = tk.StringVar(value="100")
        health_spin = ttk.Spinbox(adjust_frame, textvariable=self.health_var,
                                 from_=50, to=200, width=10)
        health_spin.grid(row=1, column=1, padx=5)
        ttk.Label(adjust_frame, text="%").grid(row=1, column=2)
        
        # Damage modifier
        ttk.Label(adjust_frame, text="Damage Modifier:").grid(row=2, column=0, sticky=tk.W)
        self.damage_var = tk.StringVar(value="100")
        damage_spin = ttk.Spinbox(adjust_frame, textvariable=self.damage_var,
                                 from_=50, to=200, width=10)
        damage_spin.grid(row=2, column=1, padx=5)
        ttk.Label(adjust_frame, text="%").grid(row=2, column=2)
        
        # Name prefix
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(name_frame, text="Name Prefix:").pack(side=tk.LEFT)
        self.prefix_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.prefix_var, width=20).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Clone", 
                  command=self.clone).pack(side=tk.LEFT, padx=20)
        ttk.Button(button_frame, text="Cancel",
                  command=self.dialog.destroy).pack(side=tk.LEFT)
                  
    def clone(self):
        """Perform the clone operation"""
        if not self.target_var.get():
            messagebox.showwarning("No Target", "Please select a target faction")
            return
            
        self.result = {
            'units': self.units,
            'target': self.target_var.get(),
            'cost_modifier': float(self.cost_var.get()) / 100,
            'health_modifier': float(self.health_var.get()) / 100,
            'damage_modifier': float(self.damage_var.get()) / 100,
            'prefix': self.prefix_var.get()
        }
        
        self.dialog.destroy()