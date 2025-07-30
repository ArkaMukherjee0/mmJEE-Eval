# JEE Advanced answer collection tool
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from pathlib import Path
import time
from PIL import Image, ImageTk
import shutil
from collections import Counter, defaultdict

class JEEAnswerCollector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JEE Advanced Answer Collection Utility")
        self.root.geometry("1600x900")
        
        # Data structures
        self.question_data = []
        self.current_question_index = 0
        self.sources = [
            "FIITJEE", "Aakash", "Allen Kota", 
            "Resonance", "Motion Education", "Official Key"
        ]
        self.current_answers = {}
        self.final_dataset = []
        self.questions_by_type = {
            'MCQ-Single': [],
            'MCQ-Multiple': [],
            'Numerical': [],
            'Matching': []
        }
        
        # UI state
        self.current_image = None
        self.review_mode = False
        
        self.setup_gui()
        
    def setup_gui(self):
        # Create notebook for different modes
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Setup different tabs
        self.setup_load_tab(notebook)
        self.setup_answer_tab(notebook)
        self.setup_review_tab(notebook)
        self.setup_dataset_tab(notebook)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Load question images to begin answer collection")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(fill='x', side='bottom')
    
    def setup_load_tab(self, notebook):
        load_frame = ttk.Frame(notebook)
        notebook.add(load_frame, text="Load Questions")
        
        # Title
        title_label = ttk.Label(load_frame, text="JEE Advanced Answer Collection", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=20)
        
        # Instructions
        instructions = ttk.LabelFrame(load_frame, text="Instructions")
        instructions.pack(fill='x', padx=20, pady=10)
        
        instruction_text = """
1. Select a directory containing exported question images
2. Images should be named with pattern: YEAR_PAPER_LANG_SUBJECT_QUESTIONID_TYPE_pageN.png
3. The utility will automatically organize questions by subject and type in this order:
   Mathematics: MCQ-Single → MCQ-Multiple → Numerical → Matching
   Physics: MCQ-Single → MCQ-Multiple → Numerical → Matching  
   Chemistry: MCQ-Single → MCQ-Multiple → Numerical → Matching
4. For each question, collect answers from multiple sources
5. System will perform majority voting and flag discrepancies
        """
        ttk.Label(instructions, text=instruction_text, justify='left').pack(padx=10, pady=10)
        
        # Directory selection
        dir_frame = ttk.LabelFrame(load_frame, text="Question Images Directory")
        dir_frame.pack(fill='x', padx=20, pady=10)
        
        dir_inner = ttk.Frame(dir_frame)
        dir_inner.pack(fill='x', padx=10, pady=10)
        
        self.questions_dir_var = tk.StringVar()
        ttk.Entry(dir_inner, textvariable=self.questions_dir_var, width=80).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_inner, text="Browse", command=self.select_questions_dir).pack(side='right', padx=(5, 0))
        
        # Load button
        ttk.Button(dir_frame, text="Load Questions", command=self.load_questions).pack(pady=10)
        
        # Progress display
        self.load_progress_frame = ttk.LabelFrame(load_frame, text="Loading Progress")
        self.load_progress_frame.pack(fill='x', padx=20, pady=10)
        
        self.load_progress_text = tk.Text(self.load_progress_frame, height=8, width=80)
        load_scrollbar = ttk.Scrollbar(self.load_progress_frame, orient='vertical', command=self.load_progress_text.yview)
        self.load_progress_text.configure(yscrollcommand=load_scrollbar.set)
        
        load_scrollbar.pack(side='right', fill='y')
        self.load_progress_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
    
    def setup_answer_tab(self, notebook):
        answer_frame = ttk.Frame(notebook)
        notebook.add(answer_frame, text="Collect Answers")
        
        # Top controls
        control_frame = ttk.Frame(answer_frame)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(side='left')
        
        ttk.Button(nav_frame, text="◀ Previous", command=self.prev_question).pack(side='left', padx=5)
        self.question_label = ttk.Label(nav_frame, text="Question 0/0", font=('Arial', 12, 'bold'))
        self.question_label.pack(side='left', padx=10)
        ttk.Button(nav_frame, text="Next ▶", command=self.next_question).pack(side='left', padx=5)
        
        # Question type filter
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(side='left', padx=20)
        
        ttk.Label(filter_frame, text="Filter by type:").pack(side='left')
        self.type_filter_var = tk.StringVar()
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_filter_var, width=15,
                                 values=['All', 'MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching'])
        type_combo.pack(side='left', padx=5)
        type_combo.set('All')
        type_combo.bind('<<ComboboxSelected>>', self.filter_questions)
        
        # Actions
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(side='right')
        
        ttk.Button(action_frame, text="Save Progress", command=self.save_answer_progress).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Auto-Fill Demo", command=self.auto_fill_demo).pack(side='left', padx=5)
        
        # Main content area
        main_frame = ttk.Frame(answer_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel - Question image
        image_frame = ttk.LabelFrame(main_frame, text="Question Image")
        image_frame.pack(side='left', fill='both', expand=True)
        
        # Image display with scrollbars
        image_inner = ttk.Frame(image_frame)
        image_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.image_canvas = tk.Canvas(image_inner, bg='white')
        v_scroll = ttk.Scrollbar(image_inner, orient='vertical', command=self.image_canvas.yview)
        h_scroll = ttk.Scrollbar(image_inner, orient='horizontal', command=self.image_canvas.xview)
        self.image_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        self.image_canvas.pack(side='left', fill='both', expand=True)
        
        # Right panel - Answer collection
        answer_panel = ttk.Frame(main_frame, width=500)
        answer_panel.pack(side='right', fill='y', padx=(10, 0))
        answer_panel.pack_propagate(False)
        
        # Question info
        info_frame = ttk.LabelFrame(answer_panel, text="Question Information")
        info_frame.pack(fill='x', pady=5)
        
        self.question_info_text = tk.Text(info_frame, height=4, wrap='word')
        self.question_info_text.pack(fill='x', padx=10, pady=10)
        
        # Answer collection form
        collection_frame = ttk.LabelFrame(answer_panel, text="Answer Collection")
        collection_frame.pack(fill='both', expand=True, pady=5)
        
        # Sources table
        table_frame = ttk.Frame(collection_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Headers
        headers_frame = ttk.Frame(table_frame)
        headers_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(headers_frame, text="Source", width=20, font=('Arial', 10, 'bold')).pack(side='left')
        ttk.Label(headers_frame, text="Answer", width=30, font=('Arial', 10, 'bold')).pack(side='left', padx=(20, 0))
        
        # Scrollable frame for source entries
        canvas_frame = ttk.Frame(table_frame)
        canvas_frame.pack(fill='both', expand=True)
        
        self.sources_canvas = tk.Canvas(canvas_frame, height=300)
        sources_scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.sources_canvas.yview)
        self.sources_frame = ttk.Frame(self.sources_canvas)
        
        self.sources_canvas.configure(yscrollcommand=sources_scrollbar.set)
        sources_scrollbar.pack(side='right', fill='y')
        self.sources_canvas.pack(side='left', fill='both', expand=True)
        
        self.sources_canvas.create_window((0, 0), window=self.sources_frame, anchor='nw')
        self.sources_frame.bind('<Configure>', self.update_sources_scroll)
        
        # Initialize source entries
        self.source_entries = []
        self.create_source_entries()
        
        # Add/Remove source buttons
        btn_frame = ttk.Frame(collection_frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Add Source", command=self.add_source_entry).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Last", command=self.remove_source_entry).pack(side='left', padx=5)
        
        # Answer analysis
        analysis_frame = ttk.LabelFrame(answer_panel, text="Answer Analysis")
        analysis_frame.pack(fill='x', pady=5)
        
        self.analysis_text = tk.Text(analysis_frame, height=6, wrap='word')
        self.analysis_text.pack(fill='x', padx=10, pady=10)
        
        # Action buttons
        final_btn_frame = ttk.Frame(answer_panel)
        final_btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(final_btn_frame, text="Analyze Answers", command=self.analyze_answers).pack(side='left', padx=5)
        ttk.Button(final_btn_frame, text="Accept & Next", command=self.accept_and_next).pack(side='left', padx=5)
        ttk.Button(final_btn_frame, text="Flag for Review", command=self.flag_for_review).pack(side='left', padx=5)
    
    def setup_review_tab(self, notebook):
        review_frame = ttk.Frame(notebook)
        notebook.add(review_frame, text="Review Flagged")
        
        ttk.Label(review_frame, text="Review Questions Flagged for Manual Verification", 
                 font=('Arial', 14, 'bold')).pack(pady=20)
        
        # Flagged questions list
        list_frame = ttk.LabelFrame(review_frame, text="Flagged Questions")
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.flagged_listbox = tk.Listbox(list_frame, height=15)
        flagged_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.flagged_listbox.yview)
        self.flagged_listbox.configure(yscrollcommand=flagged_scrollbar.set)
        
        flagged_scrollbar.pack(side='right', fill='y')
        self.flagged_listbox.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        self.flagged_listbox.bind('<<ListboxSelect>>', self.load_flagged_question)
        
        # Review controls
        review_controls = ttk.Frame(review_frame)
        review_controls.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(review_controls, text="Accept Majority Vote", command=self.accept_majority).pack(side='left', padx=5)
        ttk.Button(review_controls, text="Set Custom Answer", command=self.set_custom_answer).pack(side='left', padx=5)
        ttk.Button(review_controls, text="Remove from Dataset", command=self.remove_from_dataset).pack(side='left', padx=5)
    
    def setup_dataset_tab(self, notebook):
        dataset_frame = ttk.Frame(notebook)
        notebook.add(dataset_frame, text="Final Dataset")
        
        ttk.Label(dataset_frame, text="Generate Final Dataset", 
                 font=('Arial', 14, 'bold')).pack(pady=20)
        
        # Dataset statistics
        stats_frame = ttk.LabelFrame(dataset_frame, text="Dataset Statistics")
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=8, wrap='word')
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Export options
        export_frame = ttk.LabelFrame(dataset_frame, text="Export Options")
        export_frame.pack(fill='x', padx=20, pady=10)
        
        export_inner = ttk.Frame(export_frame)
        export_inner.pack(fill='x', padx=10, pady=10)
        
        # Output directory
        ttk.Label(export_inner, text="Output Directory:").pack(anchor='w')
        dir_frame = ttk.Frame(export_inner)
        dir_frame.pack(fill='x', pady=5)
        
        self.output_dir_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=60).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.select_output_dir).pack(side='right', padx=(5, 0))
        
        # Export formats
        ttk.Label(export_inner, text="Export Formats:").pack(anchor='w', pady=(10, 0))
        format_frame = ttk.Frame(export_inner)
        format_frame.pack(fill='x')
        
        self.export_json_var = tk.BooleanVar(value=True)
        self.export_csv_var = tk.BooleanVar(value=True)
        self.copy_images_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(format_frame, text="JSON Dataset", variable=self.export_json_var).pack(side='left', padx=10)
        ttk.Checkbutton(format_frame, text="CSV Dataset", variable=self.export_csv_var).pack(side='left', padx=10)
        ttk.Checkbutton(format_frame, text="Copy Images", variable=self.copy_images_var).pack(side='left', padx=10)
        
        # Generate button
        ttk.Button(export_inner, text="Generate Final Dataset", 
                  command=self.generate_final_dataset).pack(pady=20)
        
        # Progress display
        self.export_progress = ttk.Progressbar(export_inner, mode='determinate')
        self.export_progress.pack(fill='x', pady=10)
    
    def select_questions_dir(self):
        directory = filedialog.askdirectory(title="Select directory containing question images")
        if directory:
            self.questions_dir_var.set(directory)
    
    def load_questions(self):
        questions_dir = Path(self.questions_dir_var.get())
        if not questions_dir.exists():
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        self.load_progress_text.delete(1.0, tk.END)
        self.load_progress_text.insert(tk.END, "Loading questions...\n")
        self.root.update()
        
        # Find all PNG files
        png_files = list(questions_dir.rglob("*.png"))
        
        if not png_files:
            messagebox.showerror("Error", "No PNG files found in the selected directory")
            return
        
        self.load_progress_text.insert(tk.END, f"Found {len(png_files)} image files\n")
        self.root.update()
        
        # Parse and organize questions by subject and type
        questions_by_subject_type = defaultdict(lambda: defaultdict(list))
        
        for png_file in png_files:
            try:
                # Parse filename: YEAR_PAPER_LANG_SUBJECT_QUESTIONTYPE_QUESTIONNUM_TYPE_pageN.png
                name_parts = png_file.stem.split('_')
                
                if len(name_parts) >= 6:
                    year = name_parts[0]
                    paper = name_parts[1]
                    language = name_parts[2]
                    subject = name_parts[3]
                    question_id = name_parts[4]  # e.g., "MCQ-Single"
                    question_number_part = name_parts[5]  # e.g., "q1"
                    question_type = name_parts[6] if len(name_parts) > 6 else question_id  # e.g., "MCQ-Single"
                    
                    # Extract question number from question_number_part (e.g., "q1" -> 1)
                    try:
                        if question_number_part.startswith('q'):
                            question_number = int(question_number_part[1:])
                        else:
                            question_number = 0
                    except (ValueError, IndexError):
                        question_number = 0
                    
                    # Determine the actual question type from the question_id or filename pattern
                    if 'MCQ-Single' in png_file.name:
                        question_type = 'MCQ-Single'
                    elif 'MCQ-Multiple' in png_file.name:
                        question_type = 'MCQ-Multiple'
                    elif 'Numerical' in png_file.name:
                        question_type = 'Numerical'
                    elif 'Matching' in png_file.name:
                        question_type = 'Matching'
                    else:
                        # Fallback to parsing from question_id
                        question_type = question_id
                    
                    question_info = {
                        'file_path': str(png_file),
                        'filename': png_file.name,
                        'year': year,
                        'paper': paper,
                        'language': language,
                        'subject': subject,
                        'question_id': f"{question_id}_{question_number_part}",
                        'question_type': question_type,
                        'question_number': question_number,
                        'answers': {},
                        'final_answer': None,
                        'confidence': None,
                        'flagged': False,
                        'review_notes': ''
                    }
                    
                    questions_by_subject_type[subject][question_type].append(question_info)
                
            except Exception as e:
                self.load_progress_text.insert(tk.END, f"Error parsing {png_file.name}: {str(e)}\n")
                continue
        
        # Define ordering: Subject first, then question type
        subject_order = ['Mathematics', 'Physics', 'Chemistry']
        question_type_order = ['MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching']
        
        # Organize in proper order: Subject -> Question Type -> Question Number
        self.question_data = []
        self.questions_by_type = defaultdict(list)
        
        self.load_progress_text.insert(tk.END, f"\nOrganizing questions by subject and type:\n")
        
        for subject in subject_order:
            if subject in questions_by_subject_type:
                self.load_progress_text.insert(tk.END, f"\n{subject}:\n")
                
                for question_type in question_type_order:
                    if question_type in questions_by_subject_type[subject]:
                        # Sort questions by question number
                        type_questions = sorted(
                            questions_by_subject_type[subject][question_type],
                            key=lambda x: x['question_number']
                        )
                        
                        self.question_data.extend(type_questions)
                        self.questions_by_type[question_type].extend(type_questions)
                        
                        question_range = f"q1 to q{max(q['question_number'] for q in type_questions)}" if type_questions else "none"
                        self.load_progress_text.insert(tk.END, 
                            f"  {question_type}: {len(type_questions)} questions ({question_range})\n")
        
        # Add any subjects not in the standard order
        for subject in questions_by_subject_type:
            if subject not in subject_order:
                self.load_progress_text.insert(tk.END, f"\n{subject} (Other):\n")
                
                for question_type in question_type_order:
                    if question_type in questions_by_subject_type[subject]:
                        type_questions = sorted(
                            questions_by_subject_type[subject][question_type],
                            key=lambda x: x['question_number']
                        )
                        
                        self.question_data.extend(type_questions)
                        self.questions_by_type[question_type].extend(type_questions)
                        
                        self.load_progress_text.insert(tk.END, 
                            f"  {question_type}: {len(type_questions)} questions\n")
        
        # Summary
        self.load_progress_text.insert(tk.END, f"\nTotal questions loaded: {len(self.question_data)}\n")
        self.load_progress_text.insert(tk.END, "Question order:\n")
        self.load_progress_text.insert(tk.END, "Mathematics: MCQ-Single → MCQ-Multiple → Numerical → Matching\n")
        self.load_progress_text.insert(tk.END, "Physics: MCQ-Single → MCQ-Multiple → Numerical → Matching\n")
        self.load_progress_text.insert(tk.END, "Chemistry: MCQ-Single → MCQ-Multiple → Numerical → Matching\n")
        self.load_progress_text.insert(tk.END, "Ready to begin answer collection!\n")
        
        # Display summary by type
        self.load_progress_text.insert(tk.END, f"\nSummary by question type:\n")
        for question_type in question_type_order:
            count = len(self.questions_by_type[question_type])
            self.load_progress_text.insert(tk.END, f"  {question_type}: {count} questions total\n")
        
        if self.question_data:
            self.current_question_index = 0
            self.load_current_question()
            self.status_var.set(f"Loaded {len(self.question_data)} questions in subject→type order. Ready for answer collection.")
        
        self.root.update()
    
    def create_source_entries(self):
        # Clear existing entries
        for widget in self.sources_frame.winfo_children():
            widget.destroy()
        self.source_entries = []
        
        # Create initial entries for known sources
        for i, source in enumerate(self.sources):
            self.add_source_entry_widget(source)
        
        # Add a few blank entries
        for i in range(2):
            self.add_source_entry_widget("")
    
    def add_source_entry_widget(self, default_source=""):
        row_frame = ttk.Frame(self.sources_frame)
        row_frame.pack(fill='x', pady=2)
        
        source_var = tk.StringVar(value=default_source)
        answer_var = tk.StringVar()
        
        source_combo = ttk.Combobox(row_frame, textvariable=source_var, width=18,
                                   values=self.sources + ["Custom"])
        source_combo.pack(side='left', padx=(0, 10))
        
        answer_entry = ttk.Entry(row_frame, textvariable=answer_var, width=30)
        answer_entry.pack(side='left')
        
        self.source_entries.append((source_var, answer_var, row_frame))
        
        # Update scroll region
        self.sources_frame.update_idletasks()
        self.sources_canvas.configure(scrollregion=self.sources_canvas.bbox("all"))
    
    def add_source_entry(self):
        self.add_source_entry_widget()
    
    def remove_source_entry(self):
        if len(self.source_entries) > 1:
            source_var, answer_var, row_frame = self.source_entries.pop()
            row_frame.destroy()
            
            # Update scroll region
            self.sources_frame.update_idletasks()
            self.sources_canvas.configure(scrollregion=self.sources_canvas.bbox("all"))
    
    def update_sources_scroll(self, event):
        self.sources_canvas.configure(scrollregion=self.sources_canvas.bbox("all"))
    
    def load_current_question(self):
        if not self.question_data or self.current_question_index >= len(self.question_data):
            return
        
        question = self.question_data[self.current_question_index]
        
        # Update question label
        self.question_label.config(text=f"Question {self.current_question_index + 1}/{len(self.question_data)}")
        
        # Load image
        try:
            image_path = question['file_path']
            pil_image = Image.open(image_path)
            
            # Scale image to fit canvas
            canvas_width = 800
            canvas_height = 600
            
            img_width, img_height = pil_image.size
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            scale = min(scale_x, scale_y, 1.0)  # Don't upscale
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.current_image = ImageTk.PhotoImage(pil_image)
            
            # Display image
            self.image_canvas.delete("all")
            self.image_canvas.create_image(0, 0, anchor='nw', image=self.current_image)
            self.image_canvas.configure(scrollregion=(0, 0, new_width, new_height))
            
        except Exception as e:
            self.image_canvas.delete("all")
            self.image_canvas.create_text(400, 300, text=f"Error loading image:\n{str(e)}", 
                                        font=('Arial', 12), anchor='center')
        
        # Update question info
        current_subject = question['subject']
        current_type = question['question_type']
        
        # Count questions of same subject and type before current question
        same_type_count = 0
        total_same_type = 0
        for i, q in enumerate(self.question_data):
            if q['subject'] == current_subject and q['question_type'] == current_type:
                total_same_type += 1
                if i <= self.current_question_index:
                    same_type_count += 1
        
        info_text = f"""Question ID: {question['question_id']}
Type: {question['question_type']}
Subject: {question['subject']}
Progress: Question {same_type_count}/{total_same_type} in {current_subject} {current_type}
Paper: {question['year']} Paper {question['paper']} ({question['language']})
Question Number: {question.get('question_number', 'Unknown')}
File: {question['filename']}"""
        
        self.question_info_text.delete(1.0, tk.END)
        self.question_info_text.insert(tk.END, info_text)
        
        # Load existing answers
        self.load_existing_answers(question)
        
        # Clear analysis
        self.analysis_text.delete(1.0, tk.END)
    
    def get_section_number(self, question_type):
        """Get section number for question type"""
        section_map = {
            'MCQ-Single': 1,
            'MCQ-Multiple': 2, 
            'Numerical': 3,
            'Matching': 4
        }
        return section_map.get(question_type, 'Unknown')
    
    def load_existing_answers(self, question):
        # Clear current entries
        for source_var, answer_var, _ in self.source_entries:
            answer_var.set("")
        
        # Load saved answers
        for source, answer in question.get('answers', {}).items():
            # Find matching source entry or create new one
            found = False
            for source_var, answer_var, _ in self.source_entries:
                if source_var.get() == source:
                    answer_var.set(answer)
                    found = True
                    break
            
            if not found:
                # Add new entry for this source
                self.add_source_entry_widget(source)
                self.source_entries[-1][1].set(answer)
    
    def prev_question(self):
        if self.current_question_index > 0:
            self.save_current_answers()
            self.current_question_index -= 1
            self.load_current_question()
    
    def next_question(self):
        if self.current_question_index < len(self.question_data) - 1:
            self.save_current_answers()
            self.current_question_index += 1
            self.load_current_question()
    
    def save_current_answers(self):
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        answers = {}
        
        for source_var, answer_var, _ in self.source_entries:
            source = source_var.get().strip()
            answer = answer_var.get().strip()
            
            if source and answer:
                answers[source] = answer
        
        question['answers'] = answers
    
    def analyze_answers(self):
        self.save_current_answers()
        
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        answers = question.get('answers', {})
        
        if not answers:
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(tk.END, "No answers provided yet.")
            return
        
        # Count answer frequencies
        answer_counts = Counter(answers.values())
        total_sources = len(answers)
        
        analysis = f"Answer Analysis for {question['question_id']}:\n"
        analysis += f"Total sources: {total_sources}\n\n"
        
        analysis += "Answer frequency:\n"
        for answer, count in answer_counts.most_common():
            percentage = (count / total_sources) * 100
            analysis += f"  '{answer}': {count} sources ({percentage:.1f}%)\n"
        
        # Determine confidence and recommendation
        if len(answer_counts) == 1:
            # All sources agree
            final_answer = list(answer_counts.keys())[0]
            confidence = "HIGH"
            analysis += f"\n✓ CONSENSUS: All sources agree on '{final_answer}'\n"
            analysis += "Recommendation: Accept this answer\n"
            
            question['final_answer'] = final_answer
            question['confidence'] = confidence
            question['flagged'] = False
            
        elif answer_counts.most_common(1)[0][1] >= total_sources * 0.6:
            # Majority agreement (60%+)
            final_answer = answer_counts.most_common(1)[0][0]
            majority_count = answer_counts.most_common(1)[0][1]
            confidence = "MEDIUM"
            
            analysis += f"\n⚠ MAJORITY: '{final_answer}' ({majority_count}/{total_sources} sources)\n"
            analysis += "Recommendation: Accept majority vote or flag for review\n"
            
            question['final_answer'] = final_answer
            question['confidence'] = confidence
            question['flagged'] = True  # Flag for review by default
            
        else:
            # No clear majority
            confidence = "LOW"
            analysis += f"\n❌ NO CONSENSUS: No clear majority found\n"
            analysis += "Recommendation: Flag for manual review\n"
            
            question['final_answer'] = None
            question['confidence'] = confidence
            question['flagged'] = True
        
        # Show source details
        analysis += f"\nSource details:\n"
        for source, answer in answers.items():
            analysis += f"  {source}: '{answer}'\n"
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, analysis)
    
    def accept_and_next(self):
        self.save_current_answers()
        self.analyze_answers()
        
        if self.question_data:
            question = self.question_data[self.current_question_index]
            if question.get('final_answer'):
                question['flagged'] = False
                self.status_var.set(f"Accepted answer for {question['question_id']}")
                self.next_question()
            else:
                messagebox.showwarning("Warning", "Please analyze answers first or no consensus found")
    
    def flag_for_review(self):
        self.save_current_answers()
        
        if self.question_data:
            question = self.question_data[self.current_question_index]
            question['flagged'] = True
            
            # Get review notes
            notes = tk.simpledialog.askstring(
                "Review Notes",
                f"Add notes for {question['question_id']}:",
                initialvalue=question.get('review_notes', '')
            )
            
            if notes is not None:
                question['review_notes'] = notes
            
            self.status_var.set(f"Flagged {question['question_id']} for review")
            self.update_flagged_list()
            self.next_question()
    
    def auto_fill_demo(self):
        """Auto-fill with demo data for testing"""
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        question_type = question.get('question_type', 'MCQ-Single')
        
        # Demo answers based on question type
        demo_answers = {
            'MCQ-Single': ['A', 'A', 'B', 'A'],
            'MCQ-Multiple': ['A,B', 'A,B,C', 'A,B', 'A,B'],
            'Numerical': ['2.5', '2.50', '2.5', '2.5'],
            'Matching': ['A-P,B-Q,C-R', 'A-P,B-Q,C-R', 'A-P,B-Q,C-S', 'A-P,B-Q,C-R']
        }
        
        answers = demo_answers.get(question_type, ['A', 'A', 'B', 'A'])
        sources = ['FIITJEE', 'Aakash', 'Allen Kota', 'Resonance']
        
        for i, (source_var, answer_var, _) in enumerate(self.source_entries[:4]):
            if i < len(sources):
                source_var.set(sources[i])
                answer_var.set(answers[i])
    
    def filter_questions(self, event=None):
        filter_type = self.type_filter_var.get()
        
        if filter_type == 'All':
            # Show all questions in original order
            return
        
        # Filter and jump to first question of selected type
        for i, question in enumerate(self.question_data):
            if question['question_type'] == filter_type:
                self.save_current_answers()
                self.current_question_index = i
                self.load_current_question()
                
                # Show type info
                type_questions = [q for q in self.question_data if q['question_type'] == filter_type]
                subjects_with_type = list(set(q['subject'] for q in type_questions))
                self.status_var.set(f"Jumped to {filter_type} - {len(type_questions)} questions across {subjects_with_type}")
                break
    
    def save_answer_progress(self):
        if not self.question_data:
            messagebox.showinfo("Info", "No data to save")
            return
        
        self.save_current_answers()
        
        try:
            # Save to JSON file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"answer_collection_progress_{timestamp}.json"
            
            # Prepare data for saving
            save_data = {
                'timestamp': timestamp,
                'total_questions': len(self.question_data),
                'completed_questions': len([q for q in self.question_data if q.get('final_answer')]),
                'flagged_questions': len([q for q in self.question_data if q.get('flagged')]),
                'questions': self.question_data
            }
            
            filepath = filedialog.asksaveasfilename(
                title="Save progress",
                initialfile=filename,
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            
            if filepath:
                with open(filepath, 'w') as f:
                    json.dump(save_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Progress saved to {filepath}")
                self.status_var.set(f"Progress saved: {save_data['completed_questions']}/{save_data['total_questions']} completed")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save progress: {str(e)}")
    
    def update_flagged_list(self):
        self.flagged_listbox.delete(0, tk.END)
        
        for i, question in enumerate(self.question_data):
            if question.get('flagged'):
                display_text = f"{question['question_id']} - {question['question_type']} - {question['subject']}"
                if question.get('confidence'):
                    display_text += f" ({question['confidence']} confidence)"
                
                self.flagged_listbox.insert(tk.END, display_text)
    
    def load_flagged_question(self, event):
        selection = self.flagged_listbox.curselection()
        if selection:
            # Find the flagged question in main data
            flagged_questions = [q for q in self.question_data if q.get('flagged')]
            if selection[0] < len(flagged_questions):
                flagged_question = flagged_questions[selection[0]]
                
                # Find index in main question list
                for i, question in enumerate(self.question_data):
                    if question == flagged_question:
                        self.current_question_index = i
                        self.load_current_question()
                        break
    
    def accept_majority(self):
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        if question.get('final_answer'):
            question['flagged'] = False
            messagebox.showinfo("Success", f"Accepted majority vote for {question['question_id']}")
            self.update_flagged_list()
    
    def set_custom_answer(self):
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        
        # Dialog for custom answer
        dialog = tk.Toplevel(self.root)
        dialog.title("Set Custom Answer")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Set custom answer for {question['question_id']}", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Show current sources and answers
        sources_frame = ttk.LabelFrame(dialog, text="Current Sources")
        sources_frame.pack(fill='x', padx=20, pady=10)
        
        sources_text = tk.Text(sources_frame, height=6, wrap='word')
        sources_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Display current answers
        answers = question.get('answers', {})
        for source, answer in answers.items():
            sources_text.insert(tk.END, f"{source}: {answer}\n")
        
        # Custom answer entry
        ttk.Label(dialog, text="Custom Answer:").pack(anchor='w', padx=20)
        custom_answer_var = tk.StringVar(value=question.get('final_answer', ''))
        answer_entry = ttk.Entry(dialog, textvariable=custom_answer_var, width=40)
        answer_entry.pack(padx=20, pady=5)
        
        # Notes
        ttk.Label(dialog, text="Notes:").pack(anchor='w', padx=20, pady=(10, 0))
        notes_text = tk.Text(dialog, height=3, width=40)
        notes_text.pack(padx=20, pady=5)
        notes_text.insert(tk.END, question.get('review_notes', ''))
        
        def save_custom():
            custom_answer = custom_answer_var.get().strip()
            if custom_answer:
                question['final_answer'] = custom_answer
                question['confidence'] = 'MANUAL'
                question['flagged'] = False
                question['review_notes'] = notes_text.get(1.0, tk.END).strip()
                
                dialog.destroy()
                messagebox.showinfo("Success", f"Set custom answer for {question['question_id']}")
                self.update_flagged_list()
            else:
                messagebox.showwarning("Warning", "Please enter a custom answer")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Save", command=save_custom).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=10)
    
    def remove_from_dataset(self):
        if not self.question_data:
            return
        
        question = self.question_data[self.current_question_index]
        
        confirm = messagebox.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove {question['question_id']} from the dataset?\n\n"
            "This question will not be included in the final dataset."
        )
        
        if confirm:
            self.question_data.remove(question)
            messagebox.showinfo("Success", f"Removed {question['question_id']} from dataset")
            self.update_flagged_list()
            
            # Navigate to next question
            if self.current_question_index >= len(self.question_data):
                self.current_question_index = len(self.question_data) - 1
            
            if self.question_data:
                self.load_current_question()
    
    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Select output directory for final dataset")
        if directory:
            self.output_dir_var.set(directory)
    
    def generate_final_dataset(self):
        if not self.question_data:
            messagebox.showerror("Error", "No question data available")
            return
        
        output_dir = Path(self.output_dir_var.get())
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Filter questions with final answers
            completed_questions = [q for q in self.question_data if q.get('final_answer')]
            flagged_questions = [q for q in self.question_data if q.get('flagged')]
            
            self.export_progress['maximum'] = len(completed_questions)
            self.export_progress['value'] = 0
            
            dataset = []
            images_dir = output_dir / "images"
            
            if self.copy_images_var.get():
                images_dir.mkdir(exist_ok=True)
            
            for i, question in enumerate(completed_questions):
                # Prepare dataset entry
                entry = {
                    'question_id': question['question_id'],
                    'image_filename': question['filename'],
                    'image_path': str(Path("images") / question['filename']) if self.copy_images_var.get() else question['file_path'],
                    'subject': question['subject'],
                    'question_type': question['question_type'],
                    'year': question['year'],
                    'paper': question['paper'],
                    'language': question['language'],
                    'answer': question['final_answer'],
                    'confidence': question['confidence'],
                    'sources': question.get('answers', {}),
                    'review_notes': question.get('review_notes', '')
                }
                
                dataset.append(entry)
                
                # Copy image if requested
                if self.copy_images_var.get():
                    src_path = Path(question['file_path'])
                    dst_path = images_dir / question['filename']
                    if src_path.exists() and not dst_path.exists():
                        shutil.copy2(src_path, dst_path)
                
                self.export_progress['value'] = i + 1
                self.root.update()
            
            # Export JSON
            if self.export_json_var.get():
                json_file = output_dir / "jee_advanced_dataset.json"
                with open(json_file, 'w') as f:
                    json.dump({
                        'metadata': {
                            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                            'total_questions': len(dataset),
                            'flagged_questions': len(flagged_questions),
                            'subjects': list(set(q['subject'] for q in dataset)),
                            'question_types': list(set(q['question_type'] for q in dataset)),
                            'years': list(set(q['year'] for q in dataset))
                        },
                        'questions': dataset
                    }, f, indent=2)
            
            # Export CSV
            if self.export_csv_var.get():
                import csv
                csv_file = output_dir / "jee_advanced_dataset.csv"
                
                if dataset:
                    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
                        writer.writeheader()
                        writer.writerows(dataset)
            
            # Generate statistics
            self.generate_dataset_statistics(dataset, output_dir)
            
            # Generate flagged questions report
            if flagged_questions:
                flagged_file = output_dir / "flagged_questions.json"
                with open(flagged_file, 'w') as f:
                    json.dump(flagged_questions, f, indent=2)
            
            messagebox.showinfo("Success", 
                              f"Dataset generated successfully!\n\n"
                              f"Location: {output_dir}\n"
                              f"Completed questions: {len(dataset)}\n"
                              f"Flagged questions: {len(flagged_questions)}\n"
                              f"Files generated: JSON, CSV, statistics")
            
            self.status_var.set(f"Dataset generated: {len(dataset)} questions")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate dataset: {str(e)}")
    
    def generate_dataset_statistics(self, dataset, output_dir):
        # Calculate statistics
        stats = {
            'total_questions': len(dataset),
            'by_subject': {},
            'by_type': {},
            'by_year': {},
            'by_confidence': {},
            'by_paper': {}
        }
        
        for question in dataset:
            # By subject
            subject = question['subject']
            stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
            
            # By type
            q_type = question['question_type']
            stats['by_type'][q_type] = stats['by_type'].get(q_type, 0) + 1
            
            # By year
            year = question['year']
            stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
            
            # By confidence
            confidence = question['confidence']
            stats['by_confidence'][confidence] = stats['by_confidence'].get(confidence, 0) + 1
            
            # By paper
            paper = f"{question['year']} Paper {question['paper']} ({question['language']})"
            stats['by_paper'][paper] = stats['by_paper'].get(paper, 0) + 1
        
        # Update statistics display
        stats_text = "JEE Advanced Dataset Statistics\n"
        stats_text += "=" * 40 + "\n\n"
        stats_text += f"Total Questions: {stats['total_questions']}\n\n"
        
        stats_text += "By Subject:\n"
        for subject, count in sorted(stats['by_subject'].items()):
            percentage = (count / stats['total_questions']) * 100
            stats_text += f"  {subject}: {count} ({percentage:.1f}%)\n"
        
        stats_text += "\nBy Question Type:\n"
        for q_type, count in sorted(stats['by_type'].items()):
            percentage = (count / stats['total_questions']) * 100
            stats_text += f"  {q_type}: {count} ({percentage:.1f}%)\n"
        
        stats_text += "\nBy Year:\n"
        for year, count in sorted(stats['by_year'].items()):
            percentage = (count / stats['total_questions']) * 100
            stats_text += f"  {year}: {count} ({percentage:.1f}%)\n"
        
        stats_text += "\nBy Confidence Level:\n"
        for confidence, count in sorted(stats['by_confidence'].items()):
            percentage = (count / stats['total_questions']) * 100
            stats_text += f"  {confidence}: {count} ({percentage:.1f}%)\n"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats_text)
        
        # Save statistics to file
        stats_file = output_dir / "dataset_statistics.txt"
        with open(stats_file, 'w') as f:
            f.write(stats_text)
        
        # Save detailed statistics as JSON
        detailed_stats_file = output_dir / "detailed_statistics.json"
        with open(detailed_stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def run(self):
        # Initial setup
        self.update_flagged_list()
        self.root.mainloop()

def main():
    """
    Main function to run the JEE Advanced Answer Collection Utility
    
    This utility helps collect and verify answers for JEE Advanced questions from multiple sources,
    performs majority voting, and generates final datasets.
    """
    try:
        app = JEEAnswerCollector()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

# Add missing import for simpledialog
import tkinter.simpledialog

if __name__ == "__main__":
    main()