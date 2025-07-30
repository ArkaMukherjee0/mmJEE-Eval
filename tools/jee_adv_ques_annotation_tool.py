# JEE Advanced question collection tool
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import json
import os
from pathlib import Path
import time
import requests
import re
import io
from urllib.parse import urlparse

class JEEPDFDownloader:
    """Handler for downloading JEE Advanced PDFs"""
    
    BASE_URL = "https://jeeadv.ac.in/past_qps/"
    DOCUMENTS_URL = "https://jeeadv.ac.in/documents/"
    YEARS = list(range(2019, 2025))  # 2019-2025
    PAPERS = [1, 2]
    LANGUAGES = ["English", "Hindi"]
    
    @classmethod
    def generate_urls(cls):
        """Generate all possible JEE PDF URLs"""
        urls = []
        
        # 2019-2024 papers
        for year in cls.YEARS:
            for paper in cls.PAPERS:
                for language in cls.LANGUAGES:
                    url = f"{cls.BASE_URL}{year}_{paper}_{language}.pdf"
                    urls.append({
                        'url': url,
                        'year': year,
                        'paper': paper,
                        'language': language,
                        'filename': f"{year}_{paper}_{language}.pdf"
                    })
        
        # 2025 papers (different URL structure)
        for paper in cls.PAPERS:
            for language in cls.LANGUAGES:
                lang_code = language.lower()
                url = f"{cls.DOCUMENTS_URL}p{paper}_{lang_code}.pdf"
                urls.append({
                    'url': url,
                    'year': 2025,
                    'paper': paper,
                    'language': language,
                    'filename': f"2025_{paper}_{language}.pdf"
                })
        
        return urls
    
    @classmethod
    def download_pdf(cls, url_info, download_dir):
        """Download a single PDF"""
        try:
            response = requests.get(url_info['url'], timeout=30)
            response.raise_for_status()
            
            filepath = Path(download_dir) / url_info['filename']
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filepath
        except Exception as e:
            raise Exception(f"Failed to download {url_info['filename']}: {str(e)}")

class PDFQuestionAnnotator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JEE Advanced PDF Question Annotator")
        self.root.geometry("1500x900")
        
        # State variables
        self.pdf_doc = None
        self.current_page = 0
        self.total_pages = 0
        self.current_image = None
        self.annotations = []
        self.temp_rect = None
        self.start_x = None
        self.start_y = None
        self.scale_factor = 1.0
        self.output_base_dir = None
        
        # Multi-rectangle support
        self.current_question_rectangles = []  # Store multiple rectangles for current question
        self.pending_question_data = None  # Store question data while collecting rectangles
        self.multi_rectangle_mode = False  # Track if we're in multi-rectangle mode
        self.last_export_data = None  # Store data for undo functionality
        
        # PDF metadata
        self.pdf_metadata = {
            'year': None,
            'paper': None,
            'language': None,
            'current_subject': None
        }
        
        # Store URL info separately
        self.pdf_url_info = {}
        
        # Question counters for auto-generation
        self.question_counters = {
            'MCQ-Single': 0,
            'MCQ-Multiple': 0,
            'Numerical': 0,
            'Matching': 0
        }
        
        # Progress tracking
        self.progress_data = {
            'subjects_completed': [],
            'current_subject_progress': {},
            'last_worked_page': 0,
            'total_questions_annotated': 0,
            'session_start_time': None
        }
        
        # Create GUI
        self.setup_gui()
        
    def setup_gui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Download tab
        self.setup_download_tab(notebook)
        
        # Annotation tab
        self.setup_annotation_tab(notebook)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Select Download tab to get JEE PDFs or load existing PDF")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(fill='x', side='bottom')
    
    def setup_download_tab(self, notebook):
        download_frame = ttk.Frame(notebook)
        notebook.add(download_frame, text="Download PDFs")
        
        # Title
        title_label = ttk.Label(download_frame, text="JEE Advanced PDF Downloader", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Download directory selection
        dir_frame = ttk.LabelFrame(download_frame, text="Download Directory")
        dir_frame.pack(fill='x', padx=20, pady=10)
        
        dir_inner = ttk.Frame(dir_frame)
        dir_inner.pack(fill='x', padx=10, pady=10)
        
        self.download_dir_var = tk.StringVar()
        self.download_dir_var.set(str(Path.cwd() / "JEE_PDFs"))
        
        ttk.Entry(dir_inner, textvariable=self.download_dir_var, width=60).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_inner, text="Browse", command=self.select_download_dir).pack(side='right', padx=(5, 0))
        
        # PDF selection
        selection_frame = ttk.LabelFrame(download_frame, text="Select PDFs to Download")
        selection_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for PDF selection
        tree_frame = ttk.Frame(selection_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('Year', 'Paper', 'Language', 'Status')
        self.pdf_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.pdf_tree.heading(col, text=col)
            self.pdf_tree.column(col, width=100)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.pdf_tree.yview)
        self.pdf_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        tree_scrollbar.pack(side='right', fill='y')
        self.pdf_tree.pack(side='left', fill='both', expand=True)
        
        # Populate tree
        self.populate_pdf_tree()
        
        # Download controls
        control_frame = ttk.Frame(selection_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(control_frame, text="Check All", command=self.check_all_pdfs).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Uncheck All", command=self.uncheck_all_pdfs).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Check Existing", command=self.check_existing_pdfs).pack(side='left', padx=5)
        
        self.download_progress = ttk.Progressbar(control_frame, mode='determinate')
        self.download_progress.pack(side='right', fill='x', expand=True, padx=(20, 0))
        
        ttk.Button(control_frame, text="Download Selected", 
                  command=self.download_selected_pdfs).pack(side='right', padx=5)
    
    def setup_annotation_tab(self, notebook):
        annotation_frame = ttk.Frame(notebook)
        notebook.add(annotation_frame, text="Annotate Questions")
        
        # Top frame for controls
        control_frame = ttk.Frame(annotation_frame)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # PDF loading and metadata
        pdf_frame = ttk.Frame(control_frame)
        pdf_frame.pack(side='left')
        
        ttk.Button(pdf_frame, text="Load PDF", command=self.load_pdf).pack(side='left', padx=5)
        ttk.Button(pdf_frame, text="Set Base Output Dir", command=self.set_output_dir).pack(side='left', padx=5)
        
        # PDF metadata display
        meta_frame = ttk.LabelFrame(control_frame, text="PDF Info")
        meta_frame.pack(side='left', padx=20)
        
        self.meta_label = ttk.Label(meta_frame, text="No PDF loaded")
        self.meta_label.pack(padx=10, pady=5)
        
        # Progress display
        progress_frame = ttk.LabelFrame(control_frame, text="Progress Status")
        progress_frame.pack(side='left', padx=10)
        
        self.progress_label = ttk.Label(progress_frame, text="No progress data", foreground='blue')
        self.progress_label.pack(padx=10, pady=5)
        
        # Subject selection
        subject_frame = ttk.LabelFrame(control_frame, text="Current Subject")
        subject_frame.pack(side='left', padx=20)
        
        self.current_subject_var = tk.StringVar()
        subject_combo = ttk.Combobox(subject_frame, textvariable=self.current_subject_var,
                                   values=['Mathematics', 'Physics', 'Chemistry'], width=12)
        subject_combo.pack(padx=10, pady=5)
        subject_combo.bind('<<ComboboxSelected>>', self.on_subject_change)
        
        # Page navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(side='left', padx=20)
        
        ttk.Button(nav_frame, text="◀ Prev", command=self.prev_page).pack(side='left')
        self.page_label = ttk.Label(nav_frame, text="Page: 0/0")
        self.page_label.pack(side='left', padx=10)
        ttk.Button(nav_frame, text="Next ▶", command=self.next_page).pack(side='left')
        
        # Zoom controls
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(side='left', padx=20)
        
        ttk.Button(zoom_frame, text="Zoom -", command=self.zoom_out).pack(side='left')
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side='left', padx=10)
        ttk.Button(zoom_frame, text="Zoom +", command=self.zoom_in).pack(side='left')
        
        # Action buttons
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(side='right', padx=20)
        
        ttk.Button(action_frame, text="Clear Page", command=self.clear_page_annotations).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Clear All", command=self.clear_all_annotations).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Export All", command=self.export_annotations).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Undo Last Export", command=self.undo_last_export).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Save Progress", command=self.save_progress).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Quit Annotating", command=self.quit_annotating).pack(side='left', padx=5)
        
        # Main content area
        main_frame = ttk.Frame(annotation_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel for image
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(side='left', fill='both', expand=True)
        
        # Canvas with scrollbars
        self.canvas = tk.Canvas(image_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(image_frame, orient='vertical', command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(image_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.start_rectangle)
        self.canvas.bind("<B1-Motion>", self.draw_rectangle)
        self.canvas.bind("<ButtonRelease-1>", self.end_rectangle)
        self.canvas.bind("<Double-Button-1>", self.delete_rectangle)
        
        # Right panel for annotations list
        right_panel = ttk.Frame(main_frame, width=350)
        right_panel.pack(side='right', fill='y', padx=(10, 0))
        right_panel.pack_propagate(False)
        
        ttk.Label(right_panel, text="All Annotations", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Resume work section
        resume_frame = ttk.LabelFrame(right_panel, text="Resume Previous Work")
        resume_frame.pack(fill='x', pady=5)
        
        self.resume_button = ttk.Button(resume_frame, text="Load Previous Progress", 
                                       command=self.load_previous_progress, state='disabled')
        self.resume_button.pack(pady=5)
        
        self.resume_info_label = ttk.Label(resume_frame, text="No previous work found", 
                                          font=('Arial', 8), foreground='gray')
        self.resume_info_label.pack(pady=2)
        
        # Filter frame
        filter_frame = ttk.Frame(right_panel)
        filter_frame.pack(fill='x', pady=2)
        
        ttk.Label(filter_frame, text="Filter:").pack(side='left')
        self.filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, width=12,
                                   values=['All', 'Current Page', 'MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching'])
        filter_combo.pack(side='left', padx=(5, 0))
        filter_combo.set('All')
        filter_combo.bind('<<ComboboxSelected>>', self.update_annotation_list)
        
        # Listbox for annotations
        list_frame = ttk.Frame(right_panel)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        self.annotation_listbox = tk.Listbox(list_frame)
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.annotation_listbox.yview)
        self.annotation_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        list_scrollbar.pack(side='right', fill='y')
        self.annotation_listbox.pack(side='left', fill='both', expand=True)
        
        # Bind listbox selection to show question location
        self.annotation_listbox.bind('<<ListboxSelect>>', self.on_annotation_select)
        self.annotation_listbox.bind('<Double-Button-1>', self.edit_annotation)
        self.annotation_listbox.bind('<Delete>', self.delete_selected_annotation)
        self.annotation_listbox.bind('<BackSpace>', self.delete_selected_annotation)
        
        # Context menu for annotations
        self.annotation_context_menu = tk.Menu(self.annotation_listbox, tearoff=0)
        self.annotation_context_menu.add_command(label="Go to Page", command=self.goto_annotation_page)
        self.annotation_context_menu.add_command(label="Edit Question", command=self.edit_annotation)
        self.annotation_context_menu.add_separator()
        self.annotation_context_menu.add_command(label="Delete", command=self.delete_selected_annotation)
        
        self.annotation_listbox.bind('<Button-3>', self.show_annotation_context_menu)  # Right-click
        
        # Question details frame - UPDATED: Removed Question ID field
        details_frame = ttk.LabelFrame(right_panel, text="Add New Question")
        details_frame.pack(fill='x', pady=5)
        
        ttk.Label(details_frame, text="Question Type:").pack(anchor='w')
        self.question_type_var = tk.StringVar()
        self.question_type_var.set('MCQ-Single')  # Default value
        type_combo = ttk.Combobox(details_frame, textvariable=self.question_type_var,
                                values=['MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching'])
        type_combo.pack(fill='x', pady=2)
        
        # Auto-generated Question ID display
        ttk.Label(details_frame, text="Next Question ID:").pack(anchor='w', pady=(10, 0))
        self.next_question_id_var = tk.StringVar()
        self.next_question_id_label = ttk.Label(details_frame, textvariable=self.next_question_id_var, 
                                               font=('Arial', 10, 'bold'), foreground='blue')
        self.next_question_id_label.pack(anchor='w', pady=2)
        
        # Update question ID when type changes
        type_combo.bind('<<ComboboxSelected>>', self.update_next_question_id)
        self.update_next_question_id()  # Initial update
        
        # Multi-rectangle support
        multi_rect_frame = ttk.LabelFrame(details_frame, text="Multi-Part Questions")
        multi_rect_frame.pack(fill='x', pady=(10, 5))
        
        # Rectangle count display
        self.rect_count_var = tk.StringVar()
        self.rect_count_var.set("Rectangles: 0")
        self.rect_count_label = ttk.Label(multi_rect_frame, textvariable=self.rect_count_var, 
                                         font=('Arial', 9), foreground='purple')
        self.rect_count_label.pack(anchor='w', pady=2)
        
        # Buttons for rectangle management
        rect_button_frame = ttk.Frame(multi_rect_frame)
        rect_button_frame.pack(fill='x', pady=2)
        
        self.add_rectangle_button = ttk.Button(rect_button_frame, text="Add Question", 
                                              command=self.add_single_rectangle_question, state='disabled')
        self.add_rectangle_button.pack(side='left', padx=(0, 5))
        
        self.add_another_rect_button = ttk.Button(rect_button_frame, text="Add Another Rectangle", 
                                                 command=self.add_another_rectangle, state='disabled')
        self.add_another_rect_button.pack(side='left', padx=5)
        
        # Output directory info
        output_info_frame = ttk.LabelFrame(right_panel, text="Output Directory")
        output_info_frame.pack(fill='x', pady=5)
        
        self.output_info_label = ttk.Label(output_info_frame, text="Not set", wraplength=300)
        self.output_info_label.pack(anchor='w', padx=5, pady=5)
    
    def scan_existing_questions_in_directory(self, question_type):
        """Scan the current output directory for existing questions of the given type"""
        if not hasattr(self, 'current_output_dir') or not self.current_output_dir or not self.current_output_dir.exists():
            return 0
        
        max_question_num = 0
        
        # Look for PNG files that match the question type pattern
        for png_file in self.current_output_dir.glob("*.png"):
            filename = png_file.stem
            # Pattern: *_MCQ-Single_q3_* or similar
            pattern = f"_{question_type}_q"
            
            if pattern in filename:
                # Extract the question number
                try:
                    # Find the position after the pattern
                    start_pos = filename.find(pattern) + len(pattern)
                    # Find the next underscore or end of string
                    end_pos = filename.find('_', start_pos)
                    if end_pos == -1:
                        end_pos = len(filename)
                    
                    question_num_str = filename[start_pos:end_pos]
                    question_num = int(question_num_str)
                    max_question_num = max(max_question_num, question_num)
                    
                except (ValueError, IndexError):
                    continue
        
        return max_question_num
    
    def update_question_counters_from_directory(self):
        """Update question counters based on existing files in the directory"""
        if not hasattr(self, 'current_output_dir') or not self.current_output_dir:
            return
        
        for question_type in self.question_counters.keys():
            existing_max = self.scan_existing_questions_in_directory(question_type)
            self.question_counters[question_type] = existing_max
        
        self.update_next_question_id()
    
    def add_single_rectangle_question(self):
        """Add a single rectangle question directly to annotations"""
        if not hasattr(self, 'current_rect') or not self.current_rect:
            messagebox.showwarning("Warning", "Please draw a rectangle first")
            return
        
        if not self.current_subject_var.get():
            messagebox.showwarning("Warning", "Please select a subject")
            return
        
        question_type = self.question_type_var.get()
        if not question_type:
            messagebox.showwarning("Warning", "Please select a question type")
            return
        
        # Generate question ID
        next_question_num = self.question_counters[question_type] + 1
        question_id = f"{question_type}_q{next_question_num}"
        
        # Create annotation directly
        annotation = {
            'question_id': question_id,
            'subject': self.current_subject_var.get(),
            'question_type': question_type,
            'page': self.current_page,
            'canvas_coords': self.current_rect['canvas_coords'],
            'pdf_coords': self.current_rect['pdf_coords'],
            'timestamp': time.time(),
            'year': self.pdf_metadata['year'],
            'paper': self.pdf_metadata['paper'],
            'language': self.pdf_metadata['language']
        }
        
        # Change rectangle appearance and add tags
        if self.temp_rect:
            self.canvas.itemconfig(self.temp_rect, outline='green', width=2)
            self.canvas.addtag_withtag('annotation', self.temp_rect)
            annotation['canvas_item'] = self.temp_rect
        
        # Update question counter
        self.question_counters[question_type] += 1
        
        # Add to annotations
        self.annotations.append(annotation)
        
        # Reset for next question
        self.temp_rect = None
        self.current_rect = None
        
        # Update UI
        self.update_annotation_list()
        self.update_next_question_id()
        self.add_rectangle_button.config(state='disabled')
        self.add_another_rect_button.config(state='normal')
        
        self.status_var.set(f"Added question: {annotation['question_id']}")
    
    def add_another_rectangle(self):
        """Switch to multi-rectangle mode and prepare for additional rectangles"""
        if not self.annotations:
            messagebox.showwarning("Warning", "Please add a question first")
            return
        
        # Get the last added annotation
        last_annotation = self.annotations[-1]
        
        # Enter multi-rectangle mode
        self.multi_rectangle_mode = True
        self.pending_question_data = last_annotation.copy()
        
        # Remove the last annotation from the list (we'll re-add it as multi-rectangle)
        self.annotations.remove(last_annotation)
        
        # Initialize rectangles list with the existing rectangle
        self.current_question_rectangles = [{
            'canvas_coords': last_annotation['canvas_coords'],
            'pdf_coords': last_annotation['pdf_coords'],
            'page': last_annotation['page'],
            'canvas_item': last_annotation.get('canvas_item')
        }]
        
        # Change the existing rectangle color to orange (pending)
        if last_annotation.get('canvas_item'):
            self.canvas.itemconfig(last_annotation['canvas_item'], outline='orange', width=3)
            self.canvas.addtag_withtag('pending', last_annotation['canvas_item'])
        
        # Update UI
        self.rect_count_var.set(f"Rectangles: {len(self.current_question_rectangles)}")
        self.add_rectangle_button.config(text="Add Rectangle", command=self.add_current_rectangle_to_multi)
        self.add_another_rect_button.config(state='disabled')
        
        # Add complete button
        self.complete_button = ttk.Button(self.add_rectangle_button.master, text="Complete Multi-Rect Question", 
                                         command=self.complete_multi_rectangle_question)
        self.complete_button.pack(side='left', padx=5)
        
        self.status_var.set(f"Multi-rectangle mode activated for {last_annotation['question_id']}. Draw another rectangle...")
    
    def add_current_rectangle_to_multi(self):
        """Add current rectangle to the multi-rectangle collection"""
        if not hasattr(self, 'current_rect') or not self.current_rect:
            messagebox.showwarning("Warning", "Please draw a rectangle first")
            return
        
        # Store rectangle data
        rect_data = {
            'canvas_coords': self.current_rect['canvas_coords'],
            'pdf_coords': self.current_rect['pdf_coords'],
            'page': self.current_page,
            'canvas_item': self.temp_rect
        }
        
        self.current_question_rectangles.append(rect_data)
        
        # Change rectangle color to indicate it's been added
        if self.temp_rect:
            self.canvas.itemconfig(self.temp_rect, outline='orange', width=3)
            self.canvas.addtag_withtag('pending', self.temp_rect)
        
        # Update UI
        self.rect_count_var.set(f"Rectangles: {len(self.current_question_rectangles)}")
        self.add_rectangle_button.config(state='disabled')
        
        # Clear current rectangle
        self.temp_rect = None
        self.current_rect = None
        
        self.status_var.set(f"Added rectangle {len(self.current_question_rectangles)} for question {self.pending_question_data['question_id']}")
    
    def complete_multi_rectangle_question(self):
        """Complete the multi-rectangle question and add it to annotations"""
        if not self.current_question_rectangles or not self.pending_question_data:
            messagebox.showwarning("Warning", "No multi-rectangle question in progress")
            return
        
        # Create the annotation with all rectangles
        annotation = self.pending_question_data.copy()
        annotation['rectangles'] = self.current_question_rectangles.copy()
        annotation['rectangle_count'] = len(self.current_question_rectangles)
        
        # For compatibility, set the main coordinates to the first rectangle
        annotation['canvas_coords'] = self.current_question_rectangles[0]['canvas_coords']
        annotation['pdf_coords'] = self.current_question_rectangles[0]['pdf_coords']
        annotation['page'] = self.current_question_rectangles[0]['page']
        
        # Change all rectangles to final green color
        for rect_data in self.current_question_rectangles:
            if 'canvas_item' in rect_data and rect_data['canvas_item']:
                self.canvas.itemconfig(rect_data['canvas_item'], outline='green', width=2)
                self.canvas.addtag_withtag('annotation', rect_data['canvas_item'])
        
        # Add to annotations
        self.annotations.append(annotation)
        
        # Reset multi-rectangle mode
        self.multi_rectangle_mode = False
        self.current_question_rectangles = []
        self.pending_question_data = None
        
        # Update UI
        self.rect_count_var.set("Rectangles: 0")
        self.add_rectangle_button.config(text="Add Question", command=self.add_single_rectangle_question, state='disabled')
        self.add_another_rect_button.config(state='disabled')
        
        # Remove complete button
        if hasattr(self, 'complete_button'):
            self.complete_button.destroy()
            delattr(self, 'complete_button')
        
        self.update_annotation_list()
        
        self.status_var.set(f"Completed multi-rectangle question: {annotation['question_id']} with {annotation['rectangle_count']} rectangles")
    
    def populate_pdf_tree(self):
        """Populate the PDF selection tree"""
        urls = JEEPDFDownloader.generate_urls()
        
        for url_info in urls:
            values = (url_info['year'], url_info['paper'], url_info['language'], 'Not Downloaded')
            item_id = self.pdf_tree.insert('', 'end', values=values)
            # Store URL info separately using item_id as key
            self.pdf_url_info[item_id] = url_info
    
    def select_download_dir(self):
        directory = filedialog.askdirectory(title="Select download directory")
        if directory:
            self.download_dir_var.set(directory)
    
    def check_all_pdfs(self):
        for item in self.pdf_tree.get_children():
            self.pdf_tree.selection_add(item)
    
    def uncheck_all_pdfs(self):
        self.pdf_tree.selection_remove(self.pdf_tree.selection())
    
    def update_next_question_id(self, event=None):
        """Update the next question ID based on current question type and existing files"""
        question_type = self.question_type_var.get()
        if question_type:
            # Update counters from directory first
            if hasattr(self, 'current_output_dir') and self.current_output_dir:
                existing_max = self.scan_existing_questions_in_directory(question_type)
                self.question_counters[question_type] = max(self.question_counters[question_type], existing_max)
            
            next_number = self.question_counters[question_type] + 1
            question_id = f"{question_type}_q{next_number}"
            self.next_question_id_var.set(question_id)
    
    def on_annotation_select(self, event):
        """Handle annotation selection from listbox"""
        selection = self.annotation_listbox.curselection()
        if selection:
            index = selection[0]
            # Get filtered annotations
            filtered_annotations = self.get_filtered_annotations()
            if index < len(filtered_annotations):
                annotation = filtered_annotations[index]
                # Navigate to the page of selected annotation
                target_page = annotation['page']
                if target_page != self.current_page:
                    self.current_page = target_page
                    self.load_page()
                    
                # Highlight the annotation briefly
                if 'rectangles' in annotation:
                    # Multi-rectangle question
                    for rect_data in annotation['rectangles']:
                        if 'canvas_item' in rect_data and rect_data['canvas_item']:
                            original_color = self.canvas.itemcget(rect_data['canvas_item'], 'outline')
                            self.canvas.itemconfig(rect_data['canvas_item'], outline='red', width=4)
                            self.root.after(1000, lambda item=rect_data['canvas_item'], color=original_color: 
                                          self.canvas.itemconfig(item, outline=color, width=2))
                elif 'canvas_item' in annotation:
                    # Single rectangle question
                    original_color = self.canvas.itemcget(annotation['canvas_item'], 'outline')
                    self.canvas.itemconfig(annotation['canvas_item'], outline='red', width=4)
                    self.root.after(1000, lambda: self.canvas.itemconfig(annotation['canvas_item'], 
                                                                        outline=original_color, width=2))
    
    def show_annotation_context_menu(self, event):
        """Show context menu for annotation list"""
        try:
            self.annotation_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.annotation_context_menu.grab_release()
    
    def goto_annotation_page(self):
        """Navigate to the page of selected annotation"""
        selection = self.annotation_listbox.curselection()
        if selection:
            index = selection[0]
            filtered_annotations = self.get_filtered_annotations()
            if index < len(filtered_annotations):
                annotation = filtered_annotations[index]
                target_page = annotation['page']
                if target_page != self.current_page:
                    self.current_page = target_page
                    self.load_page()
    
    def delete_selected_annotation(self, event=None):
        """Delete the selected annotation from the list"""
        selection = self.annotation_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an annotation to delete")
            return
        
        index = selection[0]
        filtered_annotations = self.get_filtered_annotations()
        
        if index >= len(filtered_annotations):
            return
        
        annotation_to_delete = filtered_annotations[index]
        
        # Confirm deletion
        rect_info = f" ({annotation_to_delete.get('rectangle_count', 1)} rectangle(s))" if annotation_to_delete.get('rectangle_count', 1) > 1 else ""
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this annotation?\n\n"
            f"Question ID: {annotation_to_delete['question_id']}\n"
            f"Subject: {annotation_to_delete['subject']}\n"
            f"Type: {annotation_to_delete['question_type']}\n"
            f"Page: {annotation_to_delete['page'] + 1}{rect_info}"
        )
        
        if not confirm:
            return
        
        # Remove from canvas if visible
        if 'rectangles' in annotation_to_delete:
            # Multi-rectangle question
            for rect_data in annotation_to_delete['rectangles']:
                if 'canvas_item' in rect_data and rect_data['canvas_item']:
                    self.canvas.delete(rect_data['canvas_item'])
        elif 'canvas_item' in annotation_to_delete:
            # Single rectangle question
            self.canvas.delete(annotation_to_delete['canvas_item'])
        
        # Remove from annotations list
        self.annotations.remove(annotation_to_delete)
        
        # Update question counter (decrement if this was the highest number)
        question_type = annotation_to_delete['question_type']
        question_id = annotation_to_delete['question_id']
        
        # Extract question number from ID (e.g., "MCQ-Single_q5" -> 5)
        try:
            q_num_str = question_id.split('_q')[-1]
            q_num = int(q_num_str)
            
            # Check if this was the highest numbered question of this type
            remaining_questions = [ann for ann in self.annotations if ann['question_type'] == question_type]
            if remaining_questions:
                highest_remaining = max(
                    int(ann['question_id'].split('_q')[-1]) 
                    for ann in remaining_questions
                )
                self.question_counters[question_type] = highest_remaining
            else:
                self.question_counters[question_type] = 0
        except (ValueError, IndexError):
            # If we can't parse the number, just decrement by 1
            self.question_counters[question_type] = max(0, self.question_counters[question_type] - 1)
        
        # Update UI
        self.update_annotation_list()
        self.update_next_question_id()
        
        self.status_var.set(f"Deleted annotation: {annotation_to_delete['question_id']}")
    
    def edit_annotation(self, event=None):
        """Edit the selected annotation"""
        selection = self.annotation_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an annotation to edit")
            return
        
        index = selection[0]
        filtered_annotations = self.get_filtered_annotations()
        
        if index >= len(filtered_annotations):
            return
        
        annotation_to_edit = filtered_annotations[index]
        
        # Create edit dialog
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("Edit Annotation")
        edit_dialog.geometry("300x300")
        edit_dialog.grab_set()
        
        # Center the dialog
        edit_dialog.transient(self.root)
        
        ttk.Label(edit_dialog, text="Edit Question Details", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Question ID (read-only display)
        ttk.Label(edit_dialog, text="Question ID:").pack(anchor='w', padx=20)
        ttk.Label(edit_dialog, text=annotation_to_edit['question_id'], 
                 font=('Arial', 10, 'bold'), foreground='blue').pack(anchor='w', padx=20, pady=(0, 10))
        
        # Subject
        ttk.Label(edit_dialog, text="Subject:").pack(anchor='w', padx=20)
        subject_var = tk.StringVar(value=annotation_to_edit['subject'])
        subject_combo = ttk.Combobox(edit_dialog, textvariable=subject_var,
                                   values=['Mathematics', 'Physics', 'Chemistry'], width=25)
        subject_combo.pack(padx=20, pady=(0, 10))
        
        # Question Type
        ttk.Label(edit_dialog, text="Question Type:").pack(anchor='w', padx=20)
        type_var = tk.StringVar(value=annotation_to_edit['question_type'])
        type_combo = ttk.Combobox(edit_dialog, textvariable=type_var,
                                values=['MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching'], width=25)
        type_combo.pack(padx=20, pady=(0, 10))
        
        # Rectangle info (read-only)
        rect_count = annotation_to_edit.get('rectangle_count', 1)
        rect_info = f"Rectangles: {rect_count}" if rect_count > 1 else "Single rectangle"
        ttk.Label(edit_dialog, text=rect_info, 
                 font=('Arial', 9), foreground='purple').pack(anchor='w', padx=20, pady=(0, 5))
        
        # Page info (read-only)
        ttk.Label(edit_dialog, text=f"Page: {annotation_to_edit['page'] + 1}", 
                 font=('Arial', 9), foreground='gray').pack(anchor='w', padx=20, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(edit_dialog)
        button_frame.pack(pady=10)
        
        def save_changes():
            # Update the annotation
            annotation_to_edit['subject'] = subject_var.get()
            annotation_to_edit['question_type'] = type_var.get()
            
            # Update UI
            self.update_annotation_list()
            edit_dialog.destroy()
            
            self.status_var.set(f"Updated annotation: {annotation_to_edit['question_id']}")
        
        def cancel_edit():
            edit_dialog.destroy()
        
        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=cancel_edit).pack(side='left', padx=10)
    
    def get_filtered_annotations(self):
        """Get annotations based on current filter"""
        filter_value = self.filter_var.get()
        
        if filter_value == 'All':
            return self.annotations
        elif filter_value == 'Current Page':
            return [ann for ann in self.annotations if ann['page'] == self.current_page]
        elif filter_value in ['MCQ-Single', 'MCQ-Multiple', 'Numerical', 'Matching']:
            return [ann for ann in self.annotations if ann['question_type'] == filter_value]
        else:
            return self.annotations
    
    def check_existing_pdfs(self):
        """Check which PDFs already exist and update status"""
        download_dir = Path(self.download_dir_var.get())
        
        for item in self.pdf_tree.get_children():
            if item in self.pdf_url_info:
                url_info = self.pdf_url_info[item]
                filename = url_info['filename']
                filepath = download_dir / filename
                
                if filepath.exists():
                    values = list(self.pdf_tree.item(item)['values'])
                    values[3] = 'Downloaded'
                    self.pdf_tree.item(item, values=values)
    
    def download_selected_pdfs(self):
        """Download selected PDFs"""
        selected_items = self.pdf_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select PDFs to download")
            return
        
        download_dir = Path(self.download_dir_var.get())
        download_dir.mkdir(parents=True, exist_ok=True)
        
        self.download_progress['maximum'] = len(selected_items)
        self.download_progress['value'] = 0
        
        downloaded_count = 0
        failed_downloads = []
        
        for i, item in enumerate(selected_items):
            # Get URL info for this item
            if item in self.pdf_url_info:
                url_info = self.pdf_url_info[item]
            else:
                # Fallback: reconstruct from tree values
                values = self.pdf_tree.item(item)['values']
                year, paper, language = values[0], values[1], values[2]
                url_info = {
                    'url': f"{JEEPDFDownloader.BASE_URL}{year}_{paper}_{language}.pdf",
                    'year': year,
                    'paper': paper,
                    'language': language,
                    'filename': f"{year}_{paper}_{language}.pdf"
                }
            
            try:
                self.status_var.set(f"Downloading {url_info['filename']}...")
                self.root.update()
                
                JEEPDFDownloader.download_pdf(url_info, download_dir)
                
                # Update status in tree
                values = list(self.pdf_tree.item(item)['values'])
                values[3] = 'Downloaded'
                self.pdf_tree.item(item, values=values)
                
                downloaded_count += 1
                
            except Exception as e:
                failed_downloads.append(f"{url_info['filename']}: {str(e)}")
                # Update status in tree
                values = list(self.pdf_tree.item(item)['values'])
                values[3] = 'Failed'
                self.pdf_tree.item(item, values=values)
            
            self.download_progress['value'] = i + 1
            self.root.update()
        
        # Show results
        message = f"Downloaded {downloaded_count} PDFs successfully"
        if failed_downloads:
            message += f"\n\nFailed downloads:\n" + "\n".join(failed_downloads[:5])
            if len(failed_downloads) > 5:
                message += f"\n... and {len(failed_downloads) - 5} more"
        
        messagebox.showinfo("Download Complete", message)
        self.status_var.set(f"Download complete: {downloaded_count} successful, {len(failed_downloads)} failed")
    
    def parse_pdf_filename(self, filename):
        """Parse JEE PDF filename to extract metadata"""
        match = re.match(r'(\d{4})_(\d)_(English|Hindi)\.pdf', filename)
        if match:
            return {
                'year': int(match.group(1)),
                'paper': int(match.group(2)),
                'language': match.group(3)
            }
        return None
    
    def load_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if file_path:
            try:
                self.pdf_doc = fitz.open(file_path)
                self.total_pages = len(self.pdf_doc)
                self.current_page = 0
                self.annotations = []
                
                # Reset multi-rectangle state
                self.current_question_rectangles = []
                self.pending_question_data = None
                
                # Parse PDF metadata from filename
                filename = Path(file_path).name
                parsed_meta = self.parse_pdf_filename(filename)
                
                if parsed_meta:
                    self.pdf_metadata.update(parsed_meta)
                    meta_text = f"Year: {parsed_meta['year']}, Paper: {parsed_meta['paper']}, Language: {parsed_meta['language']}"
                else:
                    meta_text = f"Custom PDF: {filename}"
                
                self.meta_label.config(text=meta_text)
                
                self.load_page()
                self.check_existing_progress()  # Check for previous work
                self.update_output_directory()
                self.status_var.set(f"Loaded: {filename} ({self.total_pages} pages)")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load PDF: {str(e)}")
    
    def check_existing_progress(self):
        """Check if there's existing work for this PDF"""
        if not self.output_base_dir:
            self.output_base_dir = Path.cwd() / "question_images"
        
        # Check if there's a master progress file for this PDF
        if self.pdf_metadata['year'] and self.pdf_metadata['paper'] and self.pdf_metadata['language']:
            pdf_dir = (
                self.output_base_dir / 
                str(self.pdf_metadata['year']) / 
                f"Paper_{self.pdf_metadata['paper']}_{self.pdf_metadata['language']}"
            )
            
            master_progress_file = pdf_dir / "master_progress.json"
            
            if master_progress_file.exists():
                try:
                    with open(master_progress_file, 'r') as f:
                        saved_progress = json.load(f)
                    
                    # Update progress display
                    completed_subjects = saved_progress.get('subjects_completed', [])
                    total_questions = saved_progress.get('total_questions_annotated', 0)
                    last_worked = saved_progress.get('last_worked_date', 'Unknown')
                    
                    progress_text = f"Previous work found!\n"
                    progress_text += f"Completed: {', '.join(completed_subjects) if completed_subjects else 'None'}\n"
                    progress_text += f"Total questions: {total_questions}\n"
                    progress_text += f"Last worked: {last_worked}"
                    
                    self.progress_label.config(text=progress_text, foreground='green')
                    self.resume_button.config(state='normal')
                    self.resume_info_label.config(text="Click to resume from where you left off")
                    
                    # Also check individual subject progress
                    subject_progress = self.scan_subject_directories(pdf_dir)
                    if subject_progress:
                        self.display_subject_progress(subject_progress)
                    
                except Exception as e:
                    self.progress_label.config(text="Error reading progress file", foreground='red')
            else:
                # No master progress, but check for individual exports
                subject_progress = self.scan_subject_directories(pdf_dir)
                if subject_progress:
                    self.progress_label.config(text="Found exported images\n(No progress file)", foreground='orange')
                    self.resume_button.config(state='normal')
                    self.resume_info_label.config(text="Found previous exports - click to analyze")
                    self.display_subject_progress(subject_progress)
                else:
                    self.progress_label.config(text="No previous work found", foreground='gray')
    
    def scan_subject_directories(self, pdf_dir):
        """Scan for existing subject directories and count questions"""
        if not pdf_dir.exists():
            return {}
        
        subject_progress = {}
        subjects = ['Mathematics', 'Physics', 'Chemistry']
        
        for subject in subjects:
            subject_dir = pdf_dir / subject
            if subject_dir.exists():
                # Count PNG files (exported questions)
                png_files = list(subject_dir.glob("*.png"))
                if png_files:
                    # Find highest question number for each type
                    question_counts = {'MCQ-Single': 0, 'MCQ-Multiple': 0, 'Numerical': 0, 'Matching': 0}
                    
                    for png_file in png_files:
                        # Parse filename to extract question info
                        name_parts = png_file.stem.split('_')
                        for part in name_parts:
                            for q_type in question_counts.keys():
                                if part.startswith(q_type):
                                    # Extract question number
                                    q_num_str = part.replace(q_type, '').replace('q', '')
                                    try:
                                        q_num = int(q_num_str)
                                        question_counts[q_type] = max(question_counts[q_type], q_num)
                                    except ValueError:
                                        continue
                    
                    subject_progress[subject] = {
                        'total_questions': len(png_files),
                        'question_counts': question_counts,
                        'last_modified': max(png_file.stat().st_mtime for png_file in png_files)
                    }
        
        return subject_progress
    
    def display_subject_progress(self, subject_progress):
        """Display subject progress in a readable format"""
        if not subject_progress:
            return
        
        progress_text = "Found previous work:\n"
        for subject, data in subject_progress.items():
            progress_text += f"• {subject}: {data['total_questions']} questions\n"
        
        self.progress_label.config(text=progress_text, foreground='blue')
    
    def load_previous_progress(self):
        """Load and resume from previous progress"""
        if not self.pdf_metadata['year']:
            messagebox.showwarning("Warning", "No PDF metadata available")
            return
        
        pdf_dir = (
            self.output_base_dir / 
            str(self.pdf_metadata['year']) / 
            f"Paper_{self.pdf_metadata['paper']}_{self.pdf_metadata['language']}"
        )
        
        master_progress_file = pdf_dir / "master_progress.json"
        
        if master_progress_file.exists():
            # Load from master progress file
            try:
                with open(master_progress_file, 'r') as f:
                    saved_progress = json.load(f)
                
                self.progress_data = saved_progress
                
                # Restore question counters
                if 'question_counters' in saved_progress:
                    self.question_counters = saved_progress['question_counters']
                
                # Navigate to last worked page
                if 'last_worked_page' in saved_progress:
                    self.current_page = saved_progress['last_worked_page']
                    self.load_page()
                
                # Set subject to next incomplete one
                completed = saved_progress.get('subjects_completed', [])
                all_subjects = ['Mathematics', 'Physics', 'Chemistry']
                
                for subject in all_subjects:
                    if subject not in completed:
                        self.current_subject_var.set(subject)
                        self.update_output_directory()
                        break
                
                self.update_next_question_id()
                messagebox.showinfo("Progress Loaded", 
                                  f"Resumed from previous session!\n"
                                  f"Completed subjects: {', '.join(completed)}\n"
                                  f"Current subject: {self.current_subject_var.get()}\n"
                                  f"Page: {self.current_page + 1}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load progress: {str(e)}")
        else:
            # Analyze existing exports and estimate progress
            subject_progress = self.scan_subject_directories(pdf_dir)
            if subject_progress:
                self.estimate_progress_from_exports(subject_progress)
    
    def estimate_progress_from_exports(self, subject_progress):
        """Estimate progress from existing exported files"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Resume Progress")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Found previous work:", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Display found work
        for subject, data in subject_progress.items():
            frame = ttk.LabelFrame(dialog, text=subject)
            frame.pack(fill='x', padx=20, pady=5)
            
            ttk.Label(frame, text=f"Total questions: {data['total_questions']}").pack(anchor='w')
            
            for q_type, count in data['question_counts'].items():
                if count > 0:
                    ttk.Label(frame, text=f"  {q_type}: up to q{count}").pack(anchor='w')
        
        ttk.Label(dialog, text="Select subject to continue with:", font=('Arial', 10, 'bold')).pack(pady=(20, 5))
        
        subject_var = tk.StringVar()
        for subject in ['Mathematics', 'Physics', 'Chemistry']:
            ttk.Radiobutton(dialog, text=subject, variable=subject_var, value=subject).pack()
        
        # Set default to first incomplete subject
        completed_subjects = list(subject_progress.keys())
        all_subjects = ['Mathematics', 'Physics', 'Chemistry']
        next_subject = next((s for s in all_subjects if s not in completed_subjects), 'Mathematics')
        subject_var.set(next_subject)
        
        def resume():
            selected_subject = subject_var.get()
            if selected_subject:
                # Set counters based on found progress
                if selected_subject in subject_progress:
                    found_counts = subject_progress[selected_subject]['question_counts']
                    for q_type, count in found_counts.items():
                        self.question_counters[q_type] = count
                
                self.current_subject_var.set(selected_subject)
                self.update_output_directory()
                self.update_next_question_id()
                
                # Update progress data
                self.progress_data['subjects_completed'] = list(subject_progress.keys())
                self.progress_data['current_subject_progress'] = subject_progress
                
                dialog.destroy()
                messagebox.showinfo("Resumed", f"Continuing with {selected_subject}")
        
        ttk.Button(dialog, text="Resume", command=resume).pack(pady=20)
    
    def set_output_dir(self):
        directory = filedialog.askdirectory(title="Select base output directory")
        if directory:
            self.output_base_dir = Path(directory)
            self.update_output_directory()
    
    def update_output_directory(self):
        """Update the output directory based on PDF metadata and current subject"""
        if not self.output_base_dir:
            self.output_base_dir = Path.cwd() / "question_images"
        
        # Create directory structure: base_dir/year/paper_language/subject/
        if self.pdf_metadata['year'] and self.pdf_metadata['paper'] and self.pdf_metadata['language']:
            self.current_output_dir = (
                self.output_base_dir / 
                str(self.pdf_metadata['year']) / 
                f"Paper_{self.pdf_metadata['paper']}_{self.pdf_metadata['language']}" /
                (self.current_subject_var.get() or "Unknown_Subject")
            )
        else:
            self.current_output_dir = self.output_base_dir / "custom_pdf" / (self.current_subject_var.get() or "Unknown_Subject")
        
        self.current_output_dir.mkdir(parents=True, exist_ok=True)
        self.output_info_label.config(text=str(self.current_output_dir))
        
        # Update question counters based on existing files in the directory
        self.update_question_counters_from_directory()
    
    def on_subject_change(self, event=None):
        """Handle subject change"""
        self.pdf_metadata['current_subject'] = self.current_subject_var.get()
        self.update_output_directory()
        
        # Update progress tracking
        self.progress_data['last_worked_page'] = self.current_page
    
    def quit_annotating(self):
        """Save comprehensive progress and quit annotation session"""
        if not self.annotations and not self.progress_data.get('total_questions_annotated', 0):
            messagebox.showinfo("Info", "No annotations to save")
            return
        
        # Save any pending annotations first
        if self.annotations:
            export_choice = messagebox.askyesnocancel(
                "Unsaved Annotations", 
                f"You have {len(self.annotations)} unsaved annotations for {self.current_subject_var.get()}.\n\n"
                "Do you want to export them before quitting?\n\n"
                "Yes: Export and save progress\n"
                "No: Save progress without exporting\n"
                "Cancel: Return to annotation"
            )
            
            if export_choice is None:  # Cancel
                return
            elif export_choice:  # Yes - export first
                self.export_annotations()
                # Don't return here, continue to save master progress
        
        # Save master progress file
        try:
            if not hasattr(self, 'current_output_dir') or not self.current_output_dir:
                self.update_output_directory()
            
            pdf_dir = self.current_output_dir.parent  # Go up one level from subject dir
            master_progress_file = pdf_dir / "master_progress.json"
            
            # Update progress data
            current_time = time.time()
            self.progress_data.update({
                'pdf_metadata': self.pdf_metadata,
                'question_counters': self.question_counters,
                'last_worked_page': self.current_page,
                'last_worked_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'session_end_time': current_time,
                'total_session_time': current_time - self.progress_data.get('session_start_time', current_time)
            })
            
            # Scan all subject directories for completion status
            subject_progress = self.scan_subject_directories(pdf_dir)
            completed_subjects = []
            total_questions = 0
            
            for subject, data in subject_progress.items():
                if data['total_questions'] > 0:
                    completed_subjects.append(subject)
                    total_questions += data['total_questions']
            
            self.progress_data['subjects_completed'] = completed_subjects
            self.progress_data['total_questions_annotated'] = total_questions
            self.progress_data['subject_progress_details'] = subject_progress
            
            # Save master progress
            with open(master_progress_file, 'w') as f:
                json.dump(self.progress_data, f, indent=2)
            
            # Create a readable summary
            summary_file = pdf_dir / "annotation_session_summary.txt"
            with open(summary_file, 'w') as f:
                f.write(f"JEE Advanced Annotation Session Summary\n")
                f.write(f"=" * 45 + "\n\n")
                f.write(f"PDF: Year {self.pdf_metadata.get('year', 'Unknown')}, ")
                f.write(f"Paper {self.pdf_metadata.get('paper', 'Unknown')}, ")
                f.write(f"Language: {self.pdf_metadata.get('language', 'Unknown')}\n")
                f.write(f"Session Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Questions Annotated: {total_questions}\n\n")
                
                f.write("Subject Completion Status:\n")
                all_subjects = ['Mathematics', 'Physics', 'Chemistry']
                for subject in all_subjects:
                    status = "✓ COMPLETED" if subject in completed_subjects else "○ PENDING"
                    questions = subject_progress.get(subject, {}).get('total_questions', 0)
                    f.write(f"  {subject}: {status} ({questions} questions)\n")
                
                f.write(f"\nLast worked on page: {self.current_page + 1}\n")
                
                if len(completed_subjects) == 3:
                    f.write(f"\n🎉 ALL SUBJECTS COMPLETED! 🎉\n")
                else:
                    remaining = [s for s in all_subjects if s not in completed_subjects]
                    f.write(f"\nNext to work on: {', '.join(remaining)}\n")
            
            # Show completion dialog
            completion_percentage = (len(completed_subjects) / 3) * 100
            messagebox.showinfo("Session Saved", 
                              f"Annotation session saved successfully!\n\n"
                              f"Progress: {completion_percentage:.0f}% complete\n"
                              f"Completed subjects: {', '.join(completed_subjects)}\n"
                              f"Total questions: {total_questions}\n\n"
                              f"Progress saved to: {master_progress_file}")
            
            # Clear current session
            self.clear_all_annotations()
            self.progress_data = {
                'subjects_completed': [],
                'current_subject_progress': {},
                'last_worked_page': 0,
                'total_questions_annotated': 0,
                'session_start_time': None
            }
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save progress: {str(e)}")
    
    def load_page(self):
        if not self.pdf_doc:
            return
            
        try:
            page = self.pdf_doc[self.current_page]
            
            # Convert page to image
            mat = fitz.Matrix(self.scale_factor, self.scale_factor)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            
            # Convert to PIL Image and then to PhotoImage
            pil_image = Image.open(io.BytesIO(img_data))
            self.current_image = ImageTk.PhotoImage(pil_image)
            
            # Clear canvas and display image
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor='nw', image=self.current_image)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update page label
            self.page_label.config(text=f"Page: {self.current_page + 1}/{self.total_pages}")
            
            # Load existing annotations for this page
            self.load_page_annotations()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load page: {str(e)}")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_page()
    
    def zoom_in(self):
        self.scale_factor *= 1.2
        self.zoom_label.config(text=f"{int(self.scale_factor * 100)}%")
        self.load_page()
    
    def zoom_out(self):
        self.scale_factor /= 1.2
        self.zoom_label.config(text=f"{int(self.scale_factor * 100)}%")
        self.load_page()
    
    def start_rectangle(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Delete temporary rectangle if it exists
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
    
    def draw_rectangle(self, event):
        if self.start_x is not None and self.start_y is not None:
            # Delete previous temporary rectangle
            if self.temp_rect:
                self.canvas.delete(self.temp_rect)
            
            # Draw new temporary rectangle
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)
            
            self.temp_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, end_x, end_y,
                outline='red', width=2, tags='temp'
            )
    
    def end_rectangle(self, event):
        if self.start_x is not None and self.start_y is not None:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)
            
            # Ensure rectangle has minimum size
            if abs(end_x - self.start_x) > 10 and abs(end_y - self.start_y) > 10:
                # Normalize coordinates
                x1, x2 = min(self.start_x, end_x), max(self.start_x, end_x)
                y1, y2 = min(self.start_y, end_y), max(self.start_y, end_y)
                
                # Convert to original PDF coordinates
                pdf_x1 = x1 / self.scale_factor
                pdf_y1 = y1 / self.scale_factor
                pdf_x2 = x2 / self.scale_factor
                pdf_y2 = y2 / self.scale_factor
                
                # Store rectangle info
                self.current_rect = {
                    'canvas_coords': (x1, y1, x2, y2),
                    'pdf_coords': (pdf_x1, pdf_y1, pdf_x2, pdf_y2),
                    'page': self.current_page
                }
                
                # Change color to indicate selection and enable add button
                if self.temp_rect:
                    self.canvas.itemconfig(self.temp_rect, outline='blue', width=3)
                    if not self.multi_rectangle_mode:
                        self.add_rectangle_button.config(state='normal')
                    else:
                        self.add_rectangle_button.config(state='normal')
            
            # Reset start coordinates
            self.start_x = None
            self.start_y = None
    
    def delete_rectangle(self, event):
        # Find rectangle at click position
        click_x = self.canvas.canvasx(event.x)
        click_y = self.canvas.canvasy(event.y)
        
        overlapping = self.canvas.find_overlapping(click_x-5, click_y-5, click_x+5, click_y+5)
        
        for item in overlapping:
            if 'annotation' in self.canvas.gettags(item):
                # Find and remove annotation
                for i, ann in enumerate(self.get_page_annotations()):
                    if 'rectangles' in ann:
                        # Multi-rectangle question
                        for rect_data in ann['rectangles']:
                            if rect_data.get('canvas_item') == item:
                                self.annotations.remove(ann)
                                # Remove all rectangles from canvas
                                for rd in ann['rectangles']:
                                    if 'canvas_item' in rd:
                                        self.canvas.delete(rd['canvas_item'])
                                self.update_annotation_list()
                                return
                    elif ann.get('canvas_item') == item:
                        # Single rectangle question
                        self.annotations.remove(ann)
                        self.canvas.delete(item)
                        self.update_annotation_list()
                        break
    
    def get_page_annotations(self):
        return [ann for ann in self.annotations if ann['page'] == self.current_page]
    
    def load_page_annotations(self):
        # Draw existing annotations for current page
        page_annotations = self.get_page_annotations()
        
        for ann in page_annotations:
            if 'rectangles' in ann:
                # Multi-rectangle question - draw all rectangles
                for rect_data in ann['rectangles']:
                    if 'canvas_coords' in rect_data:
                        x1, y1, x2, y2 = rect_data['canvas_coords']
                        rect_item = self.canvas.create_rectangle(
                            x1, y1, x2, y2, outline='green', width=2, tags='annotation'
                        )
                        rect_data['canvas_item'] = rect_item
            elif 'canvas_coords' in ann:
                # Single rectangle question
                x1, y1, x2, y2 = ann['canvas_coords']
                rect_item = self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline='green', width=2, tags='annotation'
                )
                ann['canvas_item'] = rect_item
        
        self.update_annotation_list()
    
    def update_annotation_list(self, event=None):
        self.annotation_listbox.delete(0, tk.END)
        filtered_annotations = self.get_filtered_annotations()
        
        for ann in filtered_annotations:
            page_indicator = f"[P{ann['page'] + 1}]" if self.filter_var.get() != 'Current Page' else ""
            rect_indicator = f"({ann.get('rectangle_count', 1)}R)" if ann.get('rectangle_count', 1) > 1 else ""
            display_text = f"{ann['question_id']} {page_indicator} {rect_indicator} - {ann['subject']} ({ann['question_type']})"
            self.annotation_listbox.insert(tk.END, display_text)
    
    def clear_page_annotations(self):
        # Remove annotations for current page
        page_annotations = self.get_page_annotations()
        
        for ann in page_annotations:
            if 'rectangles' in ann:
                # Multi-rectangle question
                for rect_data in ann['rectangles']:
                    if 'canvas_item' in rect_data:
                        self.canvas.delete(rect_data['canvas_item'])
            elif 'canvas_item' in ann:
                # Single rectangle question
                self.canvas.delete(ann['canvas_item'])
            
            self.annotations.remove(ann)
            # Decrement counter for deleted question
            if ann['question_type'] in self.question_counters:
                self.question_counters[ann['question_type']] = max(0, self.question_counters[ann['question_type']] - 1)
        
        self.update_annotation_list()
        self.update_next_question_id()
        self.status_var.set(f"Cleared annotations for page {self.current_page + 1}")
    
    def save_progress(self):
        if not self.annotations:
            messagebox.showinfo("Info", "No annotations to save")
            return
        
        try:
            # Save annotations as JSON
            save_data = {
                'pdf_metadata': self.pdf_metadata,
                'pdf_path': self.pdf_doc.name if self.pdf_doc else '',
                'total_pages': self.total_pages,
                'annotations': []
            }
            
            for ann in self.annotations:
                # Clean annotation data for JSON serialization
                clean_ann = {k: v for k, v in ann.items() if k not in ['canvas_item']}
                # Clean rectangles data
                if 'rectangles' in clean_ann:
                    clean_rectangles = []
                    for rect_data in clean_ann['rectangles']:
                        clean_rect = {k: v for k, v in rect_data.items() if k != 'canvas_item'}
                        clean_rectangles.append(clean_rect)
                    clean_ann['rectangles'] = clean_rectangles
                save_data['annotations'].append(clean_ann)
            
            # Save to current output directory
            if hasattr(self, 'current_output_dir') and self.current_output_dir:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"annotations_progress_{timestamp}.json"
                filepath = self.current_output_dir / filename
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"annotations_progress_{timestamp}.json"
                filepath = Path(filename)
            
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            self.status_var.set(f"Progress saved: {filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save progress: {str(e)}")
    
    def merge_rectangles_to_image(self, page, rectangles_data):
        """Merge multiple rectangles from potentially different pages into one image"""
        if not rectangles_data:
            return None
        
        # Group rectangles by page
        page_groups = {}
        for rect_data in rectangles_data:
            page_num = rect_data['page']
            if page_num not in page_groups:
                page_groups[page_num] = []
            page_groups[page_num].append(rect_data)
        
        images = []
        
        # Process each page group
        for page_num, page_rects in page_groups.items():
            page_obj = self.pdf_doc[page_num]
            
            for rect_data in page_rects:
                # Get individual rectangle
                x1, y1, x2, y2 = rect_data['pdf_coords']
                rect = fitz.Rect(x1, y1, x2, y2)
                
                # Crop page to rectangle with high resolution
                pix = page_obj.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                images.append(pil_image)
        
        if not images:
            return None
        
        if len(images) == 1:
            return images[0]
        
        # Merge multiple images vertically
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        
        merged_image = Image.new('RGB', (total_width, total_height), 'white')
        
        y_offset = 0
        for img in images:
            # Center the image horizontally if it's narrower than the total width
            x_offset = (total_width - img.width) // 2
            merged_image.paste(img, (x_offset, y_offset))
            y_offset += img.height
        
        return merged_image
    
    def export_annotations(self):
        if not self.annotations:
            messagebox.showinfo("Info", "No annotations to export")
            return
        
        if not self.output_base_dir:
            messagebox.showwarning("Warning", "Please set base output directory first")
            return
        
        try:
            # Group annotations by subject
            subject_annotations = {}
            for ann in self.annotations:
                subject = ann['subject']
                if subject not in subject_annotations:
                    subject_annotations[subject] = []
                subject_annotations[subject].append(ann)
            
            exported_count = 0
            export_info = {
                'timestamp': time.time(),
                'export_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'subjects': {}
            }
            
            # Export to appropriate subject directories
            for subject, annotations in subject_annotations.items():
                # Create subject-specific output directory
                if self.pdf_metadata['year'] and self.pdf_metadata['paper'] and self.pdf_metadata['language']:
                    subject_output_dir = (
                        self.output_base_dir / 
                        str(self.pdf_metadata['year']) / 
                        f"Paper_{self.pdf_metadata['paper']}_{self.pdf_metadata['language']}" /
                        subject
                    )
                else:
                    subject_output_dir = self.output_base_dir / "custom_pdf" / subject
                
                subject_output_dir.mkdir(parents=True, exist_ok=True)
                
                subject_files = []
                
                for ann in annotations:
                    # Create structured filename
                    year = ann.get('year', 'unknown')
                    paper = ann.get('paper', 'unknown')
                    language = ann.get('language', 'unknown')
                    question_id = ann['question_id'].replace('/', '_').replace('.', '_')
                    question_type = ann.get('question_type', 'unknown').replace(' ', '_')
                    page_num = ann['page'] + 1
                    
                    filename = f"{year}_P{paper}_{language}_{subject}_{question_id}_{question_type}_page{page_num}.png"
                    filepath = subject_output_dir / filename
                    
                    if 'rectangles' in ann and ann['rectangles']:
                        # Multi-rectangle question - merge rectangles
                        merged_image = self.merge_rectangles_to_image(None, ann['rectangles'])
                        if merged_image:
                            merged_image.save(str(filepath))
                            exported_count += 1
                            subject_files.append(filename)
                    else:
                        # Single rectangle question
                        page = self.pdf_doc[ann['page']]
                        x1, y1, x2, y2 = ann['pdf_coords']
                        rect = fitz.Rect(x1, y1, x2, y2)
                        
                        # Crop page to rectangle with high resolution
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                        pix.save(str(filepath))
                        exported_count += 1
                        subject_files.append(filename)
                
                # Save subject-specific metadata
                metadata_file = subject_output_dir / "annotations_metadata.json"
                subject_save_data = {
                    'pdf_metadata': self.pdf_metadata,
                    'pdf_path': self.pdf_doc.name if self.pdf_doc else '',
                    'export_timestamp': export_info['timestamp'],
                    'export_date': export_info['export_date'],
                    'total_annotations': len(annotations),
                    'output_directory': str(subject_output_dir),
                    'subject': subject,
                    'annotations': []
                }
                
                for ann in annotations:
                    # Clean annotation for metadata
                    clean_ann = {k: v for k, v in ann.items() if k not in ['canvas_item']}
                    # Clean rectangles data
                    if 'rectangles' in clean_ann:
                        clean_rectangles = []
                        for rect_data in clean_ann['rectangles']:
                            clean_rect = {k: v for k, v in rect_data.items() if k != 'canvas_item'}
                            clean_rectangles.append(clean_rect)
                        clean_ann['rectangles'] = clean_rectangles
                    
                    # Add generated filename
                    year = ann.get('year', 'unknown')
                    paper = ann.get('paper', 'unknown')
                    language = ann.get('language', 'unknown')
                    question_id = ann['question_id'].replace('/', '_').replace('.', '_')
                    question_type = ann.get('question_type', 'unknown').replace(' ', '_')
                    page_num = ann['page'] + 1
                    
                    clean_ann['exported_filename'] = f"{year}_P{paper}_{language}_{subject}_{question_id}_{question_type}_page{page_num}.png"
                    subject_save_data['annotations'].append(clean_ann)
                
                with open(metadata_file, 'w') as f:
                    json.dump(subject_save_data, f, indent=2)
                
                # Create subject summary report
                summary_file = subject_output_dir / "export_summary.txt"
                with open(summary_file, 'w') as f:
                    f.write(f"JEE Advanced Question Export Summary - {subject}\n")
                    f.write(f"=" * 50 + "\n\n")
                    f.write(f"Export Date: {export_info['export_date']}\n")
                    f.write(f"PDF: Year {self.pdf_metadata.get('year', 'Unknown')}, ")
                    f.write(f"Paper {self.pdf_metadata.get('paper', 'Unknown')}, ")
                    f.write(f"Language: {self.pdf_metadata.get('language', 'Unknown')}\n")
                    f.write(f"Subject: {subject}\n")
                    f.write(f"Total Questions Exported: {len(annotations)}\n\n")
                    
                    # Group by question type
                    question_types = {}
                    for ann in annotations:
                        question_type = ann['question_type']
                        if question_type not in question_types:
                            question_types[question_type] = []
                        question_types[question_type].append(ann)
                    
                    for question_type, anns in question_types.items():
                        f.write(f"{question_type}: {len(anns)} questions\n")
                        for ann in anns:
                            rect_info = f" ({ann.get('rectangle_count', 1)} rectangles)" if ann.get('rectangle_count', 1) > 1 else ""
                            f.write(f"  - {ann['question_id']} (Page {ann['page'] + 1}){rect_info}\n")
                        f.write("\n")
                
                export_info['subjects'][subject] = {
                    'question_count': len(annotations),
                    'files': subject_files,
                    'output_directory': str(subject_output_dir)
                }
            
            # Store export info for undo functionality
            self.last_export_data = export_info.copy()
            self.last_export_data['exported_annotations'] = self.annotations.copy()
            
            # Clear all annotations and reset canvas after successful export
            self.clear_all_annotations()
            
            # Create summary message
            subject_summary = ", ".join([f"{subject}: {info['question_count']}" for subject, info in export_info['subjects'].items()])
            
            self.status_var.set(f"Exported {exported_count} questions to respective subject directories")
            messagebox.showinfo("Export Complete", 
                              f"Successfully exported {exported_count} question images!\n\n"
                              f"Questions by subject:\n{subject_summary}\n\n"
                              f"Each subject exported to its own directory.\n"
                              f"Files: images, metadata.json, summary.txt\n\n"
                              f"Annotations have been cleared. You can now start annotating more questions.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export annotations: {str(e)}")
    
    def undo_last_export(self):
        """Undo the last export operation by deleting exported files and restoring annotations"""
        if not self.last_export_data:
            messagebox.showinfo("Info", "No recent export to undo")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Undo",
            f"This will delete the last exported files and restore {len(self.last_export_data.get('exported_annotations', []))} annotations.\n\n"
            f"Exported on: {self.last_export_data.get('export_date', 'Unknown')}\n"
            f"Subjects: {', '.join(self.last_export_data.get('subjects', {}).keys())}\n\n"
            "Do you want to proceed?"
        )
        
        if not confirm:
            return
        
        try:
            deleted_files = 0
            deleted_subjects = []
            
            # Delete exported files for each subject
            for subject, subject_info in self.last_export_data.get('subjects', {}).items():
                output_dir = Path(subject_info['output_directory'])
                
                if output_dir.exists():
                    # Delete PNG files
                    for filename in subject_info.get('files', []):
                        file_path = output_dir / filename
                        if file_path.exists():
                            file_path.unlink()
                            deleted_files += 1
                    
                    # Delete metadata and summary files
                    metadata_file = output_dir / "annotations_metadata.json"
                    summary_file = output_dir / "export_summary.txt"
                    
                    if metadata_file.exists():
                        metadata_file.unlink()
                    if summary_file.exists():
                        summary_file.unlink()
                    
                    deleted_subjects.append(subject)
            
            # Store the annotations to restore before clearing anything
            annotations_to_restore = self.last_export_data.get('exported_annotations', []).copy()
            
            # Clear current state completely first
            self.clear_all_annotations()
            
            # Restore annotations
            if annotations_to_restore:
                self.annotations = annotations_to_restore
                
                # Restore question counters to the state before export
                # Reset counters first
                self.question_counters = {
                    'MCQ-Single': 0,
                    'MCQ-Multiple': 0,
                    'Numerical': 0,
                    'Matching': 0
                }
                
                for ann in self.annotations:
                    question_type = ann['question_type']
                    question_id = ann['question_id']
                    try:
                        q_num = int(question_id.split('_q')[-1])
                        self.question_counters[question_type] = max(self.question_counters[question_type], q_num)
                    except (ValueError, IndexError):
                        continue
                
                # Ensure we're in the correct state for normal annotation
                self.multi_rectangle_mode = False
                self.current_question_rectangles = []
                self.pending_question_data = None
                
                # Reset UI elements to normal state
                self.add_rectangle_button.config(text="Add Question", command=self.add_single_rectangle_question, state='disabled')
                self.add_another_rect_button.config(state='disabled')
                self.rect_count_var.set("Rectangles: 0")
                
                # Remove complete button if it exists
                if hasattr(self, 'complete_button'):
                    self.complete_button.destroy()
                    delattr(self, 'complete_button')
                
                # Reload current page to restore visual annotations
                if self.pdf_doc:
                    self.load_page()
                
                self.update_annotation_list()
                self.update_next_question_id()
            
            # Clear undo data to prevent multiple undos
            self.last_export_data = None
            
            # Show success message
            messagebox.showinfo("Undo Complete", 
                              f"Successfully undone last export!\n\n"
                              f"Deleted {deleted_files} files from subjects: {', '.join(deleted_subjects)}\n"
                              f"Restored {len(annotations_to_restore)} annotations to the interface.\n\n"
                              f"You can now modify or re-export these questions.")
            
            self.status_var.set(f"Undone last export: restored {len(annotations_to_restore)} annotations")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to undo export: {str(e)}")
            # Reset state on error
            self.multi_rectangle_mode = False
            self.current_question_rectangles = []
            self.pending_question_data = None
            self.add_rectangle_button.config(text="Add Question", command=self.add_single_rectangle_question, state='disabled')
            self.add_another_rect_button.config(state='disabled').showwarning("Warning", "Please set output directory first")
            return
        
        try:
            exported_count = 0
            
            for ann in self.annotations:
                # Create structured filename
                year = ann.get('year', 'unknown')
                paper = ann.get('paper', 'unknown')
                language = ann.get('language', 'unknown')
                subject = ann['subject']
                question_id = ann['question_id'].replace('/', '_').replace('.', '_')
                question_type = ann.get('question_type', 'unknown').replace(' ', '_')
                page_num = ann['page'] + 1
                
                filename = f"{year}_P{paper}_{language}_{subject}_{question_id}_{question_type}_page{page_num}.png"
                filepath = self.current_output_dir / filename
                
                if 'rectangles' in ann and ann['rectangles']:
                    # Multi-rectangle question - merge rectangles
                    merged_image = self.merge_rectangles_to_image(None, ann['rectangles'])
                    if merged_image:
                        merged_image.save(str(filepath))
                        exported_count += 1
                else:
                    # Single rectangle question
                    page = self.pdf_doc[ann['page']]
                    x1, y1, x2, y2 = ann['pdf_coords']
                    rect = fitz.Rect(x1, y1, x2, y2)
                    
                    # Crop page to rectangle with high resolution
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                    pix.save(str(filepath))
                    exported_count += 1
            
            # Save comprehensive metadata
            metadata_file = self.current_output_dir / "annotations_metadata.json"
            save_data = {
                'pdf_metadata': self.pdf_metadata,
                'pdf_path': self.pdf_doc.name if self.pdf_doc else '',
                'export_timestamp': time.time(),
                'export_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_annotations': len(self.annotations),
                'output_directory': str(self.current_output_dir),
                'subject': self.current_subject_var.get(),
                'annotations': []
            }
            
            for ann in self.annotations:
                # Clean annotation for metadata
                clean_ann = {k: v for k, v in ann.items() if k not in ['canvas_item']}
                # Clean rectangles data
                if 'rectangles' in clean_ann:
                    clean_rectangles = []
                    for rect_data in clean_ann['rectangles']:
                        clean_rect = {k: v for k, v in rect_data.items() if k != 'canvas_item'}
                        clean_rectangles.append(clean_rect)
                    clean_ann['rectangles'] = clean_rectangles
                
                # Add generated filename
                year = ann.get('year', 'unknown')
                paper = ann.get('paper', 'unknown')
                language = ann.get('language', 'unknown')
                subject = ann['subject']
                question_id = ann['question_id'].replace('/', '_').replace('.', '_')
                question_type = ann.get('question_type', 'unknown').replace(' ', '_')
                page_num = ann['page'] + 1
                
                clean_ann['exported_filename'] = f"{year}_P{paper}_{language}_{subject}_{question_id}_{question_type}_page{page_num}.png"
                save_data['annotations'].append(clean_ann)
            
            with open(metadata_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            # Create summary report
            summary_file = self.current_output_dir / "export_summary.txt"
            with open(summary_file, 'w') as f:
                f.write(f"JEE Advanced Question Export Summary\n")
                f.write(f"=" * 40 + "\n\n")
                f.write(f"Export Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"PDF: Year {self.pdf_metadata.get('year', 'Unknown')}, ")
                f.write(f"Paper {self.pdf_metadata.get('paper', 'Unknown')}, ")
                f.write(f"Language: {self.pdf_metadata.get('language', 'Unknown')}\n")
                f.write(f"Subject: {self.current_subject_var.get()}\n")
                f.write(f"Total Questions Exported: {exported_count}\n\n")
                
                # Group by question type
                question_types = {}
                for ann in self.annotations:
                    question_type = ann['question_type']
                    if question_type not in question_types:
                        question_types[question_type] = []
                    question_types[question_type].append(ann)
                
                for question_type, anns in question_types.items():
                    f.write(f"{question_type}: {len(anns)} questions\n")
                    for ann in anns:
                        rect_info = f" ({ann.get('rectangle_count', 1)} rectangles)" if ann.get('rectangle_count', 1) > 1 else ""
                        f.write(f"  - {ann['question_id']} (Page {ann['page'] + 1}){rect_info}\n")
                    f.write("\n")
            
            # Clear all annotations and reset canvas after successful export
            self.clear_all_annotations()
            
            self.status_var.set(f"Exported {exported_count} question images to {self.current_output_dir}")
            messagebox.showinfo("Export Complete", 
                              f"Successfully exported {exported_count} question images for {self.current_subject_var.get()}\n\n"
                              f"Directory: {self.current_output_dir}\n"
                              f"Files: images, metadata.json, summary.txt\n\n"
                              f"Annotations have been cleared. You can now start annotating the next subject.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export annotations: {str(e)}")
    
    def clear_all_annotations(self):
        """Clear all annotations from memory and canvas"""
        # Remove all annotation rectangles from canvas
        for ann in self.annotations:
            if 'rectangles' in ann:
                # Multi-rectangle question
                for rect_data in ann['rectangles']:
                    if 'canvas_item' in rect_data:
                        self.canvas.delete(rect_data['canvas_item'])
            elif 'canvas_item' in ann:
                # Single rectangle question
                self.canvas.delete(ann['canvas_item'])
        
        # Clear annotations list
        self.annotations = []
        
        # Reset multi-rectangle state
        self.current_question_rectangles = []
        self.pending_question_data = None
        self.add_rectangle_button.config(state='disabled')
        self.add_another_rect_button.config(state='disabled')
        self.rect_count_var.set("Rectangles: 0")
        
        # Reset question counters
        self.question_counters = {
            'MCQ-Single': 0,
            'MCQ-Multiple': 0,
            'Numerical': 0,
            'Matching': 0
        }
        
        # Initialize session start time if not set
        if not self.progress_data.get('session_start_time'):
            self.progress_data['session_start_time'] = time.time()
        
        # Update UI
        self.update_annotation_list()
        self.update_next_question_id()
        
        self.status_var.set("All annotations cleared. Ready for new subject annotations.")
    
    def run(self):
        self.root.mainloop()

def main():
    """
    Main function to run the JEE Advanced PDF Question Annotator
    
    Required packages:
    pip install PyMuPDF pillow requests
    """
    try:
        app = PDFQuestionAnnotator()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()