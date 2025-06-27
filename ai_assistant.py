import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
from typing import Dict, List, Any, Optional
from node_editor_integration import NodeEditorIntegration
from dataclasses import dataclass
import os

# Try to import AI libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    LOCAL_AI_AVAILABLE = True
except ImportError:
    LOCAL_AI_AVAILABLE = False

@dataclass
class AIConfig:
    """Configuration for AI services"""
    use_openai: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    use_local: bool = True
    local_model: str = "microsoft/phi-2"
    temperature: float = 0.7
    max_tokens: int = 1000

class AIAssistant:
    """AI Assistant for C&C Generals modding"""
    
    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self.local_pipeline = None
        
        # Initialize AI services
        if self.config.use_openai and OPENAI_AVAILABLE and self.config.openai_api_key:
            openai.api_key = self.config.openai_api_key
            
        if self.config.use_local and LOCAL_AI_AVAILABLE:
            try:
                # Use a smaller model for faster responses
                self.local_pipeline = pipeline(
                    "text-generation",
                    model=self.config.local_model,
                    device="cuda" if torch.cuda.is_available() else "cpu"
                )
            except Exception as e:
                print(f"Failed to load local model: {e}")
                self.local_pipeline = None
                
    def generate_response(self, prompt: str, context: Dict = None) -> str:
        """Generate a response using available AI service"""
        # Add context to prompt
        full_prompt = self._build_prompt(prompt, context)
        
        try:
            if self.config.use_openai and OPENAI_AVAILABLE:
                return self._generate_openai(full_prompt)
            elif self.config.use_local and self.local_pipeline:
                return self._generate_local(full_prompt)
            else:
                return self._generate_fallback(prompt, context)
        except Exception as e:
            return f"Error generating response: {str(e)}"
            
    def _build_prompt(self, prompt: str, context: Dict = None) -> str:
        """Build a complete prompt with context"""
        system_prompt = """You are an AI assistant specializing in Command & Conquer Generals modding.
You have deep knowledge of:
- Unit balance and game mechanics
- INI file structure and syntax
- Weapon systems and damage calculations
- The relationship between different game objects

Provide helpful, specific advice for modding the game."""

        if context:
            context_str = "\n\nCurrent Context:\n"
            if 'current_unit' in context:
                context_str += f"Current Unit: {context['current_unit']}\n"
            if 'unit_stats' in context:
                context_str += f"Unit Stats: {json.dumps(context['unit_stats'], indent=2)}\n"
            if 'selected_nodes' in context:
                context_str += f"Selected Objects: {', '.join(context['selected_nodes'])}\n"
        else:
            context_str = ""
            
        return f"{system_prompt}{context_str}\n\nUser: {prompt}\n\nAssistant:"
        
    def _generate_openai(self, prompt: str) -> str:
        """Generate response using OpenAI API"""
        try:
            if hasattr(openai, 'ChatCompletion'):  # Older API version
                response = openai.ChatCompletion.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": prompt.split('\n\nUser:')[0]},
                        {"role": "user", "content": prompt.split('\n\nUser:')[1].split('\n\nAssistant:')[0]}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                return response.choices[0].message.content
            else:  # Newer API version
                client = openai.OpenAI(api_key=self.config.openai_api_key)
                response = client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": prompt.split('\n\nUser:')[0]},
                        {"role": "user", "content": prompt.split('\n\nUser:')[1].split('\n\nAssistant:')[0]}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI Error: {str(e)}"
            
    def _generate_local(self, prompt: str) -> str:
        """Generate response using local model"""
        try:
            response = self.local_pipeline(
                prompt,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                do_sample=True,
                top_p=0.95,
                pad_token_id=self.local_pipeline.tokenizer.eos_token_id
            )
            
            # Extract generated text
            generated = response[0]['generated_text']
            # Remove the prompt from the response
            if prompt in generated:
                generated = generated.replace(prompt, '').strip()
            
            return generated
        except Exception as e:
            return f"Local Model Error: {str(e)}"
            
    def _generate_fallback(self, prompt: str, context: Dict = None) -> str:
        """Fallback responses when no AI is available"""
        # Pattern matching for common requests
        prompt_lower = prompt.lower()
        
        if "balance" in prompt_lower:
            return self._balance_suggestions(context)
        elif "create" in prompt_lower and ("unit" in prompt_lower or "weapon" in prompt_lower):
            return self._creation_suggestions(prompt_lower)
        elif "counter" in prompt_lower:
            return self._counter_suggestions(context)
        elif "improve" in prompt_lower or "optimize" in prompt_lower:
            return self._improvement_suggestions(context)
        else:
            return """I can help you with:

1. **Unit Balance**: Analyze and suggest balance changes
2. **Create Units/Weapons**: Generate new game objects
3. **Counter Strategies**: Suggest counters to specific units
4. **Optimization**: Improve existing units

Please be specific about what you'd like help with!"""

    def _balance_suggestions(self, context: Dict = None) -> str:
        """Generate balance suggestions"""
        if context and 'unit_stats' in context:
            stats = context['unit_stats']
            suggestions = []
            
            # Analyze cost efficiency
            if stats.get('cost', 0) > 0:
                health_per_cost = stats.get('health', 0) / stats['cost']
                damage_per_cost = stats.get('damage', 0) / stats['cost']
                
                if health_per_cost > 1.0:
                    suggestions.append("- Consider reducing health or increasing cost")
                elif health_per_cost < 0.3:
                    suggestions.append("- Unit may be too fragile for its cost")
                    
                if damage_per_cost > 0.1:
                    suggestions.append("- Damage output may be too high for cost")
                elif damage_per_cost < 0.02:
                    suggestions.append("- Consider increasing damage or reducing cost")
                    
            # Analyze combat stats
            if stats.get('range', 0) > 200:
                suggestions.append("- Long range units should have lower health/damage")
            
            if stats.get('speed', 0) > 50:
                suggestions.append("- Fast units should be more fragile")
                
            return "Balance Suggestions:\n\n" + "\n".join(suggestions) if suggestions else "Unit appears reasonably balanced."
        else:
            return """Balance Analysis Guidelines:

1. **Cost Efficiency**: Health + Damage should be proportional to cost
2. **Role Definition**: Each unit should have clear strengths and weaknesses
3. **Counter System**: Ensure every unit has effective counters
4. **Faction Balance**: Similar roles should have similar total power across factions"""

    def _creation_suggestions(self, prompt: str) -> str:
        """Generate creation suggestions"""
        if "anti-tank" in prompt or "tank destroyer" in prompt:
            return """Anti-Tank Unit Template:

**Properties:**
- Cost: 800-1200 (depending on effectiveness)
- Health: 200-300 (fragile)
- Weapon: High damage (100-150), slow fire rate
- Damage Type: ARMOR_PIERCING
- Speed: Medium (25-35)
- Special: Bonus damage vs vehicles

**Balance Considerations:**
- Weak vs infantry
- Limited vision range
- High cost but specialized role"""
        
        elif "artillery" in prompt:
            return """Artillery Unit Template:

**Properties:**
- Cost: 1200-1500
- Health: 150-250 (very fragile)
- Weapon: Area damage, very long range (300+)
- Minimum range: 100-150
- Speed: Slow (15-20)
- Setup time before firing

**Balance Considerations:**
- Requires protection
- Ineffective at close range
- High damage but slow fire rate"""
        
        else:
            return """Unit Creation Guidelines:

1. **Define Role First**: What tactical niche will this fill?
2. **Set Base Stats**: Use existing similar units as reference
3. **Add Unique Features**: Special abilities or characteristics
4. **Consider Counters**: What will beat this unit?
5. **Test Cost Efficiency**: Is it worth building?"""

    def _counter_suggestions(self, context: Dict = None) -> str:
        """Generate counter unit suggestions"""
        if context and 'current_unit' in context:
            unit_name = context['current_unit'].lower()
            
            if 'tank' in unit_name or 'crusader' in unit_name:
                return """Tank Counters:

1. **RPG Infantry**: Cheap, high damage vs armor
2. **Attack Helicopters**: Mobile, ignore terrain
3. **Artillery**: Outrange and area damage
4. **Tank Hunters**: Specialized anti-armor infantry

Key: Use combined arms and exploit tank weaknesses (slow turret, poor vs infantry)"""
            
            elif 'infantry' in unit_name:
                return """Infantry Counters:

1. **Toxin/Flame Weapons**: Area denial
2. **Snipers**: Long range elimination
3. **Vehicles**: Crush and suppress
4. **Artillery**: Area bombardment

Key: Infantry are cheap but vulnerable to area damage"""
            
        return """General Counter Strategies:

- **Rock-Paper-Scissors**: Infantry > Rockets > Vehicles > Infantry
- **Use Terrain**: Height advantage, choke points
- **Combined Arms**: Mix unit types for versatility
- **Upgrades**: Right upgrades can change matchups"""

    def _improvement_suggestions(self, context: Dict = None) -> str:
        """Generate improvement suggestions"""
        return """Unit Improvement Strategies:

1. **Veterancy**: Design experience bonuses that enhance role
2. **Upgrades**: Add optional upgrades for versatility
3. **Synergies**: Create combos with other units
4. **Unique Abilities**: Add micro-management potential

Example Improvements:
- Add drone/secondary weapon
- Increase armor with upgrade
- Add special abilities (smoke, sprint, etc.)
- Improve sensors or stealth"""

    def analyze_weapon(self, weapon_data: Dict) -> Dict[str, Any]:
        """Analyze weapon statistics and provide insights"""
        analysis = {
            'dps': 0,
            'effectiveness': {},
            'suggestions': []
        }
        
        # Calculate DPS
        damage = float(weapon_data.get('PrimaryDamage', 0))
        fire_rate = float(weapon_data.get('DelayBetweenShots', 1000)) / 1000.0
        clip_size = int(weapon_data.get('ClipSize', 0))
        reload_time = float(weapon_data.get('ClipReloadTime', 0)) / 1000.0
        
        if clip_size > 0:
            # Calculate with reload
            total_time = (clip_size - 1) * fire_rate + reload_time
            dps = (damage * clip_size) / total_time
        else:
            # Continuous fire
            dps = damage / fire_rate if fire_rate > 0 else 0
            
        analysis['dps'] = round(dps, 2)
        
        # Analyze effectiveness vs different targets
        damage_type = weapon_data.get('DamageType', 'NORMAL')
        
        effectiveness_map = {
            'ARMOR_PIERCING': {'vehicles': 'High', 'infantry': 'Low', 'buildings': 'Medium'},
            'SMALL_ARMS': {'vehicles': 'Low', 'infantry': 'High', 'buildings': 'Low'},
            'EXPLOSION': {'vehicles': 'Medium', 'infantry': 'High', 'buildings': 'High'},
            'FLAME': {'vehicles': 'Low', 'infantry': 'Very High', 'buildings': 'Medium'},
        }
        
        analysis['effectiveness'] = effectiveness_map.get(damage_type, {
            'vehicles': 'Medium', 'infantry': 'Medium', 'buildings': 'Medium'
        })
        
        # Generate suggestions
        if dps < 10:
            analysis['suggestions'].append("Very low DPS - consider increasing damage or fire rate")
        elif dps > 100:
            analysis['suggestions'].append("Very high DPS - may be overpowered")
            
        if float(weapon_data.get('AttackRange', 0)) > 200:
            analysis['suggestions'].append("Long range weapon - ensure it has drawbacks")
            
        return analysis

class AIAssistantDialog:
    """Dialog window for AI Assistant interaction"""
    
    def __init__(self, parent, node_editor_integration):
        self.parent = parent
        self.integration = node_editor_integration
        self.ai = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("C&C Generals AI Assistant")
        self.dialog.geometry("800x600")
        
        self.setup_ui()
        self.load_config()
        self.initialize_ai()
        
    def setup_ui(self):
        """Setup the UI components"""
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="AI Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI Provider selection
        provider_frame = ttk.Frame(settings_frame)
        provider_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(provider_frame, text="AI Provider:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.provider_var = tk.StringVar(value="fallback")
        
        ttk.Radiobutton(provider_frame, text="Built-in", 
                       variable=self.provider_var, 
                       value="fallback").pack(side=tk.LEFT, padx=5)
                       
        if LOCAL_AI_AVAILABLE:
            ttk.Radiobutton(provider_frame, text="Local AI", 
                           variable=self.provider_var, 
                           value="local").pack(side=tk.LEFT, padx=5)
                           
        if OPENAI_AVAILABLE:
            ttk.Radiobutton(provider_frame, text="OpenAI", 
                           variable=self.provider_var, 
                           value="openai").pack(side=tk.LEFT, padx=5)
            
            # API key entry
            api_frame = ttk.Frame(settings_frame)
            api_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(api_frame, text="OpenAI API Key:").pack(side=tk.LEFT, padx=(0, 10))
            self.api_key_var = tk.StringVar()
            api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*", width=40)
            api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
        ttk.Button(settings_frame, text="Apply Settings", 
                  command=self.apply_settings).pack(pady=5)
                  
        # Chat interface
        chat_frame = ttk.LabelFrame(main_frame, text="Chat")
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chat history
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, height=20, font=('Arial', 10)
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure tags for formatting
        self.chat_display.tag_configure("user", foreground="#0066CC", font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure("ai", foreground="#009900", font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure("error", foreground="#CC0000")
        
        # Input frame
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.input_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_var)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        input_entry.bind('<Return>', lambda e: self.send_message())
        
        ttk.Button(input_frame, text="Send", command=self.send_message).pack(side=tk.LEFT)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(main_frame, text="Quick Actions")
        actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        actions_container = ttk.Frame(actions_frame)
        actions_container.pack(fill=tk.X, padx=10, pady=10)
        
        # Quick action buttons
        ttk.Button(actions_container, text="Analyze Selected", 
                  command=self.analyze_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_container, text="Generate Unit", 
                  command=self.generate_unit).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_container, text="Balance Report", 
                  command=self.balance_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_container, text="Suggest Counter", 
                  command=self.suggest_counter).pack(side=tk.LEFT, padx=5)
        
        # Welcome message
        self.add_message("AI", """Welcome to the C&C Generals AI Assistant!

I can help you with:
- Analyzing unit balance
- Generating new units and weapons
- Suggesting counters and strategies
- Optimizing your mod

What would you like to work on?""")
        
    def load_config(self):
        """Load AI configuration"""
        # Try to load from environment or config file
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if api_key and hasattr(self, 'api_key_var'):
            self.api_key_var.set(api_key)
            
    def initialize_ai(self):
        """Initialize the AI assistant"""
        config = AIConfig()
        
        if self.provider_var.get() == "openai" and hasattr(self, 'api_key_var'):
            config.use_openai = True
            config.openai_api_key = self.api_key_var.get()
            config.use_local = False
        elif self.provider_var.get() == "local":
            config.use_local = True
            config.use_openai = False
        else:
            config.use_local = False
            config.use_openai = False
            
        self.ai = AIAssistant(config)
        
    def apply_settings(self):
        """Apply AI settings"""
        self.initialize_ai()
        self.add_message("System", "AI settings updated.")
        
    def add_message(self, sender: str, message: str):
        """Add a message to the chat display"""
        self.chat_display.config(state='normal')
        
        # Add sender
        self.chat_display.insert(tk.END, f"{sender}: ", sender.lower())
        
        # Add message
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
        
    def send_message(self):
        """Send a message to the AI"""
        message = self.input_var.get().strip()
        if not message:
            return
            
        # Clear input
        self.input_var.set("")
        
        # Add user message
        self.add_message("User", message)
        
        # Get context
        context = self.get_current_context()
        
        # Generate response in thread to avoid blocking UI
        def generate():
            try:
                response = self.ai.generate_response(message, context)
                self.dialog.after(0, lambda: self.add_message("AI", response))
            except Exception as e:
                self.dialog.after(0, lambda: self.add_message("Error", str(e)))
                
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()
        
    def get_current_context(self) -> Dict:
        """Get current context from the node editor"""
        context = {}
        
        if self.integration.node_canvas:
            # Get selected nodes
            selected = []
            for node_id in self.integration.node_canvas.selected_nodes:
                node = self.integration.node_canvas.nodes.get(node_id)
                if node:
                    selected.append(node.name)
                    
            if selected:
                context['selected_nodes'] = selected
                
                # If single unit selected, get its stats
                if len(selected) == 1:
                    node = next(n for n in self.integration.node_canvas.nodes.values() 
                               if n.name == selected[0])
                    if node.node_type.value == "unit":
                        context['current_unit'] = node.name
                        context['unit_stats'] = {
                            'cost': int(node.properties.get('BuildCost', 0)),
                            'health': self.integration._extract_health(node),
                            'damage': self.integration._extract_damage(node),
                            'range': self.integration._extract_range(node),
                            'speed': self.integration._extract_speed(node),
                        }
                        
        return context
        
    def analyze_selected(self):
        """Analyze selected nodes"""
        context = self.get_current_context()
        
        if not context.get('selected_nodes'):
            self.add_message("System", "Please select one or more nodes to analyze.")
            return
            
        message = f"Analyze the following objects and provide insights: {', '.join(context['selected_nodes'])}"
        self.input_var.set(message)
        self.send_message()
        
    def generate_unit(self):
        """Start unit generation dialog"""
        self.input_var.set("Help me create a new unit. What role should it fill?")
        self.send_message()
        
    def balance_report(self):
        """Generate balance report"""
        self.input_var.set("Generate a balance report for the current mod.")
        self.send_message()
        
    def suggest_counter(self):
        """Suggest counters for selected unit"""
        context = self.get_current_context()
        
        if context.get('current_unit'):
            self.input_var.set(f"What are effective counters to {context['current_unit']}?")
        else:
            self.input_var.set("What unit would you like counter suggestions for?")
            
        self.send_message()

def add_ai_assistant_to_integration(integration_class):
    """Add AI Assistant functionality to the NodeEditorIntegration class"""
    
    original_init = integration_class.__init__
    
    def new_init(self, big_editor):
        original_init(self, big_editor)
        self.ai_dialog = None
        
    integration_class.__init__ = new_init
    
    def show_ai_assistant(self):
        """Show AI Assistant dialog"""
        if not self.ai_dialog:
            self.ai_dialog = AIAssistantDialog(self.big_editor.root, self)
        else:
            self.ai_dialog.dialog.lift()
            
    integration_class.show_ai_assistant = show_ai_assistant
    
    return integration_class

# Apply the enhancement
NodeEditorIntegration = add_ai_assistant_to_integration(NodeEditorIntegration)