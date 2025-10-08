import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pandas as pd
from PIL import Image, ImageTk
import os
import json
from pathlib import Path
from datetime import datetime
import pyperclip
import io
import random

class CrossLingualAnalysisGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cross-Lingual Analysis Annotator")
        self.root.geometry("1800x1000")
        self.root.configure(bg='#f5f5f5')
        
        # Data storage
        self.csv_path = r"multilingual_analysis_results.csv"
        self.df = None
        self.filtered_questions = pd.DataFrame()
        self.current_index = 0
        self.total_questions = 0
        
        # Target models
        self.target_models = {
            'internvl3-78b': 'InternVL3 78B',
            'gpt-5': 'GPT-5',
            'grok4-fast': 'Grok 4 Fast',
            'llama4-scout': 'Llama 4 Scout',
            'llama4-maverick': 'Llama 4 Maverick'
        }
        
        # Correctness categories - sample 10 from each
        self.correctness_categories = [
            'both_correct',
            'english_correct_hindi_incorrect', 
            'english_incorrect_hindi_correct',
            'both_incorrect'
        ]
        
        # Progress tracking
        self.progress_file = "crosslingual_analysis_progress.json"
        self.results_file = "crosslingual_analysis_results.csv"
        self.completed_questions = set()
        self.evaluations = {}
        
        # Analysis questions
        self.error_types = {
            "conceptual_errors": "Conceptual errors (inability to use correct concepts)",
            "grounding_errors": "Grounding errors (wrong formulas, incorrect modeling, wrong equation setup)",
            "computation_errors": "Computation errors (algebraic manipulation, arithmetic errors)",
            "instruction_errors": "Instruction following errors (not following format, units, precision requirements)"
        }
        
        self.crosslingual_questions = {
            "appropriate_language": "Do the models use appropriate target language?",
            "internal_switching": "Do models switch to English internally while maintaining Hindi output format?",
            "phrase_reasoning": "Do models quote non-English phrases and reason about them in English?"
        }
        
        # Image settings
        self.image_base_path = r"final_dataset\images"
        self.zoom_factor = 1.0
        self.original_image = None
        
        # Initialize variables for evaluation
        self.score_vars = {}
        
        # Load data and create GUI
        self.load_data()
        self.create_widgets()
        self.load_progress()
        
        if self.total_questions > 0:
            self.load_current_question()
    
    def load_data(self):
        """Load and filter data for analysis"""
        try:
            self.df = pd.read_csv(self.csv_path, encoding='utf-8')
            self.status_var.set(f"Loaded {len(self.df)} total records") if hasattr(self, 'status_var') else None
            
            # Filter for target models
            model_filtered = self.df[self.df['model_name'].isin(self.target_models.keys())].copy()
            
            # Sample 10 questions from each correctness category for each model
            sampled_questions = []
            
            for model in self.target_models.keys():
                model_data = model_filtered[model_filtered['model_name'] == model]
                
                for category in self.correctness_categories:
                    category_data = model_data[model_data['correctness_category'] == category]
                    
                    # Sample up to 10 questions from this category
                    sample_size = min(10, len(category_data))
                    if sample_size > 0:
                        sampled = category_data.sample(n=sample_size, random_state=42)
                        sampled_questions.append(sampled)
            
            if sampled_questions:
                self.filtered_questions = pd.concat(sampled_questions, ignore_index=True)
                # Shuffle the final dataset
                self.filtered_questions = self.filtered_questions.sample(frac=1, random_state=42).reset_index(drop=True)
            else:
                self.filtered_questions = pd.DataFrame()
            
            self.total_questions = len(self.filtered_questions)
            
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Filtered to {self.total_questions} questions for annotation")
            
            print(f"Loaded {self.total_questions} questions for cross-lingual analysis")
            
        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            print(error_msg)
            if hasattr(self, 'status_var'):
                self.status_var.set(error_msg)
            messagebox.showerror("Data Loading Error", error_msg)
    
    def create_widgets(self):
        """Create the main GUI layout"""
        # Configure main window grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_container.columnconfigure(0, weight=2)  # Left panel
        main_container.columnconfigure(1, weight=3)  # Middle panel
        main_container.columnconfigure(2, weight=2)  # Right panel
        main_container.rowconfigure(1, weight=1)
        
        # Header
        self.create_header(main_container)
        
        # Main content
        content_frame = ttk.Frame(main_container)
        content_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=3)
        content_frame.columnconfigure(2, weight=2)
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Question info and navigation
        self.create_info_panel(content_frame)
        
        # Middle panel - Question image and responses
        self.create_content_panel(content_frame)
        
        # Right panel - Analysis form
        self.create_analysis_panel(content_frame)
        
        # Footer
        self.create_footer(main_container)
    
    def create_header(self, parent):
        """Create header with progress and navigation"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        # Title and progress
        title_label = ttk.Label(header_frame, text="Cross-Lingual Analysis Annotator", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_label = ttk.Label(header_frame, text="Question 0/0", 
                                      font=('Arial', 12))
        self.progress_label.grid(row=0, column=2, sticky=tk.E)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(header_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Navigation buttons
        nav_frame = ttk.Frame(header_frame)
        nav_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(nav_frame, text="◀ Previous", command=self.previous_question).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(nav_frame, text="Next ▶", command=self.next_question).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(nav_frame, text="Jump to...", command=self.jump_to_question).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(nav_frame, text="Export Results", command=self.export_results).pack(side=tk.RIGHT)
    
    def create_info_panel(self, parent):
        """Create left panel with question information"""
        info_frame = ttk.LabelFrame(parent, text="Question Information", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(1, weight=1)
        
        # Question metadata
        self.info_text = scrolledtext.ScrolledText(info_frame, height=12, width=35, 
                                                 font=('Consolas', 9))
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Correct answer
        answer_frame = ttk.LabelFrame(info_frame, text="Correct Answer", padding="5")
        answer_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        answer_frame.columnconfigure(0, weight=1)
        
        self.correct_answer_text = tk.Text(answer_frame, height=3, width=35,
                                         font=('Arial', 11, 'bold'),
                                         bg='#f0f8ff', fg='#006400',
                                         wrap=tk.WORD)
        self.correct_answer_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Predicted answers
        pred_frame = ttk.LabelFrame(info_frame, text="Predicted Answers", padding="5")
        pred_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        pred_frame.columnconfigure(0, weight=1)
        
        ttk.Label(pred_frame, text="English:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W)
        self.pred_en_text = tk.Text(pred_frame, height=2, width=35, font=('Arial', 9),
                                   bg='#fff5ee', wrap=tk.WORD)
        self.pred_en_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(2, 5))
        
        ttk.Label(pred_frame, text="Hindi:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W)
        self.pred_hi_text = tk.Text(pred_frame, height=2, width=35, font=('Arial', 9),
                                   bg='#f0fff0', wrap=tk.WORD)
        self.pred_hi_text.grid(row=3, column=0, sticky=(tk.W, tk.E))
    
    def create_content_panel(self, parent):
        """Create middle panel with image and responses"""
        content_frame = ttk.Frame(parent)
        content_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        # Image display
        image_frame = ttk.LabelFrame(content_frame, text="Question Image", padding="5")
        image_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(1, weight=1)
        
        # Image controls
        img_controls = ttk.Frame(image_frame)
        img_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Language selection
        self.language_var = tk.StringVar(value="English")
        ttk.Radiobutton(img_controls, text="English", variable=self.language_var,
                       value="English", command=self.update_question_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(img_controls, text="Hindi", variable=self.language_var,
                       value="Hindi", command=self.update_question_image).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(img_controls, text="Copy Image", command=self.copy_image).pack(side=tk.RIGHT)
        
        # Image canvas
        self.canvas = tk.Canvas(image_frame, bg='white', height=200)
        img_scroll = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=img_scroll.set)
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        img_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Response tabs
        response_frame = ttk.LabelFrame(content_frame, text="Model Responses", padding="5")
        response_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        self.response_notebook = ttk.Notebook(response_frame)
        self.response_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # English response tab
        en_frame = ttk.Frame(self.response_notebook)
        self.response_notebook.add(en_frame, text="English Response")
        en_frame.columnconfigure(0, weight=1)
        en_frame.rowconfigure(1, weight=1)
        
        ttk.Button(en_frame, text="📋 Copy English Response", 
                  command=lambda: self.copy_response('english')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.english_response = scrolledtext.ScrolledText(en_frame, wrap=tk.WORD, font=('Arial', 10))
        self.english_response.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Hindi response tab
        hi_frame = ttk.Frame(self.response_notebook)
        self.response_notebook.add(hi_frame, text="Hindi Response")
        hi_frame.columnconfigure(0, weight=1)
        hi_frame.rowconfigure(1, weight=1)
        
        ttk.Button(hi_frame, text="📋 Copy Hindi Response",
                  command=lambda: self.copy_response('hindi')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.hindi_response = scrolledtext.ScrolledText(hi_frame, wrap=tk.WORD, font=('Arial', 10))
        self.hindi_response.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_analysis_panel(self, parent):
        """Create right panel with analysis form"""
        analysis_frame = ttk.LabelFrame(parent, text="Analysis Form", padding="10")
        analysis_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        analysis_frame.columnconfigure(0, weight=1)
        analysis_frame.rowconfigure(0, weight=1)
        
        # Scrollable analysis form
        canvas = tk.Canvas(analysis_frame)
        scrollbar = ttk.Scrollbar(analysis_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Create analysis questions
        self.create_analysis_questions(scrollable_frame)
        
        # Action buttons
        action_frame = ttk.Frame(analysis_frame)
        action_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(action_frame, text="Save & Continue", 
                  command=self.save_analysis).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Clear Form", 
                  command=self.clear_form).pack(side=tk.LEFT)
    
    def create_analysis_questions(self, parent):
        """Create analysis questions with scales"""
        row = 0
        self.score_vars = {}
        
        # Error type analysis (0-10 scale)
        error_header = ttk.Label(parent, text="Error Analysis (0-10 Scale)", 
                               font=('Arial', 12, 'bold'), foreground='#2E4A8A')
        error_header.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1
        
        for error_id, error_desc in self.error_types.items():
            # Error description
            desc_label = ttk.Label(parent, text=error_desc, wraplength=300, 
                                 font=('Arial', 9), justify=tk.LEFT)
            desc_label.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
            row += 1
            
            # Scale
            scale_frame = ttk.Frame(parent)
            scale_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            scale_frame.columnconfigure(1, weight=1)
            
            var = tk.IntVar(value=0)
            self.score_vars[error_id] = var
            
            ttk.Label(scale_frame, text="0").grid(row=0, column=0, padx=(0, 5))
            scale = ttk.Scale(scale_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                            variable=var, command=lambda val, eid=error_id: self.update_scale_label(eid, val))
            scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
            ttk.Label(scale_frame, text="10").grid(row=0, column=2, padx=(5, 0))
            
            # Value label
            value_label = ttk.Label(scale_frame, text="0", font=('Arial', 10, 'bold'))
            value_label.grid(row=1, column=1, pady=(2, 0))
            setattr(self, f"scale_label_{error_id}", value_label)
            
            row += 1
        
        # Separator
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, 
                                                       sticky=(tk.W, tk.E), pady=(15, 15))
        row += 1
        
        # Cross-lingual analysis (binary checkboxes)
        crossling_header = ttk.Label(parent, text="Cross-Lingual Analysis", 
                                   font=('Arial', 12, 'bold'), foreground='#8B4513')
        crossling_header.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1
        
        for question_id, question_text in self.crosslingual_questions.items():
            var = tk.BooleanVar()
            self.score_vars[question_id] = var
            
            checkbox = ttk.Checkbutton(parent, text=question_text, variable=var)
            checkbox.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
            row += 1
        
        # Notes section
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2,
                                                       sticky=(tk.W, tk.E), pady=(15, 10))
        row += 1
        
        notes_label = ttk.Label(parent, text="Additional Notes", font=('Arial', 11, 'bold'))
        notes_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1
        
        self.notes_text = scrolledtext.ScrolledText(parent, height=6, width=40, wrap=tk.WORD)
        self.notes_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
    
    def create_footer(self, parent):
        """Create footer with status"""
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(parent, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def update_scale_label(self, question_id, value):
        """Update scale value label"""
        rounded_value = round(float(value))
        self.score_vars[question_id].set(rounded_value)
        label = getattr(self, f"scale_label_{question_id}")
        label.config(text=str(rounded_value))
    
    def load_current_question(self):
        """Load and display current question"""
        if self.current_index >= self.total_questions:
            messagebox.showinfo("Complete", "All questions have been analyzed!")
            return
        
        current_question = self.filtered_questions.iloc[self.current_index]
        
        # Update progress
        self.progress_label.config(text=f"Question {self.current_index + 1} of {self.total_questions}")
        self.progress_bar['maximum'] = self.total_questions
        self.progress_bar['value'] = self.current_index + 1
        
        # Update question info
        self.update_question_info(current_question)
        
        # Update image
        self.update_question_image()
        
        # Update responses
        self.update_responses(current_question)
        
        # Load existing evaluation
        self.load_existing_evaluation(current_question)
        
        # Update status
        unique_id = self.get_unique_question_id(current_question)
        status_icon = "✓" if unique_id in self.completed_questions else "✗"
        self.status_var.set(f"Question {self.current_index + 1}: {current_question['model_name']} - {current_question['correctness_category']} [{status_icon}]")
    
    def update_question_info(self, question):
        """Update question information display"""
        info_text = f"""ID: {question['unique_question_id']}
Model: {self.target_models.get(question['model_name'], question['model_name'])}
Subject: {question['subject']}
Question Type: {question['question_type']}
Year: {question['year']} | Paper: {question['paper']}

Correctness Category: {question['correctness_category']}
English Correct: {question['is_correct_english']}
Hindi Correct: {question['is_correct_hindi']}"""
        
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_text)
        self.info_text.config(state='disabled')
        
        # Update correct answer
        self.correct_answer_text.config(state='normal')
        self.correct_answer_text.delete(1.0, tk.END)
        self.correct_answer_text.insert(1.0, str(question['correct_answer']))
        self.correct_answer_text.config(state='disabled')
        
        # Update predicted answers
        self.pred_en_text.config(state='normal')
        self.pred_en_text.delete(1.0, tk.END)
        self.pred_en_text.insert(1.0, str(question.get('predicted_answer_english', 'N/A')))
        self.pred_en_text.config(state='disabled')
        
        self.pred_hi_text.config(state='normal')
        self.pred_hi_text.delete(1.0, tk.END)
        self.pred_hi_text.insert(1.0, str(question.get('predicted_answer_hindi', 'N/A')))
        self.pred_hi_text.config(state='disabled')
    
    def update_question_image(self):
        """Update question image display"""
        if self.current_index >= self.total_questions:
            return
            
        current_question = self.filtered_questions.iloc[self.current_index]
        lang = self.language_var.get().lower()
        image_path_col = f'image_path_{lang}'
        
        if image_path_col not in current_question:
            return
        
        image_path = current_question[image_path_col]
        
        if not image_path or not os.path.exists(image_path):
            self.canvas.delete("all")
            self.canvas.create_text(200, 100, text="Image not found", fill='red')
            return
        
        try:
            image = Image.open(image_path)
            self.original_image = image.copy()
            
            # Resize for display
            max_width, max_height = 600, 200
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(200, 100, text=f"Error loading image: {str(e)}", fill='red')
    
    def update_responses(self, question):
        """Update response displays"""
        # English response
        self.english_response.config(state='normal')
        self.english_response.delete(1.0, tk.END)
        self.english_response.insert(1.0, str(question.get('full_response_english', 'No English response')))
        self.english_response.config(state='disabled')
        
        # Hindi response
        self.hindi_response.config(state='normal')
        self.hindi_response.delete(1.0, tk.END)
        self.hindi_response.insert(1.0, str(question.get('full_response_hindi', 'No Hindi response')))
        self.hindi_response.config(state='disabled')
    
    def get_unique_question_id(self, question):
        """Generate unique question ID"""
        return f"{question['unique_question_id']}_{question['model_name']}"
    
    def load_existing_evaluation(self, question):
        """Load existing evaluation if available"""
        unique_id = self.get_unique_question_id(question)
        
        if unique_id in self.evaluations:
            eval_data = self.evaluations[unique_id]
            
            # Load error scores
            for error_id in self.error_types.keys():
                if error_id in eval_data:
                    self.score_vars[error_id].set(eval_data[error_id])
                    label = getattr(self, f"scale_label_{error_id}")
                    label.config(text=str(eval_data[error_id]))
            
            # Load cross-lingual scores
            for question_id in self.crosslingual_questions.keys():
                if question_id in eval_data:
                    self.score_vars[question_id].set(eval_data[question_id])
            
            # Load notes
            self.notes_text.delete(1.0, tk.END)
            self.notes_text.insert(1.0, eval_data.get('notes', ''))
        else:
            self.clear_form()
    
    def copy_image(self):
        """Copy current image to clipboard in proper format"""
        if not self.original_image:
            messagebox.showwarning("Warning", "No image to copy")
            return
        
        success = False
        error_messages = []
        
        # Method 1: Try win32clipboard with proper BMP format
        try:
            import win32clipboard
            import win32con
            
            # Convert PIL image to BMP format for clipboard
            output = io.BytesIO()
            # Convert to RGB if necessary (removes alpha channel)
            rgb_image = self.original_image.convert('RGB')
            rgb_image.save(output, format='BMP')
            data = output.getvalue()[14:]  # Remove BMP file header for clipboard
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            success = True
            self.status_var.set("Image copied to clipboard (BMP format)")
            
        except ImportError:
            error_messages.append("win32clipboard not available")
        except Exception as e:
            error_messages.append(f"win32clipboard failed: {str(e)}")
        
        # Method 2: Try PowerShell method (Windows)
        if not success:
            try:
                import subprocess
                import tempfile
                import os
                
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    self.original_image.save(tmp_file.name, 'PNG')
                    tmp_path = tmp_file.name
                
                # Use PowerShell to copy image to clipboard
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $image = [System.Drawing.Image]::FromFile("{tmp_path}")
                [System.Windows.Forms.Clipboard]::SetImage($image)
                $image.Dispose()
                '''
                
                result = subprocess.run(['powershell', '-Command', ps_script], 
                                      capture_output=True, text=True, timeout=10)
                
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                if result.returncode == 0:
                    success = True
                    self.status_var.set("Image copied to clipboard (PowerShell)")
                else:
                    error_messages.append(f"PowerShell failed: {result.stderr}")
                    
            except Exception as e:
                error_messages.append(f"PowerShell method failed: {str(e)}")
        
        # Method 3: Try tkinter method (cross-platform)
        if not success:
            try:
                # Save to temporary file and copy path
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    self.original_image.save(tmp_file.name, 'PNG')
                    tmp_path = tmp_file.name
                
                # Copy file path to clipboard as fallback
                pyperclip.copy(tmp_path)
                success = True
                self.status_var.set(f"Temp image file path copied: {tmp_path}")
                messagebox.showinfo("Image Copied", 
                                  f"Image saved to temporary file and path copied to clipboard:\n{tmp_path}\n\n"
                                  f"You can paste this path or navigate to it to upload the image.")
                
            except Exception as e:
                error_messages.append(f"Temporary file method failed: {str(e)}")
        
        # Method 4: Final fallback - copy original image path
        if not success:
            try:
                current_question = self.filtered_questions.iloc[self.current_index]
                lang = self.language_var.get().lower()
                image_path = current_question[f'image_path_{lang}']
                
                if image_path and os.path.exists(image_path):
                    pyperclip.copy(image_path)
                    success = True
                    self.status_var.set("Original image path copied to clipboard")
                    messagebox.showinfo("Image Path Copied", 
                                      f"Original image path copied to clipboard:\n{image_path}")
                else:
                    error_messages.append("Original image path not found")
                    
            except Exception as e:
                error_messages.append(f"Path copy failed: {str(e)}")
        
        # If nothing worked, show error
        if not success:
            error_msg = "Failed to copy image to clipboard.\n\nErrors encountered:\n" + "\n".join(error_messages)
            error_msg += "\n\nTry installing pywin32: pip install pywin32"
            messagebox.showerror("Copy Failed", error_msg)
    
    def copy_response(self, language):
        """Copy response to clipboard"""
        try:
            if language == 'english':
                content = self.english_response.get(1.0, tk.END).strip()
            else:
                content = self.hindi_response.get(1.0, tk.END).strip()
            
            pyperclip.copy(content)
            self.status_var.set(f"{language.title()} response copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy response: {str(e)}")
    
    def clear_form(self):
        """Clear analysis form"""
        # Reset error scores to 0
        for error_id in self.error_types.keys():
            self.score_vars[error_id].set(0)
            label = getattr(self, f"scale_label_{error_id}")
            label.config(text="0")
        
        # Reset cross-lingual checkboxes
        for question_id in self.crosslingual_questions.keys():
            self.score_vars[question_id].set(False)
        
        # Clear notes
        self.notes_text.delete(1.0, tk.END)
    
    def save_analysis(self):
        """Save current analysis"""
        if self.current_index >= self.total_questions:
            return
        
        current_question = self.filtered_questions.iloc[self.current_index]
        unique_id = self.get_unique_question_id(current_question)
        
        # Collect evaluation data
        evaluation = {
            'unique_question_id': current_question['unique_question_id'],
            'model_name': current_question['model_name'],
            'subject': current_question['subject'],
            'correctness_category': current_question['correctness_category'],
            'evaluation_timestamp': datetime.now().isoformat()
        }
        
        # Add error scores
        for error_id in self.error_types.keys():
            evaluation[error_id] = self.score_vars[error_id].get()
        
        # Add cross-lingual scores
        for question_id in self.crosslingual_questions.keys():
            evaluation[question_id] = self.score_vars[question_id].get()
        
        # Add notes
        evaluation['notes'] = self.notes_text.get(1.0, tk.END).strip()
        
        # Store evaluation
        self.evaluations[unique_id] = evaluation
        self.completed_questions.add(unique_id)
        
        # Save to file
        self.save_to_file()
        
        # Update status and move to next
        self.status_var.set(f"Analysis saved for {unique_id}")
        messagebox.showinfo("Success", "Analysis saved successfully!")
        self.next_question()
    
    def save_to_file(self):
        """Save evaluations to JSON file"""
        try:
            eval_data = {
                'metadata': {
                    'total_questions': self.total_questions,
                    'completed_questions': len(self.completed_questions),
                    'completion_percentage': round((len(self.completed_questions) / self.total_questions) * 100, 1),
                    'last_updated': datetime.now().isoformat(),
                    'target_models': self.target_models,
                    'analysis_criteria': {
                        'error_types': self.error_types,
                        'crosslingual_questions': self.crosslingual_questions
                    }
                },
                'evaluations': self.evaluations
            }
            
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(eval_data, f, indent=2, ensure_ascii=False)
            
            # Also save progress
            progress_data = {
                'current_index': self.current_index,
                'completed_questions': list(self.completed_questions),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")
    
    def load_progress(self):
        """Load previous progress"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                self.current_index = progress_data.get('current_index', 0)
                self.completed_questions = set(progress_data.get('completed_questions', []))
            
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    eval_data = json.load(f)
                
                self.evaluations = eval_data.get('evaluations', {})
                
        except Exception as e:
            print(f"Warning: Could not load progress: {str(e)}")
    
    def jump_to_question(self):
        """Jump to specific question"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Jump to Question")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Enter question number (1-{self.total_questions}):").pack(pady=10)
        
        entry = ttk.Entry(dialog, width=10)
        entry.pack(pady=5)
        entry.focus()
        
        def go_to_question():
            try:
                question_num = int(entry.get())
                if 1 <= question_num <= self.total_questions:
                    self.current_index = question_num - 1
                    self.load_current_question()
                    dialog.destroy()
                else:
                    messagebox.showerror("Invalid Input", f"Please enter a number between 1 and {self.total_questions}")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Go", command=go_to_question).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        entry.bind('<Return>', lambda e: go_to_question())
    
    def previous_question(self):
        """Move to previous question"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_question()
        else:
            messagebox.showinfo("First Question", "You are at the first question!")
    
    def next_question(self):
        """Move to next question"""
        if self.current_index < self.total_questions - 1:
            self.current_index += 1
            self.load_current_question()
        else:
            messagebox.showinfo("Complete", "You have reached the last question!")
    
    def export_results(self):
        """Export results to CSV"""
        if not self.evaluations:
            messagebox.showwarning("Warning", "No evaluations to export")
            return
        
        try:
            export_path = filedialog.asksaveasfilename(
                title="Export Analysis Results",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if not export_path:
                return
            
            # Convert evaluations to DataFrame
            eval_list = []
            for unique_id, eval_data in self.evaluations.items():
                row = {
                    'unique_question_id': eval_data['unique_question_id'],
                    'model_name': eval_data['model_name'],
                    'subject': eval_data['subject'],
                    'correctness_category': eval_data['correctness_category'],
                    'evaluation_timestamp': eval_data['evaluation_timestamp']
                }
                
                # Add error scores
                for error_id in self.error_types.keys():
                    row[error_id] = eval_data.get(error_id, 0)
                
                # Add cross-lingual scores
                for question_id in self.crosslingual_questions.keys():
                    row[question_id] = eval_data.get(question_id, False)
                
                row['notes'] = eval_data.get('notes', '')
                eval_list.append(row)
            
            df = pd.DataFrame(eval_list)
            df.to_csv(export_path, index=False, encoding='utf-8')
            
            messagebox.showinfo("Success", f"Results exported to {export_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {str(e)}")
    
    def run(self):
        """Start the GUI application"""
        if self.total_questions == 0:
            messagebox.showerror("No Data", "No questions found for analysis. Please check the data file.")
            return
        
        # Handle window closing
        def on_closing():
            if messagebox.askokcancel("Quit", "Save progress and quit?"):
                self.save_to_file()
                self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()

def main():
    """Main function to run the Cross-Lingual Analysis GUI"""
    try:
        app = CrossLingualAnalysisGUI()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()