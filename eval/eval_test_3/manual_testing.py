# Tool for human verification of wrong answers
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageTk
import io

class ResponseEvaluatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Response Evaluation Tool")
        self.root.geometry("1400x900")
        
        # Data storage
        self.questions = []
        self.current_index = 0
        self.evaluations = {}
        self.evaluation_file = None
        self.current_image = None
        self.current_photo = None
        self.questions_file_path = None
        
        # Image settings
        self.image_base_path = "final_dataset\images"
        
        # Create GUI components
        self.create_widgets()
        self.show_startup_dialog()
        
    def show_startup_dialog(self):
        """Show startup dialog to choose between loading new questions or resuming"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Questions")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Manual Response Evaluation Tool", 
                 font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        ttk.Label(main_frame, text="Choose how to start:", 
                 font=('Arial', 12)).pack(pady=(0, 15))
        
        # Option 1: Load new questions
        new_frame = ttk.LabelFrame(main_frame, text="Start New Evaluation", padding="10")
        new_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(new_frame, text="Load a fresh set of questions for evaluation").pack(anchor=tk.W)
        ttk.Button(new_frame, text="Load New Questions", 
                  command=lambda: self.startup_choice("new", dialog)).pack(pady=(5, 0))
        
        # Option 2: Resume from checkpoint
        resume_frame = ttk.LabelFrame(main_frame, text="Resume Previous Session", padding="10")
        resume_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(resume_frame, text="Continue from a previously saved evaluation session").pack(anchor=tk.W)
        ttk.Button(resume_frame, text="Resume from Checkpoint", 
                  command=lambda: self.startup_choice("resume", dialog)).pack(pady=(5, 0))
        
        # Option 3: Demo mode
        demo_frame = ttk.LabelFrame(main_frame, text="Demo Mode", padding="10")
        demo_frame.pack(fill=tk.X)
        
        ttk.Label(demo_frame, text="Try to load default questions file if available").pack(anchor=tk.W)
        ttk.Button(demo_frame, text="Try Default File", 
                  command=lambda: self.startup_choice("demo", dialog)).pack(pady=(5, 0))
        
    def startup_choice(self, choice, dialog):
        """Handle startup choice"""
        dialog.destroy()
        
        if choice == "new":
            self.load_new_questions()
        elif choice == "resume":
            self.resume_from_checkpoint()
        elif choice == "demo":
            self.load_demo_questions()
    
    def load_demo_questions(self):
        """Try to load default questions file"""
        default_file = "selected_questions_for_manual_review.json"
        if Path(default_file).exists():
            self.load_questions_from_file(default_file)
        else:
            messagebox.showinfo("Demo Mode", 
                               f"Default file '{default_file}' not found.\nPlease select a questions file.")
            self.load_new_questions()
    
    def load_new_questions(self):
        """Load a new set of questions"""
        file_path = filedialog.askopenfilename(
            title="Select Questions JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.load_questions_from_file(file_path)
    
    def resume_from_checkpoint(self):
        """Resume from a previously saved evaluation session"""
        file_path = filedialog.askopenfilename(
            title="Select Evaluation Checkpoint File",
            filetypes=[("JSON files", "manual_evaluations_*.json"), ("All JSON files", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
            
            # Extract metadata to find original questions file
            checkpoint_info = eval_data.get('checkpoint_info', {})
            original_questions_file = checkpoint_info.get('original_questions_file')
            
            if not original_questions_file or not Path(original_questions_file).exists():
                # Ask user to locate the original questions file
                messagebox.showinfo("Locate Questions File", 
                                   "Please select the original questions file for this evaluation session.")
                questions_file = filedialog.askopenfilename(
                    title="Select Original Questions JSON File",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if not questions_file:
                    return
                original_questions_file = questions_file
            
            # Load questions
            self.load_questions_from_file(original_questions_file)
            
            # Load existing evaluations
            self.evaluations = eval_data.get('evaluations', {})
            self.evaluation_file = file_path
            
            # Find the next unevaluated question
            self.find_next_unevaluated_question()
            
            self.status_bar.config(text=f"Resumed from checkpoint: {len(self.evaluations)}/{len(self.questions)} completed")
            messagebox.showinfo("Checkpoint Loaded", 
                               f"Resumed evaluation session!\n"
                               f"Progress: {len(self.evaluations)}/{len(self.questions)} questions evaluated\n"
                               f"Starting from question {self.current_index + 1}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load checkpoint: {str(e)}")
            self.load_new_questions()
    
    def find_next_unevaluated_question(self):
        """Find the next question that hasn't been evaluated"""
        for i, question in enumerate(self.questions):
            unique_question_id = self.get_unique_question_id(question)
            if unique_question_id not in self.evaluations:
                self.current_index = i
                self.show_question()
                return
        
        # All questions evaluated - go to first question
        self.current_index = 0
        self.show_question()
        messagebox.showinfo("All Evaluated", "All questions have been evaluated! You can review or modify existing evaluations.")
    
    def get_unique_question_id(self, question):
        """Generate unique question ID"""
        original_question_id = question.get('question_id', 'unknown')
        subject = question.get('subject', 'unknown')
        language = question.get('language', 'unknown')
        year = question.get('year', 'unknown')
        paper = question.get('paper', 'unknown')
        return f"{original_question_id}_{subject}_{language}_{year}_{paper}"
    
    def load_questions_from_file(self, file_path):
        """Load questions from specified file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.questions = data.get('selected_questions', [])
            
            if not self.questions:
                messagebox.showerror("Error", "No questions found in the file")
                return
            
            self.questions_file_path = file_path
            
            # Initialize new evaluation file
            self.evaluation_file = f"manual_evaluations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.evaluations = {}
            
            # Update progress bar
            self.progress_bar['maximum'] = len(self.questions)
            
            # Show first question
            self.current_index = 0
            self.show_question()
            
            self.status_bar.config(text=f"Loaded {len(self.questions)} questions from {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load questions: {str(e)}")

    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title and progress
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.title_label = ttk.Label(title_frame, text="Manual Response Evaluation", 
                                   font=('Arial', 16, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        
        self.progress_label = ttk.Label(title_frame, text="Question 0/0", 
                                      font=('Arial', 12))
        self.progress_label.pack(side=tk.RIGHT)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Left panel - Question info and navigation
        left_frame = ttk.LabelFrame(main_frame, text="Question Information", padding="10")
        left_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(4, weight=1)
        
        # Question metadata
        self.info_text = scrolledtext.ScrolledText(left_frame, height=6, width=35, 
                                                 font=('Consolas', 10))
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Correct answer display
        answer_frame = ttk.LabelFrame(left_frame, text="Correct Answer", padding="5")
        answer_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        answer_frame.columnconfigure(0, weight=1)
        
        self.correct_answer_text = tk.Text(answer_frame, height=3, width=35, 
                                         font=('Arial', 11, 'bold'), 
                                         bg='#f0f8ff', fg='#006400',
                                         wrap=tk.WORD, relief=tk.FLAT)
        answer_scrollbar = ttk.Scrollbar(answer_frame, orient="vertical", command=self.correct_answer_text.yview)
        self.correct_answer_text.configure(yscrollcommand=answer_scrollbar.set)
        
        self.correct_answer_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        answer_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Copy correct answer button
        ttk.Button(answer_frame, text="Copy Correct Answer", 
                  command=self.copy_correct_answer).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Navigation buttons
        nav_frame = ttk.Frame(left_frame)
        nav_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.prev_button = ttk.Button(nav_frame, text="← Previous", command=self.prev_question)
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.next_button = ttk.Button(nav_frame, text="Next →", command=self.next_question)
        self.next_button.pack(side=tk.LEFT)
        
        # Jump to question
        jump_frame = ttk.Frame(left_frame)
        jump_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(jump_frame, text="Jump to:").pack(side=tk.LEFT)
        self.jump_var = tk.StringVar()
        jump_entry = ttk.Entry(jump_frame, textvariable=self.jump_var, width=8)
        jump_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(jump_frame, text="Go", command=self.jump_to_question).pack(side=tk.LEFT)
        
        # Navigation shortcuts
        shortcut_frame = ttk.Frame(left_frame)
        shortcut_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 10))
        
        ttk.Button(shortcut_frame, text="Next Unevaluated", 
                  command=self.goto_next_unevaluated).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(shortcut_frame, text="Prev Unevaluated", 
                  command=self.goto_prev_unevaluated).pack(side=tk.LEFT)
        
        # Evaluation status
        self.status_label = ttk.Label(left_frame, text="Not evaluated", 
                                    foreground="red", font=('Arial', 10, 'bold'))
        self.status_label.grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        
        # Middle panel - Image display
        image_frame = ttk.LabelFrame(main_frame, text="Question Image", padding="10")
        image_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # Image display with scrollbars
        image_container = ttk.Frame(image_frame)
        image_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        image_container.columnconfigure(0, weight=1)
        image_container.rowconfigure(0, weight=1)
        
        # Create canvas for image with scrollbars
        self.image_canvas = tk.Canvas(image_container, bg='white', width=400, height=500)
        v_scrollbar = ttk.Scrollbar(image_container, orient="vertical", command=self.image_canvas.yview)
        h_scrollbar = ttk.Scrollbar(image_container, orient="horizontal", command=self.image_canvas.xview)
        self.image_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Image control buttons
        image_controls = ttk.Frame(image_frame)
        image_controls.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # First row of controls
        controls_row1 = ttk.Frame(image_controls)
        controls_row1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(controls_row1, text="Copy Image", 
                  command=self.copy_image_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_row1, text="Copy Path", 
                  command=self.copy_image_path).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_row1, text="Open in Explorer", 
                  command=self.open_image_in_explorer).pack(side=tk.LEFT, padx=(0, 10))
        
        # Second row of controls
        controls_row2 = ttk.Frame(image_controls)
        controls_row2.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(controls_row2, text="Zoom In", 
                  command=self.zoom_in).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_row2, text="Zoom Out", 
                  command=self.zoom_out).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_row2, text="Reset Zoom", 
                  command=self.reset_zoom).pack(side=tk.LEFT)
        
        self.zoom_label = ttk.Label(controls_row2, text="100%")
        self.zoom_label.pack(side=tk.RIGHT)
        
        # Right panel - Response and evaluation
        right_frame = ttk.LabelFrame(main_frame, text="Response & Evaluation", padding="10")
        right_frame.grid(row=2, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # Response text (scrollable and selectable)
        response_frame = ttk.LabelFrame(right_frame, text="Model Response", padding="5")
        response_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        self.response_text = scrolledtext.ScrolledText(response_frame, height=10, width=50,
                                                     font=('Arial', 11), wrap=tk.WORD)
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        # Response control button
        response_controls = ttk.Frame(response_frame)
        response_controls.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(response_controls, text="Copy Response to Clipboard", 
                  command=self.copy_response_to_clipboard).pack(side=tk.LEFT)
        
        # Evaluation frame
        eval_frame = ttk.LabelFrame(right_frame, text="Error Analysis", padding="10")
        eval_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        eval_frame.columnconfigure(1, weight=1)
        
        # Error checkboxes
        self.conceptual_var = tk.BooleanVar()
        self.grounding_var = tk.BooleanVar()
        self.computation_var = tk.BooleanVar()
        self.instruction_var = tk.BooleanVar()
        
        ttk.Checkbutton(eval_frame, text="Conceptual errors", 
                       variable=self.conceptual_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(eval_frame, text="(Inability to use correct concepts)", 
                 font=('Arial', 9), foreground="gray").grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Checkbutton(eval_frame, text="Grounding errors", 
                       variable=self.grounding_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(eval_frame, text="(Wrong formulas, incorrect modeling, wrong equation setup)", 
                 font=('Arial', 9), foreground="gray").grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Checkbutton(eval_frame, text="Computation errors", 
                       variable=self.computation_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Label(eval_frame, text="(Algebraic manipulation, arithmetic errors)", 
                 font=('Arial', 9), foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Checkbutton(eval_frame, text="Instruction following errors", 
                       variable=self.instruction_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Label(eval_frame, text="(Not following format, units, precision, or answer requirements)", 
                 font=('Arial', 9), foreground="gray").grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        # Additional notes - FIXED: Ensure proper configuration
        notes_frame = ttk.LabelFrame(right_frame, text="Additional Notes", padding="5")
        notes_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        
        # Use ScrolledText instead of Text with manual scrollbar for better reliability
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=4, width=50,
                                                   font=('Arial', 10), wrap=tk.WORD,
                                                   state=tk.NORMAL)  # Explicitly set to NORMAL
        self.notes_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        # Add a test to verify the notes field is working
        test_button = ttk.Button(notes_frame, text="Test Notes Field", 
                                command=self.test_notes_field)
        test_button.grid(row=1, column=0, sticky=tk.W)
        
        # Action buttons
        action_frame = ttk.Frame(right_frame)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(action_frame, text="Save Evaluation", 
                  command=self.save_evaluation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Clear Evaluation", 
                  command=self.clear_evaluation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Export Results", 
                  command=self.export_results).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Image zoom settings
        self.zoom_factor = 1.0
        self.original_image = None
    
    def test_notes_field(self):
        """Test function to verify notes field is working"""
        try:
            # Clear and insert test text
            self.notes_text.delete(1.0, tk.END)
            self.notes_text.insert(1.0, "Test text - notes field is working!")
            self.notes_text.focus_set()  # Set focus to the notes field
            messagebox.showinfo("Test", "Notes field test completed. You should see test text in the notes area.")
        except Exception as e:
            messagebox.showerror("Error", f"Notes field test failed: {str(e)}")
    
    def goto_next_unevaluated(self):
        """Jump to the next unevaluated question"""
        start_index = self.current_index + 1
        for i in range(start_index, len(self.questions)):
            question = self.questions[i]
            unique_question_id = self.get_unique_question_id(question)
            if unique_question_id not in self.evaluations:
                self.current_index = i
                self.show_question()
                return
        
        # Wrap around to beginning
        for i in range(0, self.current_index):
            question = self.questions[i]
            unique_question_id = self.get_unique_question_id(question)
            if unique_question_id not in self.evaluations:
                self.current_index = i
                self.show_question()
                return
        
        messagebox.showinfo("All Evaluated", "All questions have been evaluated!")
    
    def goto_prev_unevaluated(self):
        """Jump to the previous unevaluated question"""
        start_index = self.current_index - 1
        for i in range(start_index, -1, -1):
            question = self.questions[i]
            unique_question_id = self.get_unique_question_id(question)
            if unique_question_id not in self.evaluations:
                self.current_index = i
                self.show_question()
                return
        
        # Wrap around to end
        for i in range(len(self.questions) - 1, self.current_index, -1):
            question = self.questions[i]
            unique_question_id = self.get_unique_question_id(question)
            if unique_question_id not in self.evaluations:
                self.current_index = i
                self.show_question()
                return
        
        messagebox.showinfo("All Evaluated", "All questions have been evaluated!")

    def construct_image_path(self, image_filename):
        """Construct the full image path from filename - with enhanced error handling"""
        if not image_filename or image_filename == 'N/A':
            return None
            
        try:
            # Parse filename: "2020_P1_English_Chemistry_Numerical_q1_Numerical_page18.png"
            parts = image_filename.split('_')
            if len(parts) < 4:
                print(f"Invalid filename format: {image_filename} (expected at least 4 parts)")
                return None
                
            year = parts[0]  # "2020"
            paper = parts[1]  # "P1" or "P2"
            language = parts[2]  # "English" or "Hindi"
            subject = parts[3]  # "Physics", "Chemistry", "Mathematics"
            
            # Validate components
            if not year.isdigit():
                print(f"Invalid year in filename: {year}")
                return None
                
            if paper not in ['P1', 'P2']:
                print(f"Invalid paper in filename: {paper}")
                return None
                
            if language not in ['English', 'Hindi']:
                print(f"Invalid language in filename: {language}")
                return None
                
            if subject not in ['Physics', 'Chemistry', 'Mathematics']:
                print(f"Invalid subject in filename: {subject}")
                return None
            
            # Construct path
            image_path = Path(self.image_base_path) / year / paper / language / subject / image_filename
            
            print(f"Constructed path: {image_path}")
            return str(image_path) if image_path.exists() else None
            
        except Exception as e:
            print(f"Error constructing image path for {image_filename}: {e}")
            return None
    
    def load_and_display_image(self, image_filename):
        """Load and display the question image - with robust error handling"""
        try:
            # Handle missing or invalid filename
            if not image_filename or image_filename == 'N/A':
                self.display_no_image("No image filename provided")
                return
            
            # Construct image path
            image_path = self.construct_image_path(image_filename)
            
            if not image_path:
                self.display_no_image(f"Could not construct path for: {image_filename}")
                return
                
            if not Path(image_path).exists():
                self.display_no_image(f"Image file not found:\n{image_path}")
                return
            
            # Try to load image
            try:
                self.original_image = Image.open(image_path)
                self.zoom_factor = 1.0
                self.display_image()
                print(f"Successfully loaded image: {image_filename}")
                
            except Exception as img_error:
                self.display_no_image(f"Error loading image:\n{str(img_error)}")
                print(f"Image loading error for {image_filename}: {img_error}")
                
        except Exception as e:
            self.display_no_image(f"Unexpected error:\n{str(e)}")
            print(f"Unexpected error in load_and_display_image: {e}")
    
    def display_no_image(self, message):
        """Display a message when image cannot be loaded"""
        self.image_canvas.delete("all")
        self.image_canvas.create_text(
            200, 250, text=message, 
            font=('Arial', 12), fill='red', width=350, justify=tk.CENTER
        )
        self.current_image = None
        self.original_image = None
        self.zoom_label.config(text="N/A")
    
    def display_image(self):
        """Display the current image with current zoom factor"""
        if not self.original_image:
            return
            
        try:
            # Calculate new size
            width = int(self.original_image.width * self.zoom_factor)
            height = int(self.original_image.height * self.zoom_factor)
            
            # Resize image
            resized_image = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_photo = ImageTk.PhotoImage(resized_image)
            
            # Clear canvas and display image
            self.image_canvas.delete("all")
            self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_photo)
            
            # Update scroll region
            self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
            
            # Update zoom label
            self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")
            
        except Exception as e:
            print(f"Error displaying image: {e}")
    
    def zoom_in(self):
        """Zoom in on the image"""
        if self.original_image:
            self.zoom_factor = min(self.zoom_factor * 1.2, 5.0)  # Max 500% zoom
            self.display_image()
    
    def zoom_out(self):
        """Zoom out on the image"""
        if self.original_image:
            self.zoom_factor = max(self.zoom_factor / 1.2, 0.1)  # Min 10% zoom
            self.display_image()
    
    def reset_zoom(self):
        """Reset zoom to 100%"""
        if self.original_image:
            self.zoom_factor = 1.0
            self.display_image()
    
    def copy_correct_answer(self):
        """Copy the correct answer to clipboard"""
        try:
            if not self.questions:
                return
                
            current_question = self.questions[self.current_index]
            correct_answer = current_question.get('correct_answer', 'N/A')
            
            if correct_answer == 'N/A':
                messagebox.showwarning("Warning", "No correct answer to copy")
                return
            
            self.root.clipboard_clear()
            self.root.clipboard_append(str(correct_answer))
            self.root.update()
            
            self.status_bar.config(text="Correct answer copied to clipboard")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy correct answer: {str(e)}")

    def copy_response_to_clipboard(self):
        """Copy the current model response to clipboard"""
        try:
            response_text = self.response_text.get(1.0, tk.END).strip()
            
            if not response_text or response_text == "No response available":
                messagebox.showwarning("Warning", "No response to copy")
                return
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(response_text)
            self.root.update()  # Ensure clipboard is updated
            
            self.status_bar.config(text="Model response copied to clipboard")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy response: {str(e)}")

    def copy_image_to_clipboard(self):
        """Copy the current image to clipboard using multiple methods"""
        if not self.original_image:
            messagebox.showwarning("Warning", "No image to copy")
            return
        
        success = False
        error_msg = ""
        
        # Method 1: Try win32clipboard (Windows)
        try:
            import win32clipboard
            from PIL import ImageWin
            import win32con
            
            # Convert image to BMP format for clipboard
            output = io.BytesIO()
            self.original_image.save(output, format='BMP')
            data = output.getvalue()[14:]  # Remove BMP header for clipboard
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            success = True
            self.status_bar.config(text="Image copied to clipboard (Method 1)")
            
        except ImportError:
            error_msg = "win32clipboard not available. "
        except Exception as e:
            error_msg = f"win32clipboard failed: {str(e)}. "
        
        # Method 2: Try using subprocess and PowerShell (Windows)
        if not success:
            try:
                import subprocess
                import tempfile
                
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
                import os
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                if result.returncode == 0:
                    success = True
                    self.status_bar.config(text="Image copied to clipboard (PowerShell)")
                else:
                    error_msg += f"PowerShell failed: {result.stderr}. "
                    
            except Exception as e:
                error_msg += f"PowerShell method failed: {str(e)}. "
        
        # Method 3: Fallback - copy image path
        if not success:
            try:
                current_question = self.questions[self.current_index]
                image_filename = current_question.get('image_filename', '')
                image_path = self.construct_image_path(image_filename)
                
                if image_path:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(image_path)
                    success = True
                    self.status_bar.config(text="Image path copied to clipboard (fallback)")
                else:
                    error_msg += "Image path not found."
                    
            except Exception as e:
                error_msg += f"Path copy failed: {str(e)}"
        
        if not success:
            messagebox.showerror("Error", f"Failed to copy image to clipboard.\n\nErrors: {error_msg}\n\nTry using 'Copy Path' or 'Open in Explorer' buttons instead.")

    def copy_image_path(self):
        """Copy the image file path to clipboard"""
        try:
            current_question = self.questions[self.current_index]
            image_filename = current_question.get('image_filename', '')
            image_path = self.construct_image_path(image_filename)
            
            if not image_path:
                messagebox.showwarning("Warning", "Image path not found")
                return
            
            self.root.clipboard_clear()
            self.root.clipboard_append(image_path)
            self.root.update()
            
            self.status_bar.config(text="Image path copied to clipboard")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy image path: {str(e)}")

    def open_image_in_explorer(self):
        """Open the image file in Windows Explorer"""
        try:
            current_question = self.questions[self.current_index]
            image_filename = current_question.get('image_filename', '')
            image_path = self.construct_image_path(image_filename)
            
            if not image_path:
                messagebox.showwarning("Warning", "Image path not found")
                return
            
            import subprocess
            import sys
            
            if sys.platform == "win32":
                # Windows - open in Explorer and select file
                subprocess.run(['explorer', '/select,', image_path])
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(['open', '-R', image_path])
            else:
                # Linux
                subprocess.run(['xdg-open', str(Path(image_path).parent)])
            
            self.status_bar.config(text="Image opened in file explorer")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image in explorer: {str(e)}")

    def show_question(self):
        """Display current question - purely JSON-based navigation"""
        if not self.questions or self.current_index >= len(self.questions):
            print(f"Invalid navigation: current_index={self.current_index}, total_questions={len(self.questions)}")
            return
        
        try:
            question = self.questions[self.current_index]
            
            # Create unique question ID by combining original ID with subject and language
            unique_question_id = self.get_unique_question_id(question)
            
            # Update progress
            self.progress_label.config(text=f"Question {self.current_index + 1}/{len(self.questions)}")
            self.progress_bar['value'] = self.current_index + 1
            
            # Show question info
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            
            # Safe get with fallback for missing fields
            original_question_id = question.get('question_id', 'unknown')
            subject = question.get('subject', 'unknown')
            language = question.get('language', 'unknown')
            model_name = question.get('model_name', 'N/A')
            question_type = question.get('question_type', 'N/A')
            year = question.get('year', 'N/A')
            paper = question.get('paper', 'N/A')
            predicted_answer = question.get('predicted_answer', 'N/A')
            is_correct = question.get('is_correct', 'N/A')
            image_filename = question.get('image_filename', 'N/A')
            
            # Handle inference time safely
            try:
                inference_time = float(question.get('inference_time', 0))
                inference_time_str = f"{inference_time:.2f}s"
            except (ValueError, TypeError):
                inference_time_str = "N/A"
            
            info = f"""Question ID: {original_question_id}
Unique ID: {unique_question_id}
Model: {model_name}
Subject: {subject}
Language: {language}
Question Type: {question_type}
Year: {year}
Paper: {paper}

Predicted Answer: {predicted_answer}
Is Correct: {is_correct}
Inference Time: {inference_time_str}

Image: {image_filename}"""
            
            self.info_text.insert(1.0, info)
            self.info_text.config(state=tk.DISABLED)
            
            # Display correct answer
            self.correct_answer_text.config(state=tk.NORMAL)
            self.correct_answer_text.delete(1.0, tk.END)
            correct_answer = question.get('correct_answer', 'N/A')
            self.correct_answer_text.insert(1.0, str(correct_answer))
            self.correct_answer_text.config(state=tk.DISABLED)
            
            # Load and display image (with error handling)
            self.load_and_display_image(image_filename)
            
            # Show response
            self.response_text.delete(1.0, tk.END)
            response = question.get('full_response', 'No response available')
            self.response_text.insert(1.0, str(response))
            
            # Load existing evaluation if available (using unique question ID)
            if unique_question_id in self.evaluations:
                eval_data = self.evaluations[unique_question_id]
                self.conceptual_var.set(eval_data.get('conceptual_errors', False))
                self.grounding_var.set(eval_data.get('grounding_errors', False))
                self.computation_var.set(eval_data.get('computation_errors', False))
                self.instruction_var.set(eval_data.get('instruction_errors', False))
                
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.insert(1.0, eval_data.get('notes', ''))
                
                self.status_label.config(text="Evaluated ✓", foreground="green")
            else:
                self.clear_evaluation()
            
            # Update navigation buttons based on JSON array bounds
            self.prev_button.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
            self.next_button.config(state=tk.NORMAL if self.current_index < len(self.questions) - 1 else tk.DISABLED)
            
            # Update status bar with debug info
            evaluation_status = "✓" if unique_question_id in self.evaluations else "✗"
            self.status_bar.config(text=f"Question {self.current_index + 1}/{len(self.questions)} [{evaluation_status}] - ID: {unique_question_id}")
            
        except Exception as e:
            print(f"Error in show_question: {e}")
            messagebox.showerror("Error", f"Failed to display question {self.current_index + 1}: {str(e)}")
            # Try to recover by going to a safe index
            if self.current_index > 0:
                self.current_index = 0
                self.show_question()
    
    def prev_question(self):
        """Go to previous question - JSON-based navigation"""
        if self.current_index > 0:
            print(f"Moving from question {self.current_index + 1} to {self.current_index}")
            self.current_index -= 1
            self.show_question()
        else:
            print("Already at first question")
    
    def next_question(self):
        """Go to next question - JSON-based navigation"""
        if self.current_index < len(self.questions) - 1:
            print(f"Moving from question {self.current_index + 1} to {self.current_index + 2}")
            self.current_index += 1
            self.show_question()
        else:
            print(f"Already at last question ({len(self.questions)})")
            messagebox.showinfo("End Reached", f"You've reached the last question ({len(self.questions)})!")
    
    def jump_to_question(self):
        """Jump to specific question number - JSON-based navigation"""
        try:
            question_num = int(self.jump_var.get())
            if 1 <= question_num <= len(self.questions):
                print(f"Jumping from question {self.current_index + 1} to {question_num}")
                self.current_index = question_num - 1
                self.show_question()
                self.jump_var.set("")
            else:
                messagebox.showerror("Error", f"Question number must be between 1 and {len(self.questions)}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid question number")
    
    def save_evaluation(self):
        """Save current evaluation with enhanced checkpoint info"""
        if not self.questions:
            return
        
        question = self.questions[self.current_index]
        unique_question_id = self.get_unique_question_id(question)
        
        # Collect evaluation data
        evaluation = {
            'unique_question_id': unique_question_id,
            'original_question_id': question.get('question_id', 'unknown'),
            'model_name': question.get('model_name', ''),
            'conceptual_errors': self.conceptual_var.get(),
            'grounding_errors': self.grounding_var.get(),
            'computation_errors': self.computation_var.get(),
            'instruction_errors': self.instruction_var.get(),
            'notes': self.notes_text.get(1.0, tk.END).strip(),
            'evaluation_timestamp': datetime.now().isoformat(),
            'question_metadata': {
                'subject': question.get('subject', ''),
                'language': question.get('language', ''),
                'question_type': question.get('question_type', ''),
                'is_correct': question.get('is_correct', False),
                'image_filename': question.get('image_filename', ''),
                'year': question.get('year', ''),
                'paper': question.get('paper', ''),
                'correct_answer': question.get('correct_answer', ''),
                'predicted_answer': question.get('predicted_answer', '')
            }
        }
        
        # Store evaluation using unique question ID
        self.evaluations[unique_question_id] = evaluation
        
        # Save to file with enhanced checkpoint information
        try:
            eval_data = {
                'checkpoint_info': {
                    'original_questions_file': self.questions_file_path,
                    'total_questions': len(self.questions),
                    'evaluated_questions': len(self.evaluations),
                    'completion_percentage': round((len(self.evaluations) / len(self.questions)) * 100, 1),
                    'last_updated': datetime.now().isoformat(),
                    'current_question_index': self.current_index,
                    'note': 'question_ids are unique combinations of original_question_id + subject + language + year + paper'
                },
                'evaluation_summary': {
                    'total_errors': sum(1 for eval_data in self.evaluations.values() 
                                      if any([eval_data.get('conceptual_errors'), 
                                             eval_data.get('grounding_errors'), 
                                             eval_data.get('computation_errors'),
                                             eval_data.get('instruction_errors')])),
                    'conceptual_errors': sum(1 for eval_data in self.evaluations.values() 
                                           if eval_data.get('conceptual_errors')),
                    'grounding_errors': sum(1 for eval_data in self.evaluations.values() 
                                          if eval_data.get('grounding_errors')),
                    'computation_errors': sum(1 for eval_data in self.evaluations.values() 
                                            if eval_data.get('computation_errors')),
                    'instruction_errors': sum(1 for eval_data in self.evaluations.values() 
                                            if eval_data.get('instruction_errors')),
                    'questions_with_notes': sum(1 for eval_data in self.evaluations.values() 
                                               if eval_data.get('notes', '').strip()),
                },
                'evaluations': self.evaluations
            }
            
            with open(self.evaluation_file, 'w', encoding='utf-8') as f:
                json.dump(eval_data, f, indent=2, ensure_ascii=False)
            
            self.status_label.config(text="Evaluated ✓", foreground="green")
            completion = round((len(self.evaluations) / len(self.questions)) * 100, 1)
            self.status_bar.config(text=f"Evaluation saved ({len(self.evaluations)}/{len(self.questions)} - {completion}% complete)")
            
            print(f"Saved evaluation for unique ID: {unique_question_id}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save evaluation: {str(e)}")
    
    def clear_evaluation(self):
        """Clear current evaluation"""
        self.conceptual_var.set(False)
        self.grounding_var.set(False)
        self.computation_var.set(False)
        self.instruction_var.set(False)
        self.notes_text.delete(1.0, tk.END)
        self.status_label.config(text="Not evaluated", foreground="red")
    
    def export_results(self):
        """Export evaluation results to CSV"""
        if not self.evaluations:
            messagebox.showwarning("Warning", "No evaluations to export")
            return
        
        try:
            import pandas as pd
            
            # Convert evaluations to DataFrame
            eval_list = []
            for unique_question_id, eval_data in self.evaluations.items():
                row = {
                    'unique_question_id': unique_question_id,
                    'original_question_id': eval_data.get('original_question_id', ''),
                    'model_name': eval_data.get('model_name', ''),
                    'subject': eval_data.get('question_metadata', {}).get('subject', ''),
                    'language': eval_data.get('question_metadata', {}).get('language', ''),
                    'question_type': eval_data.get('question_metadata', {}).get('question_type', ''),
                    'year': eval_data.get('question_metadata', {}).get('year', ''),
                    'paper': eval_data.get('question_metadata', {}).get('paper', ''),
                    'correct_answer': eval_data.get('question_metadata', {}).get('correct_answer', ''),
                    'predicted_answer': eval_data.get('question_metadata', {}).get('predicted_answer', ''),
                    'was_correct': eval_data.get('question_metadata', {}).get('is_correct', False),
                    'conceptual_errors': eval_data.get('conceptual_errors', False),
                    'grounding_errors': eval_data.get('grounding_errors', False),
                    'computation_errors': eval_data.get('computation_errors', False),
                    'instruction_errors': eval_data.get('instruction_errors', False),
                    'total_errors': sum([
                        eval_data.get('conceptual_errors', False),
                        eval_data.get('grounding_errors', False),
                        eval_data.get('computation_errors', False),
                        eval_data.get('instruction_errors', False)
                    ]),
                    'notes': eval_data.get('notes', ''),
                    'evaluation_timestamp': eval_data.get('evaluation_timestamp', ''),
                    'image_filename': eval_data.get('question_metadata', {}).get('image_filename', '')
                }
                eval_list.append(row)
            
            df = pd.DataFrame(eval_list)
            
            # Save to CSV
            output_file = f"manual_evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False)
            
            messagebox.showinfo("Success", f"Results exported to {output_file}")
            
        except ImportError:
            messagebox.showerror("Error", "pandas is required for CSV export. Install with: pip install pandas")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {str(e)}")

def main():
    root = tk.Tk()
    app = ResponseEvaluatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()