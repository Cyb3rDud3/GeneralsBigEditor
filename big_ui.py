import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import struct
import os
from pathlib import Path
import io
from datetime import datetime

# Import node editor components if available
try:
    from enhanced_node_editor import EnhancedNodeCanvas, EnhancedNode, NodeType, ConnectionType
    from enhanced_integration import EnhancedNodeEditorIntegration
    from ai_assistant import AIAssistant, AIAssistantDialog
    NODE_EDITOR_AVAILABLE = True
except ImportError:
    NODE_EDITOR_AVAILABLE = False
    print("Node Editor components not found. Basic functionality only.")

class FileEntry:
    def __init__(self, offset, size, path, data=None):
        self.offset = offset
        self.size = size
        self.path = path
        self.data = data
        self.modified = False
        
    def __str__(self):
        return f'path: {self.path}, offset: {self.offset}, size: {self.size}'

class BIGArchive:
    def __init__(self):
        self.header = None
        self.file_size = 0
        self.entries = []
        self.file_data = {}
        self.original_data = None
        
    def read_uint32_be(self, data):
        return struct.unpack('>I', data)[0]
    
    def read_uint32_le(self, data):
        return struct.unpack('<I', data)[0]
    
    def write_uint32_be(self, value):
        return struct.pack('>I', value)
    
    def write_uint32_le(self, value):
        return struct.pack('<I', value)
    
    def read_string(self, file):
        name = b""
        char = file.read(1)
        while char != b'\0' and char:
            name += char
            char = file.read(1)
        return name.decode('ascii', errors='ignore')
    
    def write_string(self, string):
        return string.encode('ascii') + b'\0'
    
    def load(self, filepath):
        with open(filepath, 'rb') as f:
            self.original_data = f.read()
            
        file = io.BytesIO(self.original_data)
        
        # Read header
        self.header = file.read(4)
        if not self.header.startswith(b'BIG'):
            raise ValueError("Not a valid BIG archive")
            
        # Read file size and count
        self.file_size = self.read_uint32_le(file.read(4))
        file_count = self.read_uint32_be(file.read(4))
        
        # Read entries based on type
        if self.header == b'BIG5':
            file.seek(3, 1)  # Skip 3 bytes
            for i in range(file_count):
                file.seek(1, 1)  # Skip 1 byte
                offset = self.read_uint32_be(file.read(4))
                size = self.read_uint32_be(file.read(4))
                path = self.read_string(file)
                self.entries.append(FileEntry(offset, size, path))
        else:  # BIG4 or BIGF
            file.seek(4, 1)  # Skip 4 bytes
            for i in range(file_count):
                offset = self.read_uint32_be(file.read(4))
                size = self.read_uint32_be(file.read(4))
                path = self.read_string(file)
                self.entries.append(FileEntry(offset, size, path))
        
        # Load file data
        for entry in self.entries:
            file.seek(entry.offset)
            entry.data = file.read(entry.size)
            
    def save(self, filepath):
        # Calculate new offsets and total size
        current_offset = 12  # Header + file_size + file_count
        
        if self.header == b'BIG5':
            current_offset += 3  # Skip bytes
            # Calculate metadata size
            for entry in self.entries:
                current_offset += 1  # Skip byte
                current_offset += 8  # offset + size
                current_offset += len(entry.path) + 1  # path + null terminator
        else:
            current_offset += 4  # Skip bytes
            # Calculate metadata size
            for entry in self.entries:
                current_offset += 8  # offset + size
                current_offset += len(entry.path) + 1  # path + null terminator
        
        # Update offsets
        for entry in self.entries:
            entry.offset = current_offset
            current_offset += entry.size
            
        total_size = current_offset
        
        # Write to file
        with open(filepath, 'wb') as f:
            # Write header
            f.write(self.header)
            f.write(self.write_uint32_le(total_size))
            f.write(self.write_uint32_be(len(self.entries)))
            
            # Write metadata
            if self.header == b'BIG5':
                f.write(b'\x00' * 3)  # Skip bytes
                for entry in self.entries:
                    f.write(b'\x00')  # Skip byte
                    f.write(self.write_uint32_be(entry.offset))
                    f.write(self.write_uint32_be(entry.size))
                    f.write(self.write_string(entry.path))
            else:
                f.write(b'\x00' * 4)  # Skip bytes
                for entry in self.entries:
                    f.write(self.write_uint32_be(entry.offset))
                    f.write(self.write_uint32_be(entry.size))
                    f.write(self.write_string(entry.path))
            
            # Write file data
            for entry in self.entries:
                f.write(entry.data)
    
    def add_file(self, path, data):
        entry = FileEntry(0, len(data), path, data)
        entry.modified = True
        self.entries.append(entry)
        return entry
    
    def remove_file(self, entry):
        self.entries.remove(entry)
    
    def update_file(self, entry, data):
        entry.data = data
        entry.size = len(data)
        entry.modified = True

class FindDialog:
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.find_window = None
        self.search_var = tk.StringVar()
        self.case_var = tk.BooleanVar()
        self.current_match = 0
        self.matches = []
        
    def show(self):
        if self.find_window and self.find_window.winfo_exists():
            self.find_window.lift()
            return
            
        self.find_window = tk.Toplevel(self.parent)
        self.find_window.title("Find")
        self.find_window.geometry("400x150")
        self.find_window.transient(self.parent)
        
        # Main frame
        main_frame = ttk.Frame(self.find_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search entry
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Find:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind('<Return>', lambda e: self.find_next())
        search_entry.bind('<KeyRelease>', lambda e: self.on_search_change())
        
        # Options
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="Case sensitive", 
                        variable=self.case_var, 
                        command=self.on_search_change).pack(side=tk.LEFT)
        
        self.match_label = ttk.Label(options_frame, text="")
        self.match_label.pack(side=tk.RIGHT)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Find Next", command=self.find_next).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Find Previous", command=self.find_previous).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Close", command=self.close).pack(side=tk.RIGHT, padx=2)
        
        # Get selected text if any
        try:
            selected_text = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.search_var.set(selected_text)
        except tk.TclError:
            pass
        
        # Focus on search entry
        search_entry.focus_set()
        search_entry.select_range(0, tk.END)
        
        # Bind escape key to close
        self.find_window.bind('<Escape>', lambda e: self.close())
        
        # Remove all tags when window opens
        self.text_widget.tag_remove('search', '1.0', tk.END)
        self.text_widget.tag_remove('current_match', '1.0', tk.END)
        
        # Configure tags
        self.text_widget.tag_configure('search', background='yellow')
        self.text_widget.tag_configure('current_match', background='orange')
        
        # If we have search text, find all matches
        if self.search_var.get():
            self.find_all()
        
    def on_search_change(self):
        self.find_all()
        
    def find_all(self):
        # Clear previous highlights
        self.text_widget.tag_remove('search', '1.0', tk.END)
        self.text_widget.tag_remove('current_match', '1.0', tk.END)
        self.matches = []
        self.current_match = 0
        
        search_term = self.search_var.get()
        if not search_term:
            self.match_label.config(text="")
            return
            
        # Search for all matches
        start_pos = '1.0'
        case_sensitive = self.case_var.get()
        
        while True:
            pos = self.text_widget.search(search_term, start_pos, tk.END, 
                                         nocase=not case_sensitive)
            if not pos:
                break
                
            end_pos = f"{pos}+{len(search_term)}c"
            self.matches.append((pos, end_pos))
            self.text_widget.tag_add('search', pos, end_pos)
            start_pos = end_pos
            
        # Update match counter
        if self.matches:
            self.current_match = 0
            self.highlight_current_match()
            self.update_match_label()
        else:
            self.match_label.config(text="No matches found")
            
    def find_next(self):
        if not self.matches:
            self.find_all()
            return
            
        if self.matches:
            self.current_match = (self.current_match + 1) % len(self.matches)
            self.highlight_current_match()
            self.update_match_label()
            
    def find_previous(self):
        if not self.matches:
            self.find_all()
            return
            
        if self.matches:
            self.current_match = (self.current_match - 1) % len(self.matches)
            self.highlight_current_match()
            self.update_match_label()
            
    def highlight_current_match(self):
        # Remove previous current match highlight
        self.text_widget.tag_remove('current_match', '1.0', tk.END)
        
        if self.matches:
            pos, end_pos = self.matches[self.current_match]
            self.text_widget.tag_add('current_match', pos, end_pos)
            self.text_widget.see(pos)
            
    def update_match_label(self):
        if self.matches:
            self.match_label.config(text=f"Match {self.current_match + 1} of {len(self.matches)}")
        else:
            self.match_label.config(text="No matches found")
            
    def close(self):
        # Remove all highlights
        self.text_widget.tag_remove('search', '1.0', tk.END)
        self.text_widget.tag_remove('current_match', '1.0', tk.END)
        if self.find_window:
            self.find_window.destroy()

class BIGArchiveEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("BIG Archive Editor")
        self.root.geometry("1200x800")
        
        self.archive = None
        self.current_file = None
        self.current_entry = None
        self.entry_map = {}  # Maps tree item IDs to entries
        self.find_dialog = None  # Will be initialized after text editor is created
        
        self.setup_ui()
        self.setup_styles()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TButton', padding=6)
        style.configure('Treeview', rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Archive", command=self.open_archive, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Archive", command=self.save_archive, accelerator="Ctrl+S")
        file_menu.add_command(label="Save Archive As...", command=self.save_archive_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self.show_find_dialog, accelerator="Ctrl+F")
        
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Open", command=self.open_archive).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_archive).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Add File", command=self.add_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Extract File", command=self.extract_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete File", command=self.delete_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Replace File", command=self.replace_file).pack(side=tk.LEFT, padx=2)
        
        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - File tree
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Search box
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_tree)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Tree view
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=('size', 'offset', 'modified'), show='tree headings')
        self.tree.heading('#0', text='File Path')
        self.tree.heading('size', text='Size')
        self.tree.heading('offset', text='Offset')
        self.tree.heading('modified', text='Modified')
        
        self.tree.column('#0', width=400)
        self.tree.column('size', width=100)
        self.tree.column('offset', width=100)
        self.tree.column('modified', width=80)
        
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        # Right panel - File viewer/editor
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        # File info
        info_frame = ttk.LabelFrame(right_frame, text="File Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.info_label = ttk.Label(info_frame, text="No file selected")
        self.info_label.pack(anchor=tk.W)
        
        # Editor notebook
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Text editor tab
        text_frame = ttk.Frame(self.notebook)
        self.notebook.add(text_frame, text="Text Editor")
        
        self.text_editor = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.text_editor.pack(fill=tk.BOTH, expand=True)
        
        # Initialize find dialog
        self.find_dialog = FindDialog(self.root, self.text_editor)
        
        editor_toolbar = ttk.Frame(text_frame)
        editor_toolbar.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        ttk.Button(editor_toolbar, text="Save Changes", command=self.save_text_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(editor_toolbar, text="Revert", command=self.revert_text_changes).pack(side=tk.LEFT)
        ttk.Button(editor_toolbar, text="Find", command=self.show_find_dialog).pack(side=tk.LEFT, padx=5)
        
        # Hex viewer tab
        hex_frame = ttk.Frame(self.notebook)
        self.notebook.add(hex_frame, text="Hex Viewer")
        
        self.hex_viewer = scrolledtext.ScrolledText(hex_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.hex_viewer.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_archive())
        self.root.bind('<Control-s>', lambda e: self.save_archive())
        self.root.bind('<Control-f>', lambda e: self.show_find_dialog())
        
    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.update_idletasks()
        
    def open_archive(self):
        filepath = filedialog.askopenfilename(
            title="Open BIG Archive",
            filetypes=[("BIG Archives", "*.big *.BIG"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.archive = BIGArchive()
                self.archive.load(filepath)
                app.node_integration.integrate()
                self.current_file = filepath
                self.populate_tree()
                self.update_status(f"Loaded: {os.path.basename(filepath)} ({len(self.archive.entries)} files)")
                self.root.title(f"BIG Archive Editor - {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open archive: {str(e)}")
                
    def save_archive(self):
        if not self.archive or not self.current_file:
            self.save_archive_as()
            return
            
        try:
            self.archive.save(self.current_file)
            self.update_status(f"Saved: {os.path.basename(self.current_file)}")
            self.refresh_tree()
            messagebox.showinfo("Success", "Archive saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save archive: {str(e)}")
            
    def save_archive_as(self):
        if not self.archive:
            messagebox.showwarning("Warning", "No archive loaded")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Save BIG Archive As",
            defaultextension=".big",
            filetypes=[("BIG Archives", "*.big"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.archive.save(filepath)
                self.current_file = filepath
                self.update_status(f"Saved as: {os.path.basename(filepath)}")
                self.root.title(f"BIG Archive Editor - {os.path.basename(filepath)}")
                messagebox.showinfo("Success", "Archive saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save archive: {str(e)}")
                
    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.entry_map.clear()  # Clear the entry map
        
        if not self.archive:
            return
            
        # Build directory structure
        dirs = {}
        
        for entry in self.archive.entries:
            parts = entry.path.split('/')
            parent = ''
            
            for i, part in enumerate(parts[:-1]):
                path = '/'.join(parts[:i+1])
                if path not in dirs:
                    dirs[path] = self.tree.insert(parent, 'end', text=part, open=False)
                parent = dirs[path]
                
            # Insert file
            size_str = self.format_size(entry.size)
            offset_str = f"0x{entry.offset:08X}"
            modified_str = "Yes" if entry.modified else "No"
            
            item = self.tree.insert(parent, 'end', text=parts[-1], 
                                   values=(size_str, offset_str, modified_str),
                                   tags=('file',))
            self.entry_map[item] = entry  # Store entry in the map
            
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
        
    def filter_tree(self, *args):
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.populate_tree()
            return
            
        self.tree.delete(*self.tree.get_children())
        self.entry_map.clear()  # Clear the entry map
        
        for entry in self.archive.entries:
            if search_term in entry.path.lower():
                size_str = self.format_size(entry.size)
                offset_str = f"0x{entry.offset:08X}"
                modified_str = "Yes" if entry.modified else "No"
                
                item = self.tree.insert('', 'end', text=entry.path,
                                       values=(size_str, offset_str, modified_str),
                                       tags=('file',))
                self.entry_map[item] = entry  # Store entry in the map
                
    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        if 'file' not in self.tree.item(item, 'tags'):
            return
            
        entry = self.entry_map.get(item)
        if not entry:
            return
            
        self.current_entry = entry
        self.info_label.config(text=f"Path: {entry.path}\nSize: {self.format_size(entry.size)}\n"
                                   f"Offset: 0x{entry.offset:08X}\nModified: {'Yes' if entry.modified else 'No'}")
        
        # Load content into viewers
        self.load_file_content(entry)
        
    def on_tree_double_click(self, event):
        self.extract_file()
        
    def load_file_content(self, entry):
        # Text editor
        self.text_editor.delete('1.0', tk.END)
        try:
            text_content = entry.data.decode('utf-8', errors='ignore')
            self.text_editor.insert('1.0', text_content)
        except:
            self.text_editor.insert('1.0', "[Binary file - cannot display as text]")
            
        # Hex viewer
        self.hex_viewer.delete('1.0', tk.END)
        hex_content = self.format_hex(entry.data)
        self.hex_viewer.insert('1.0', hex_content)
        
    def format_hex(self, data, bytes_per_line=16):
        lines = []
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i+bytes_per_line]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f'{i:08X}: {hex_part:<48} {ascii_part}')
        return '\n'.join(lines)
        
    def save_text_changes(self):
        if not self.current_entry:
            return
            
        try:
            new_content = self.text_editor.get('1.0', tk.END).rstrip('\n')
            new_data = new_content.encode('utf-8')
            self.archive.update_file(self.current_entry, new_data)
            self.refresh_tree()
            self.update_status(f"Updated: {self.current_entry.path}")
            messagebox.showinfo("Success", "File updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update file: {str(e)}")
            
    def revert_text_changes(self):
        if self.current_entry:
            self.load_file_content(self.current_entry)
            
    def show_find_dialog(self):
        # Only show find dialog if we're on the text editor tab
        if self.find_dialog and self.notebook.index(self.notebook.select()) == 0:
            self.find_dialog.show()
            
    def add_file(self):
        if not self.archive:
            messagebox.showwarning("Warning", "No archive loaded")
            return
            
        filepath = filedialog.askopenfilename(title="Select file to add")
        if not filepath:
            return
            
        try:
            # Ask for internal path
            internal_path = simpledialog.askstring(
                "Internal Path",
                "Enter the internal path for this file:",
                initialvalue=os.path.basename(filepath)
            )
            
            if not internal_path:
                return
                
            with open(filepath, 'rb') as f:
                data = f.read()
                
            self.archive.add_file(internal_path, data)
            self.populate_tree()
            self.update_status(f"Added: {internal_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add file: {str(e)}")
            
    def extract_file(self):
        if not self.current_entry:
            messagebox.showwarning("Warning", "No file selected")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Extract file to",
            initialfile=os.path.basename(self.current_entry.path)
        )
        
        if filepath:
            try:
                with open(filepath, 'wb') as f:
                    f.write(self.current_entry.data)
                self.update_status(f"Extracted: {os.path.basename(filepath)}")
                messagebox.showinfo("Success", "File extracted successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to extract file: {str(e)}")
                
    def delete_file(self):
        if not self.current_entry:
            messagebox.showwarning("Warning", "No file selected")
            return
            
        if messagebox.askyesno("Confirm Delete", f"Delete {self.current_entry.path}?"):
            self.archive.remove_file(self.current_entry)
            self.current_entry = None
            self.populate_tree()
            self.update_status("File deleted")
            
    def replace_file(self):
        if not self.current_entry:
            messagebox.showwarning("Warning", "No file selected")
            return
            
        filepath = filedialog.askopenfilename(title="Select replacement file")
        if not filepath:
            return
            
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
                
            self.archive.update_file(self.current_entry, data)
            self.load_file_content(self.current_entry)
            self.refresh_tree()
            self.update_status(f"Replaced: {self.current_entry.path}")
            messagebox.showinfo("Success", "File replaced successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace file: {str(e)}")
            
    def refresh_tree(self):
        # Update the tree without losing selection
        selection = self.tree.selection()
        selected_path = None
        
        if selection and self.current_entry:
            selected_path = self.current_entry.path
            
        self.populate_tree()
        
        # Restore selection
        if selected_path:
            for item in self.tree.get_children(''):
                if self.find_and_select_item(item, selected_path):
                    break
                    
    def find_and_select_item(self, item, path):
        if 'file' in self.tree.item(item, 'tags'):
            entry = self.entry_map.get(item)
            if entry and entry.path == path:
                self.tree.selection_set(item)
                self.tree.see(item)
                return True
                    
        for child in self.tree.get_children(item):
            if self.find_and_select_item(child, path):
                return True
        return False

if __name__ == '__main__':
    root = tk.Tk()
    app = BIGArchiveEditor(root)
    
    # Apply enhanced node editor integration if available
    if NODE_EDITOR_AVAILABLE:
        app.node_integration = EnhancedNodeEditorIntegration(app)
        app.node_integration.integrate()
    
    root.mainloop()