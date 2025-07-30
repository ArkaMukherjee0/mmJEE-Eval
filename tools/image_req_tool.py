import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import json
from PIL import Image, ImageTk
import os
from pathlib import Path

class ImageAnnotationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JEE Advanced Image Annotation Tool")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')
        
        # Data variables
        self.base_path = "final_dataset"
        self.csv_path = os.path.join(self.base_path, "jee_advanced_combined.csv")
        self.json_path = os.path.join(self.base_path, "jee_advanced_combined.json")
        self.df = None
        self.current_index = 0
        self.annotations = {}
        self.unsaved_changes = False
        
        # Load data
        self.load_data()
        
        # Setup UI
        self.setup_ui()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Load first image
        self.load_current_image()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_data(self):
        """Load the dataset from CSV file"""
        try:
            self.df = pd.read_csv(self.csv_path)
            
            # Initialize annotations with existing data if available
            if 'requires_image' in self.df.columns:
                for idx, row in self.df.iterrows():
                    if pd.notna(row['requires_image']):
                        self.annotations[idx] = bool(row['requires_image'])
            else:
                # Add requires_image column if it doesn't exist
                self.df['requires_image'] = None
            
            print(f"Loaded {len(self.df)} questions from dataset")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset: {str(e)}")
            self.root.destroy()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Top panel - Progress and info
        self.setup_top_panel(main_frame)
        
        # Middle panel - Image display
        self.setup_image_panel(main_frame)
        
        # Bottom panel - Controls
        self.setup_control_panel(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_top_panel(self, parent):
        """Setup the top information panel"""
        top_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Title
        title_label = tk.Label(top_frame, text="JEE Advanced Image Annotation Tool", 
                              font=('Arial', 16, 'bold'), bg='#34495e', fg='#ecf0f1')
        title_label.pack(pady=10)
        
        # Progress info
        info_frame = tk.Frame(top_frame, bg='#34495e')
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(info_frame, variable=self.progress_var, 
                                          maximum=100, length=300)
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 20))
        
        # Current question info
        self.info_label = tk.Label(info_frame, font=('Arial', 10), 
                                  bg='#34495e', fg='#bdc3c7')
        self.info_label.pack(side=tk.LEFT)
        
        # Statistics
        self.stats_label = tk.Label(info_frame, font=('Arial', 10), 
                                   bg='#34495e', fg='#bdc3c7')
        self.stats_label.pack(side=tk.RIGHT)
    
    def setup_image_panel(self, parent):
        """Setup the image display panel"""
        image_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Image canvas with scrollbars
        canvas_frame = tk.Frame(image_frame, bg='#34495e')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#ecf0f1', highlightthickness=0)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and canvas
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Question details panel
        details_frame = tk.Frame(image_frame, bg='#34495e', width=250)
        details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        details_frame.pack_propagate(False)
        
        tk.Label(details_frame, text="Question Details", font=('Arial', 12, 'bold'),
                bg='#34495e', fg='#ecf0f1').pack(pady=(10, 20))
        
        self.detail_labels = {}
        details = ['Question ID', 'Year', 'Paper', 'Subject', 'Type', 'Language']
        
        for detail in details:
            frame = tk.Frame(details_frame, bg='#34495e')
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(frame, text=f"{detail}:", font=('Arial', 9, 'bold'),
                    bg='#34495e', fg='#bdc3c7', anchor='w').pack(anchor='w')
            
            self.detail_labels[detail.lower().replace(' ', '_')] = tk.Label(
                frame, font=('Arial', 9), bg='#34495e', fg='#ecf0f1', 
                anchor='w', wraplength=200)
            self.detail_labels[detail.lower().replace(' ', '_')].pack(anchor='w')
    
    def setup_control_panel(self, parent):
        """Setup the control buttons panel"""
        control_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Navigation buttons
        nav_frame = tk.Frame(control_frame, bg='#34495e')
        nav_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Previous button
        self.prev_btn = tk.Button(nav_frame, text="◀ Previous (A)", 
                                 command=self.previous_image, font=('Arial', 10),
                                 bg='#3498db', fg='white', relief=tk.FLAT,
                                 padx=15, pady=8)
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Next button  
        self.next_btn = tk.Button(nav_frame, text="Next (D) ▶", 
                                 command=self.next_image, font=('Arial', 10),
                                 bg='#3498db', fg='white', relief=tk.FLAT,
                                 padx=15, pady=8)
        self.next_btn.pack(side=tk.LEFT)
        
        # Annotation buttons (center)
        annotation_frame = tk.Frame(control_frame, bg='#34495e')
        annotation_frame.pack(expand=True)
        
        tk.Label(annotation_frame, text="Does this question REQUIRE the image to be answered?", 
                font=('Arial', 12, 'bold'), bg='#34495e', fg='#ecf0f1').pack(pady=(15, 10))
        
        button_frame = tk.Frame(annotation_frame, bg='#34495e')
        button_frame.pack()
        
        # Yes button
        self.yes_btn = tk.Button(button_frame, text="✓ YES (Y)", 
                                command=lambda: self.annotate(True), 
                                font=('Arial', 12, 'bold'),
                                bg='#27ae60', fg='white', relief=tk.FLAT,
                                padx=25, pady=12)
        self.yes_btn.pack(side=tk.LEFT, padx=10)
        
        # No button
        self.no_btn = tk.Button(button_frame, text="✗ NO (N)", 
                               command=lambda: self.annotate(False), 
                               font=('Arial', 12, 'bold'),
                               bg='#e74c3c', fg='white', relief=tk.FLAT,
                               padx=25, pady=12)
        self.no_btn.pack(side=tk.LEFT, padx=10)
        
        # Utility buttons (right)
        utility_frame = tk.Frame(control_frame, bg='#34495e')
        utility_frame.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Save button
        save_btn = tk.Button(utility_frame, text="💾 Save (Ctrl+S)", 
                            command=self.save_annotations, font=('Arial', 10),
                            bg='#f39c12', fg='white', relief=tk.FLAT,
                            padx=15, pady=8)
        save_btn.pack(pady=(0, 5))
        
        # Jump to question
        jump_frame = tk.Frame(utility_frame, bg='#34495e')
        jump_frame.pack()
        
        tk.Label(jump_frame, text="Jump to:", font=('Arial', 8),
                bg='#34495e', fg='#bdc3c7').pack()
        
        self.jump_entry = tk.Entry(jump_frame, width=8, font=('Arial', 9))
        self.jump_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        jump_btn = tk.Button(jump_frame, text="Go", command=self.jump_to_question,
                            font=('Arial', 8), bg='#9b59b6', fg='white',
                            relief=tk.FLAT, padx=8)
        jump_btn.pack(side=tk.LEFT)
    
    def setup_status_bar(self, parent):
        """Setup the status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        status_bar = tk.Label(parent, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W,
                             bg='#34495e', fg='#bdc3c7', font=('Arial', 9))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Key-y>', lambda e: self.annotate(True))
        self.root.bind('<Key-Y>', lambda e: self.annotate(True))
        self.root.bind('<Key-n>', lambda e: self.annotate(False))
        self.root.bind('<Key-N>', lambda e: self.annotate(False))
        self.root.bind('<Key-a>', lambda e: self.previous_image())
        self.root.bind('<Key-A>', lambda e: self.previous_image())
        self.root.bind('<Key-d>', lambda e: self.next_image())
        self.root.bind('<Key-D>', lambda e: self.next_image())
        self.root.bind('<Control-s>', lambda e: self.save_annotations())
        self.root.bind('<Left>', lambda e: self.previous_image())
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('<Return>', lambda e: self.jump_to_question())
        
        # Focus on root to capture key events
        self.root.focus_set()
    
    def load_current_image(self):
        """Load and display the current image"""
        if self.df is None or len(self.df) == 0:
            return
        
        try:
            row = self.df.iloc[self.current_index]
            
            # Construct full image path
            image_path = os.path.join(self.base_path, row['image_path'])
            
            if not os.path.exists(image_path):
                self.status_var.set(f"Image not found: {image_path}")
                self.canvas.delete("all")
                self.canvas.create_text(400, 300, text="Image not found", 
                                       font=('Arial', 16), fill='red')
                return
            
            # Load and display image
            pil_image = Image.open(image_path)
            
            # Resize image if too large
            max_width, max_height = 800, 600
            if pil_image.width > max_width or pil_image.height > max_height:
                pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(pil_image)
            
            # Clear canvas and add image
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update UI elements
            self.update_ui_elements(row)
            
            self.status_var.set(f"Loaded: {os.path.basename(image_path)}")
            
        except Exception as e:
            self.status_var.set(f"Error loading image: {str(e)}")
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def update_ui_elements(self, row):
        """Update UI elements with current question data"""
        # Update question details
        self.detail_labels['question_id'].config(text=row['question_id'])
        self.detail_labels['year'].config(text=str(row['year']))
        self.detail_labels['paper'].config(text=row['paper'])
        self.detail_labels['subject'].config(text=row['subject'])
        self.detail_labels['type'].config(text=row['question_type'])
        self.detail_labels['language'].config(text=row['language'])
        
        # Update progress
        progress = (self.current_index + 1) / len(self.df) * 100
        self.progress_var.set(progress)
        
        # Update info label
        self.info_label.config(text=f"Question {self.current_index + 1} of {len(self.df)}")
        
        # Update statistics
        annotated_count = len(self.annotations)
        remaining_count = len(self.df) - annotated_count
        self.stats_label.config(text=f"Annotated: {annotated_count} | Remaining: {remaining_count}")
        
        # Update button states based on current annotation
        current_annotation = self.annotations.get(self.current_index)
        
        # Reset button colors
        self.yes_btn.config(bg='#27ae60')
        self.no_btn.config(bg='#e74c3c')
        
        # Highlight current selection
        if current_annotation is True:
            self.yes_btn.config(bg='#2ecc71')  # Brighter green
        elif current_annotation is False:
            self.no_btn.config(bg='#c0392b')  # Darker red
        
        # Update navigation buttons
        self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_index < len(self.df) - 1 else tk.DISABLED)
    
    def annotate(self, requires_image):
        """Annotate current question"""
        self.annotations[self.current_index] = requires_image
        self.unsaved_changes = True
        
        # Update UI
        self.update_ui_elements(self.df.iloc[self.current_index])
        
        self.status_var.set(f"Annotated: {'Requires image' if requires_image else 'Does not require image'}")
        
        # Auto-advance to next question
        self.root.after(500, self.next_image)  # Small delay for visual feedback
    
    def previous_image(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()
    
    def next_image(self):
        """Go to next image"""
        if self.current_index < len(self.df) - 1:
            self.current_index += 1
            self.load_current_image()
    
    def jump_to_question(self):
        """Jump to specific question number"""
        try:
            question_num = int(self.jump_entry.get())
            if 1 <= question_num <= len(self.df):
                self.current_index = question_num - 1
                self.load_current_image()
                self.jump_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", f"Question number must be between 1 and {len(self.df)}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid question number")
    
    def save_annotations(self):
        """Save annotations to both CSV and JSON files"""
        try:
            # Update DataFrame with annotations
            for idx, requires_image in self.annotations.items():
                self.df.at[idx, 'requires_image'] = requires_image
            
            # Save CSV
            self.df.to_csv(self.csv_path, index=False)
            
            # Save JSON
            json_data = self.df.to_dict('records')
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            self.unsaved_changes = False
            self.status_var.set(f"Saved {len(self.annotations)} annotations successfully")
            messagebox.showinfo("Success", f"Saved {len(self.annotations)} annotations to files")
            
        except Exception as e:
            self.status_var.set(f"Error saving: {str(e)}")
            messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
    
    def on_closing(self):
        """Handle window closing"""
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "Unsaved Changes", 
                "You have unsaved annotations. Do you want to save before closing?"
            )
            if result is True:  # Yes
                self.save_annotations()
                self.root.destroy()
            elif result is False:  # No
                self.root.destroy()
            # Cancel - do nothing
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = ImageAnnotationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()