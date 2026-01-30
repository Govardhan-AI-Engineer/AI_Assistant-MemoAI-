"""
Simple GUI for transcription with file/URL selection, language selection, and translation
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional, Dict, List
import threading
from src.transcription import TranscriptionService
from src.translation.integration import TranscriptionTranslationIntegration
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration
from src.translation import TranslationGranularity
from src.core.languages import Languages
from src.transcription.url_handler import URLHandler
from src.core.config import Config
from src.core.exceptions import TranscriptionError
from datetime import datetime
# Import export modules with error handling
try:
    from src.export import SubtitleGenerator, DocumentExporter, TTSSynthesizer
except ImportError as e:
    print(f"Warning: Export modules not available: {e}")
    SubtitleGenerator = None
    DocumentExporter = None
    TTSSynthesizer = None


class TranscriptionGUI:
    """GUI for transcription with language selection and translation"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MemoAI - Transcription & Translation Assistant")
        self.root.geometry("1000x750")  # Reduced height for better fit
        self.root.resizable(True, True)
        
        # Store canvas reference for scrolling
        self.canvas = None
        
        # Initialize services
        self.service = TranscriptionService(use_robust_pipeline=True)
        self.url_handler = URLHandler()
        
        # Initialize robust translation integration (with error handling)
        # Use robust translator for better code-mixed speech handling
        try:
            self.translation_integration = RobustTranscriptionTranslationIntegration(
                enable_normalization=True,  # Enable text normalization
                enable_llm_refinement=False  # Disable LLM refinement by default (requires setup)
            )
            self.use_robust_translator = True
            print("✓ Robust translation pipeline initialized")
        except Exception as e:
            # Fallback to standard integration if robust translator fails
            print(f"Warning: Robust translator not available: {e}")
            print("Falling back to standard translation integration...")
            try:
                self.translation_integration = TranscriptionTranslationIntegration()
                self.use_robust_translator = False
                print("✓ Standard translation pipeline initialized")
            except ImportError as ie:
                # Translation service not available - disable translation features
                self.translation_integration = None
                self.use_robust_translator = False
                print(f"Warning: Translation service not available: {ie}")
                print("Translation features will be disabled. Install dependencies to enable.")
            except Exception as ex:
                # Other initialization error
                self.translation_integration = None
                self.use_robust_translator = False
                print(f"Warning: Failed to initialize translation service: {ex}")
        
        # Variables
        self.selected_file = tk.StringVar()
        self.selected_url = tk.StringVar()
        self.input_type = tk.StringVar(value="file")  # "file" or "url"
        self.selected_language = tk.StringVar(value="auto")
        self.target_language = tk.StringVar(value="en")  # Default target for translation
        self.translation_granularity = tk.StringVar(value="whole_text")  # Default: whole text
        self.selected_translation_provider = tk.StringVar(value="auto")  # Default: auto (use default priority)
        self.enable_paragraph_retranslation = tk.BooleanVar(value=False)  # Default: disabled
        self.is_processing = False
        self.is_translating = False
        self.is_exporting = False  # Track export status
        
        # Store transcription result temporarily
        self.current_transcription: Optional[Dict] = None
        self.translations: Dict[str, str] = {}  # Store multiple translations: {target_lang: translated_text}
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        
        # Create scrollable canvas
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        
        # Main container (scrollable)
        main_frame = ttk.Frame(self.canvas, padding="10")
        
        # Configure scroll region
        def configure_scroll_region(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        main_frame.bind("<Configure>", configure_scroll_region)
        
        # Create window in canvas
        canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # Configure canvas scrolling
        def configure_canvas_width(event):
            canvas_width = event.width
            self.canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.canvas.bind("<Configure>", configure_canvas_width)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling (Windows)
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mouse wheel for Windows
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        # Also bind for Linux (Button-4 and Button-5)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="🎤 MemoAI Transcription Assistant",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input Type Selection
        input_frame = ttk.LabelFrame(main_frame, text="Input Source", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            input_frame,
            text="📁 File (Video/Audio)",
            variable=self.input_type,
            value="file",
            command=self._on_input_type_change
        ).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        ttk.Radiobutton(
            input_frame,
            text="🔗 URL (YouTube/Podcast)",
            variable=self.input_type,
            value="url",
            command=self._on_input_type_change
        ).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # File Selection
        self.file_frame = ttk.Frame(main_frame)
        self.file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.file_frame, text="File:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.selected_file, width=50)
        self.file_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        ttk.Button(
            self.file_frame,
            text="Browse...",
            command=self._browse_file
        ).grid(row=0, column=2, padx=5)
        
        # URL Selection
        self.url_frame = ttk.Frame(main_frame)
        self.url_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.url_frame, text="URL:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.selected_url, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # Language Selection
        lang_frame = ttk.LabelFrame(main_frame, text="Language Selection", padding="10")
        lang_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        lang_frame.columnconfigure(0, weight=1)
        
        ttk.Label(
            lang_frame,
            text="Select Language (or Auto-detect):",
            font=("Arial", 10)
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Language dropdown
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.selected_language,
            state="readonly",
            width=50
        )
        self.language_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Populate language options
        language_options = Languages.get_language_for_ui()
        self.language_combo['values'] = [f"{code} - {name}" for code, name in language_options]
        self.language_combo.current(0)  # Select "Auto-detect"
        
        # Info label
        info_label = ttk.Label(
            lang_frame,
            text="💡 Tip: Selecting a language makes transcription faster (skips auto-detection)",
            font=("Arial", 8),
            foreground="gray"
        )
        info_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.enable_preprocessing = tk.BooleanVar(value=True)
        self.enable_validation = tk.BooleanVar(value=True)
        self.paragraph_format = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(
            options_frame,
            text="🔧 Enable Audio Preprocessing (Noise reduction, normalization)",
            variable=self.enable_preprocessing
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(
            options_frame,
            text="✅ Enable Validation (Quality checks)",
            variable=self.enable_validation
        ).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(
            options_frame,
            text="📝 Paragraph Format",
            variable=self.paragraph_format
        ).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # Process Button
        self.process_button = ttk.Button(
            main_frame,
            text="🚀 Start Transcription",
            command=self._start_transcription,
            state=tk.NORMAL
        )
        self.process_button.grid(row=6, column=0, columnspan=3, pady=20)
        
        # Translation Section (initially hidden, shown after transcription)
        self.translation_frame = ttk.LabelFrame(main_frame, text="🌍 Translation", padding="10")
        self.translation_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        self.translation_frame.columnconfigure(1, weight=1)
        self.translation_frame.grid_remove()  # Hide initially
        
        # Row 0: Target language
        ttk.Label(
            self.translation_frame,
            text="Translate to:",
            font=("Arial", 10)
        ).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        # Target language dropdown
        self.target_language_combo = ttk.Combobox(
            self.translation_frame,
            textvariable=self.target_language,
            state="readonly",
            width=40
        )
        self.target_language_combo.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # Populate target language options (all languages except auto-detect)
        language_options = Languages.get_language_for_ui()
        target_options = [f"{code} - {name}" for code, name in language_options if code != "auto" and code != "---"]
        self.target_language_combo['values'] = target_options
        # Set default to English
        for i, opt in enumerate(target_options):
            if opt.startswith("en -"):
                self.target_language_combo.current(i)
                break
        
        # Translate button
        self.translate_button = ttk.Button(
            self.translation_frame,
            text="🌍 Translate",
            command=self._start_translation,
            state=tk.DISABLED
        )
        self.translate_button.grid(row=0, column=2, padx=5)
        
        # Row 1: Translation Provider
        ttk.Label(
            self.translation_frame,
            text="Translation Provider:",
            font=("Arial", 10)
        ).grid(row=1, column=0, padx=5, sticky=tk.W, pady=(10, 0))
        
        # Provider dropdown - will be populated dynamically
        self.provider_options = ["Auto (Use default priority)"]
        self.provider_values = ["auto"]
        
        # Populate provider dropdown
        self._populate_provider_dropdown()
        
        self.provider_combo = ttk.Combobox(
            self.translation_frame,
            textvariable=self.selected_translation_provider,
            state="readonly",
            width=50,
            values=self.provider_options
        )
        self.provider_combo.grid(row=1, column=1, padx=5, sticky=(tk.W, tk.E), pady=(10, 0))
        # Set default to "Auto"
        self.provider_combo.current(0)
        
        # Helper function to get provider value from display text
        def get_provider_value():
            selection = self.provider_combo.get()
            try:
                idx = self.provider_options.index(selection)
                return self.provider_values[idx] if idx < len(self.provider_values) else "auto"
            except:
                return "auto"  # Default fallback
        
        self._get_provider_value = get_provider_value
        
        # Row 2: Translation granularity
        ttk.Label(
            self.translation_frame,
            text="Translation Mode:",
            font=("Arial", 10)
        ).grid(row=2, column=0, padx=5, sticky=tk.W, pady=(10, 0))
        
        # Granularity dropdown
        granularity_options = [
            ("whole_text", "Whole Text (Best for context preservation)"),
            ("paragraph", "Paragraph-wise (Good for long texts)"),
            ("line_by_line", "Line-by-line (Best for subtitles)")
        ]
        granularity_values = [opt[0] for opt in granularity_options]
        granularity_display = [opt[1] for opt in granularity_options]
        
        self.granularity_combo = ttk.Combobox(
            self.translation_frame,
            textvariable=self.translation_granularity,
            state="readonly",
            width=50,
            values=granularity_display
        )
        self.granularity_combo.grid(row=2, column=1, padx=5, sticky=(tk.W, tk.E), pady=(10, 0))
        # Set default to "Whole Text"
        self.granularity_combo.current(0)
        
        # Helper function to get granularity value from display text
        def get_granularity_value():
            selection = self.granularity_combo.get()
            for opt in granularity_options:
                if opt[1] == selection:
                    return opt[0]
            return "whole_text"  # Default fallback
        
        self._get_granularity_value = get_granularity_value
        
        # Row 3: Paragraph-level re-translation checkbox
        self.paragraph_retranslation_checkbox = ttk.Checkbutton(
            self.translation_frame,
            text="Enable paragraph-level re-translation for quality refinement",
            variable=self.enable_paragraph_retranslation
        )
        self.paragraph_retranslation_checkbox.grid(row=3, column=0, columnspan=2, padx=5, sticky=tk.W, pady=(10, 0))
        
        # Translation status label (moved to row 4 after checkbox)
        self.translation_status_label = ttk.Label(
            self.translation_frame,
            text="",
            font=("Arial", 8),
            foreground="gray"
        )
        self.translation_status_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # Export Section (initially hidden, shown after transcription)
        self.export_frame = ttk.LabelFrame(main_frame, text="📤 Export", padding="10")
        self.export_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        self.export_frame.columnconfigure(0, weight=1)
        self.export_frame.columnconfigure(1, weight=1)
        self.export_frame.columnconfigure(2, weight=1)
        self.export_frame.grid_remove()  # Hide initially
        
        # Export buttons row
        export_buttons_frame = ttk.Frame(self.export_frame)
        export_buttons_frame.grid(row=0, column=0, columnspan=3, pady=5)
        
        # Generate Subtitles button
        self.export_subtitles_button = ttk.Button(
            export_buttons_frame,
            text="📝 Generate Subtitles (SRT/VTT)",
            command=self._export_subtitles,
            state=tk.DISABLED
        )
        self.export_subtitles_button.grid(row=0, column=0, padx=5)
        
        # Export Documents button
        self.export_documents_button = ttk.Button(
            export_buttons_frame,
            text="📄 Export Documents (MD/TXT/JSON)",
            command=self._export_documents,
            state=tk.DISABLED
        )
        self.export_documents_button.grid(row=0, column=1, padx=5)
        
        # Generate Speech button
        self.export_speech_button = ttk.Button(
            export_buttons_frame,
            text="🔊 Generate Speech (TTS)",
            command=self._export_speech,
            state=tk.DISABLED
        )
        self.export_speech_button.grid(row=0, column=2, padx=5)
        
        # Export status label
        self.export_status_label = ttk.Label(
            self.export_frame,
            text="",
            font=("Arial", 8),
            foreground="gray"
        )
        self.export_status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # Progress Frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_label = ttk.Label(progress_frame, text="", font=("Arial", 9))
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=400
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Output Frame with Notebook (Tabs for Original and Translations)
        output_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        output_frame.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Original transcription tab
        original_frame = ttk.Frame(self.notebook)
        self.notebook.add(original_frame, text="📝 Original Transcription")
        
        self.output_text = scrolledtext.ScrolledText(
            original_frame,
            wrap=tk.WORD,
            width=70,
            height=15,
            font=("Arial", 10)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Translations tab (will be populated dynamically)
        self.translations_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translations_frame, text="🌍 Translations")
        
        # Translations text area
        self.translations_text = scrolledtext.ScrolledText(
            self.translations_frame,
            wrap=tk.WORD,
            width=70,
            height=15,
            font=("Arial", 10),
            state=tk.NORMAL,  # Ensure it's enabled for editing
            bg="white",  # Ensure background is visible
            fg="black"   # Ensure text color is visible
        )
        self.translations_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize with placeholder text
        self.translations_text.insert(1.0, "No translations yet. Use the translation section above to translate.\n\n")
        self.translations_text.insert(tk.END, "You can translate to multiple languages - each translation will be added here.")
        
        # Initial state
        self._on_input_type_change()
    
    def _populate_provider_dropdown(self):
        """Populate provider dropdown with available providers"""
        self.provider_options = ["Auto (Use default priority)"]
        self.provider_values = ["auto"]
        
        # Get available providers from translation service
        if self.translation_integration:
            try:
                # Handle both robust and standard translators
                if hasattr(self.translation_integration, 'get_available_providers'):
                    # Robust translator
                    available_providers = self.translation_integration.get_available_providers()
                elif hasattr(self.translation_integration, 'translation_service'):
                    # Standard translator
                    available_providers = self.translation_integration.translation_service.get_available_providers()
                else:
                    available_providers = []
                
                provider_display_names = {
                    'google': 'Google Translate',
                    'libre': 'LibreTranslate',
                    'deepl': 'DeepL',
                    'ai': 'AI Translation'
                }
                for provider in available_providers:
                    display_name = provider_display_names.get(provider, provider.title())
                    self.provider_options.append(display_name)
                    self.provider_values.append(provider)
            except Exception as e:
                print(f"Warning: Could not get available providers: {e}")
        
        # Update combobox if it exists
        if hasattr(self, 'provider_combo'):
            self.provider_combo['values'] = self.provider_options
    
    def _on_input_type_change(self):
        """Handle input type change"""
        if self.input_type.get() == "file":
            self.file_frame.grid()
            self.url_frame.grid_remove()
        else:
            self.file_frame.grid_remove()
            self.url_frame.grid()
    
    def _browse_file(self):
        """Browse for file"""
        file_path = filedialog.askopenfilename(
            title="Select Audio/Video File",
            filetypes=[
                ("All Supported", "*.mp4 *.mp3 *.m4a *.aac *.wav *.flac *.ogg *.avi *.mov *.mkv *.webm"),
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("Audio Files", "*.mp3 *.m4a *.aac *.wav *.flac *.ogg"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.selected_file.set(file_path)
    
    def _get_selected_language(self) -> Optional[str]:
        """Extract language code from selection"""
        selection = self.language_combo.get()
        if not selection:
            return None
        
        # Format: "code - name"
        parts = selection.split(" - ", 1)
        if len(parts) > 0:
            code = parts[0].strip()
            if code == "auto" or code == "---":
                return None
            return code
        return None
    
    def _start_transcription(self):
        """Start transcription in separate thread"""
        if self.is_processing:
            messagebox.showwarning("Processing", "Transcription is already in progress!")
            return
        
        # Validate input
        if self.input_type.get() == "file":
            file_path = self.selected_file.get()
            if not file_path or not Path(file_path).exists():
                messagebox.showerror("Error", "Please select a valid file!")
                return
            input_source = Path(file_path)
        else:
            url = self.selected_url.get().strip()
            if not url:
                messagebox.showerror("Error", "Please enter a valid URL!")
                return
            # Validate URL
            is_valid, url_type = self.url_handler.validate_url(url)
            if not is_valid:
                messagebox.showerror("Error", f"Invalid URL: {url}")
                return
            input_source = url
        
        # Clear previous transcription and translations (override)
        self.current_transcription = None
        self.translations = {}
        self.translation_frame.grid_remove()
        self.translate_button.config(state=tk.DISABLED)
        self.translations_text.delete(1.0, tk.END)
        self.translations_text.insert(tk.END, "No translations yet. Transcribe first, then translate.")
        
        # Get language
        language = self._get_selected_language()
        
        # Start processing in thread
        self.is_processing = True
        self.process_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_label.config(text="Processing... Please wait")
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Starting transcription...\n\n")
        
        thread = threading.Thread(
            target=self._transcribe_thread,
            args=(input_source, language),
            daemon=True
        )
        thread.start()
    
    def _transcribe_thread(self, input_source, language: Optional[str]):
        """Transcription in separate thread"""
        try:
            # Update UI
            self.root.after(0, self._update_progress, f"Transcribing... Language: {language or 'Auto-detect'}")
            
            # Perform transcription
            if isinstance(input_source, str):  # URL
                result = self.service.transcribe_url(
                    url=input_source,
                    language=language,
                    enable_preprocessing=self.enable_preprocessing.get(),
                    enable_validation=self.enable_validation.get(),
                    paragraph_format=self.paragraph_format.get()
                )
            else:  # File
                result = self.service.transcribe(
                    file_path=input_source,
                    language=language,
                    enable_preprocessing=self.enable_preprocessing.get(),
                    enable_validation=self.enable_validation.get(),
                    paragraph_format=self.paragraph_format.get()
                )
            
            # Update UI with results
            self.root.after(0, self._on_transcription_complete, result)
            
        except Exception as e:
            self.root.after(0, self._on_transcription_error, str(e))
    
    def _update_progress(self, message: str):
        """Update progress message"""
        self.progress_label.config(text=message)
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)
    
    def _on_transcription_complete(self, result: dict):
        """Handle transcription completion"""
        self.progress_bar.stop()
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress_label.config(text="✅ Transcription completed!")
        
        # Store transcription result temporarily (override previous if exists)
        self.current_transcription = result
        self.translations = {}  # Clear previous translations when new transcription
        self.translation_data = {}  # Clear previous translation data
        
        # Display results
        self.output_text.delete(1.0, tk.END)
        
        # Basic info
        self.output_text.insert(tk.END, "=" * 70 + "\n")
        self.output_text.insert(tk.END, "TRANSCRIPTION RESULT\n")
        self.output_text.insert(tk.END, "=" * 70 + "\n\n")
        
        # Language info
        detected_lang = result.get('language', 'unknown')
        self.output_text.insert(tk.END, f"Language: {detected_lang}\n")
        
        # Metadata
        metadata = result.get('metadata', {})
        if metadata:
            model_used = metadata.get('model_used', 'unknown')
            self.output_text.insert(tk.END, f"Model Used: {model_used}\n")
            if metadata.get('preprocessing_applied'):
                self.output_text.insert(tk.END, "✅ Preprocessing: Applied\n")
            if metadata.get('validation_applied'):
                self.output_text.insert(tk.END, "✅ Validation: Applied\n")
        
        # Quality report
        quality_report = result.get('quality_report')
        if quality_report:
            quality_score = quality_report.get('quality_score', 100)
            self.output_text.insert(tk.END, f"\nQuality Score: {quality_score}/100\n")
            
            warnings = quality_report.get('warnings', [])
            if warnings:
                self.output_text.insert(tk.END, "\n⚠️  Warnings:\n")
                for warning in warnings:
                    self.output_text.insert(tk.END, f"  - {warning}\n")
        
        # Transcription text
        self.output_text.insert(tk.END, "\n" + "=" * 70 + "\n")
        self.output_text.insert(tk.END, "TRANSCRIBED TEXT:\n")
        self.output_text.insert(tk.END, "=" * 70 + "\n\n")
        
        text = result.get('text', '')
        if text:
            self.output_text.insert(tk.END, text)
        else:
            self.output_text.insert(tk.END, "No text transcribed.")
        
        # Saved path
        saved_path = result.get('saved_path')
        if saved_path:
            self.output_text.insert(tk.END, f"\n\n✅ Saved to: {saved_path}")
        
        self.output_text.see(tk.END)
        
        # Show translation section and enable translate button (if translation service is available)
        if self.translation_integration is not None:
            # Populate provider dropdown when showing translation frame
            self._populate_provider_dropdown()
            self.translation_frame.grid()
            self.translate_button.config(state=tk.NORMAL)
            self.translation_status_label.config(
                text="✅ Transcription stored. You can now translate to any language multiple times."
            )
        else:
            # Translation service not available - hide translation section
            self.translation_frame.grid_remove()
            self.translate_button.config(state=tk.DISABLED)
        
        # Clear translations tab
        self.translations_text.delete(1.0, tk.END)
        self.translations_text.insert(tk.END, "No translations yet. Use the translation section above to translate.\n\n")
        self.translations_text.insert(tk.END, "You can translate to multiple languages - each translation will be added here.")
        
        # Show export section and enable export buttons (if export modules available)
        self.export_frame.grid()
        if SubtitleGenerator is not None:
            self.export_subtitles_button.config(state=tk.NORMAL)
        if DocumentExporter is not None:
            self.export_documents_button.config(state=tk.NORMAL)
        if TTSSynthesizer is not None:
            self.export_speech_button.config(state=tk.NORMAL)
        self.export_status_label.config(
            text="✅ Ready to export. Select an export option above."
        )
        
        # Scroll to show Results section after transcription
        if self.canvas:
            try:
                self.canvas.update_idletasks()
                # Scroll to bottom to show Results section
                self.canvas.yview_moveto(1.0)
                self.root.update_idletasks()
            except Exception:
                pass
        
        messagebox.showinfo("Success", "Transcription completed successfully! You can now translate it.\n\nScroll down to see the Results section.")
    
    def _on_transcription_error(self, error_message: str):
        """Handle transcription error"""
        self.progress_bar.stop()
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress_label.config(text="❌ Transcription failed")
        
        # Clear stored transcription on error
        self.current_transcription = None
        self.translations = {}
        self.translation_frame.grid_remove()
        self.translate_button.config(state=tk.DISABLED)
        
        self.output_text.insert(tk.END, f"\n❌ ERROR: {error_message}\n")
        self.output_text.see(tk.END)
        
        messagebox.showerror("Error", f"Transcription failed:\n{error_message}")
    
    def _get_target_language_code(self) -> Optional[str]:
        """Extract target language code from selection"""
        selection = self.target_language_combo.get()
        if not selection:
            return None
        
        parts = selection.split(" - ", 1)
        if len(parts) > 0:
            code = parts[0].strip()
            if code == "---":
                return None
            return code
        return None
    
    def _start_translation(self):
        """Start translation in separate thread"""
        # Check if translation service is available
        if self.translation_integration is None:
            messagebox.showerror(
                "Translation Unavailable",
                "Translation service is not available.\n\n"
                "Please install required dependencies:\n"
                "  pip install googletrans==4.0.0rc1\n"
                "  pip install deep-translator>=1.11.4\n\n"
                "Then restart the application."
            )
            return
        
        if not self.current_transcription:
            messagebox.showwarning("No Transcription", "Please transcribe audio/video first!")
            return
        
        if self.is_translating:
            messagebox.showwarning("Processing", "Translation is already in progress!")
            return
        
        target_lang = self._get_target_language_code()
        if not target_lang:
            messagebox.showerror("Error", "Please select a target language!")
            return
        
        # Check if already translated to this language
        if target_lang in self.translations:
            response = messagebox.askyesno(
                "Already Translated",
                f"This transcription is already translated to {target_lang}.\n"
                f"Do you want to translate again?"
            )
            if not response:
                # Just show existing translation
                self._show_translation(target_lang, self.translations[target_lang])
                return
        
        # Start translation in thread
        self.is_translating = True
        self.translate_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_label.config(text=f"Translating to {target_lang}...")
        
        thread = threading.Thread(
            target=self._translate_thread,
            args=(target_lang,),
            daemon=True
        )
        thread.start()
    
    def _translate_thread(self, target_language: str):
        """Translation in separate thread"""
        try:
            # Update UI
            self.root.after(0, self._update_progress, f"Translating to {target_language}...")
            
            print(f"DEBUG: Starting translation to {target_language}")
            print(f"DEBUG: Current transcription text length: {len(self.current_transcription.get('text', '')) if self.current_transcription else 0}")
            
            # Translate using stored transcription
            print(f"DEBUG: About to translate. Source text preview: {self.current_transcription.get('text', '')[:50]}")
            print(f"DEBUG: Source language: {self.current_transcription.get('language', 'unknown')}")
            print(f"DEBUG: Target language: {target_language}")
            
            # Get selected provider
            provider_str = self._get_provider_value()
            selected_provider = None if provider_str == "auto" else provider_str
            
            print(f"DEBUG: Using translation provider: {selected_provider or 'auto (default priority)'}")
            print(f"DEBUG: Using robust translator: {getattr(self, 'use_robust_translator', False)}")
            
            # Use robust translator if available, otherwise fallback to standard
            if getattr(self, 'use_robust_translator', False) and isinstance(
                self.translation_integration, RobustTranscriptionTranslationIntegration
            ):
                # Use robust translator with sentence-by-sentence translation
                print("DEBUG: Using robust translation pipeline (sentence-by-sentence)")
                # Get paragraph re-translation setting from checkbox
                enable_retranslation = self.enable_paragraph_retranslation.get()
                print(f"DEBUG: Paragraph re-translation enabled: {enable_retranslation}")
                translation_result = self.translation_integration.translate_transcription(
                    transcription_result=self.current_transcription,
                    target_language=target_language,
                    preferred_provider=selected_provider,
                    use_sentence_by_sentence=True,
                    use_two_step=False,
                    enable_paragraph_retranslation=enable_retranslation
                )
            else:
                # Fallback to standard translator
                print("DEBUG: Using standard translation pipeline")
                granularity_str = self._get_granularity_value()
                if granularity_str == "whole_text":
                    selected_granularity = TranslationGranularity.WHOLE_TEXT
                elif granularity_str == "paragraph":
                    selected_granularity = TranslationGranularity.PARAGRAPH
                elif granularity_str == "line_by_line":
                    selected_granularity = TranslationGranularity.LINE_BY_LINE
                else:
                    selected_granularity = TranslationGranularity.WHOLE_TEXT
                
                print(f"DEBUG: Using translation granularity: {selected_granularity.value}")
                translation_result = self.translation_integration.translate_transcription(
                    transcription_result=self.current_transcription,
                    target_language=target_language,
                    granularity=selected_granularity,
                    preferred_provider=selected_provider
                )
            
            print(f"DEBUG: Translation completed. Result keys: {list(translation_result.keys())}")
            translated_text_result = translation_result.get('translated_text', '')
            print(f"DEBUG: Translated text length: {len(translated_text_result)}")
            print(f"DEBUG: Translated text preview (first 100 chars): {translated_text_result[:100]}")
            print(f"DEBUG: Full translation_result dict: {translation_result}")
            
            # Store translation
            translated_text = translation_result.get('translated_text', '')
            if translated_text:
                self.translations[target_language] = translated_text
                # Store full translation data for export (with segments/paragraphs if available)
                self.translation_data[target_language] = {
                    'text': translated_text,
                    'translation_result': translation_result,
                    'source_language': self.current_transcription.get('language'),
                    'target_language': target_language
                }
                print(f"DEBUG: Translation stored for {target_language}")
            else:
                print(f"WARNING: Empty translation result for {target_language}")
            
            # Update UI with translation
            self.root.after(0, self._on_translation_complete, translation_result, target_language)
            
        except Exception as e:
            print(f"ERROR in translation thread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, self._on_translation_error, str(e))
    
    def _on_translation_complete(self, translation_result: dict, target_language: str):
        """Handle translation completion"""
        self.progress_bar.stop()
        self.is_translating = False
        self.translate_button.config(state=tk.NORMAL)
        self.progress_label.config(text="✅ Translation completed!")
        
        # Debug: Check translation result structure
        print(f"DEBUG: Translation result keys: {list(translation_result.keys())}")
        print(f"DEBUG: Has 'translated_text': {'translated_text' in translation_result}")
        
        translated_text = translation_result.get('translated_text', '')
        
        # Validate translated text
        if not translated_text or not translated_text.strip():
            error_msg = "Translation returned empty text. Please try again."
            print(f"ERROR: {error_msg}")
            print(f"DEBUG: Full translation_result: {translation_result}")
            self._on_translation_error(error_msg)
            return
        
        # Handle both robust and standard translation result formats
        if getattr(self, 'use_robust_translator', False):
            # Robust translator format
            provider = translation_result.get('provider', 'unknown')
            used_preferred = translation_result.get('used_preferred_provider', True)
            fallback_provider = translation_result.get('fallback_provider')
            secondary_provider = translation_result.get('secondary_provider')
            paragraph_retranslation = translation_result.get('paragraph_retranslation', False)
        else:
            # Standard translator format
            translation_info = translation_result.get('translation', {})
            provider = translation_info.get('provider', 'unknown')
            used_preferred = translation_info.get('used_preferred_provider', True)
            fallback_provider = translation_info.get('fallback_provider')
            secondary_provider = translation_info.get('secondary_provider')
            paragraph_retranslation = translation_info.get('secondary_provider') is not None
        
        # Get selected provider name for display
        selected_provider_str = self._get_provider_value()
        provider_display_names = {
            'google': 'Google Translate',
            'libre': 'LibreTranslate',
            'deepl': 'DeepL',
            'ai': 'AI Translation',
            'auto': 'Auto (default priority)'
        }
        selected_provider_display = provider_display_names.get(selected_provider_str, selected_provider_str.title())
        
        # Update translation status with fallback information
        lang_name = Languages.get_language_name(target_language)
        provider_display = provider_display_names.get(provider, provider.title())
        
        # Build status message with all information
        status_parts = []
        
        if not used_preferred and fallback_provider and selected_provider_str != "auto":
            # Selected provider failed, fallback was used
            fallback_display = provider_display_names.get(fallback_provider, fallback_provider.title())
            status_parts.append(f"⚠️ Your selected provider ({selected_provider_display}) failed. Used {fallback_display} instead.")
        else:
            status_parts.append(f"✅ Translated to {lang_name} ({target_language}) using {provider_display}.")
        
        # Add paragraph re-translation info if enabled
        if paragraph_retranslation and secondary_provider:
            secondary_display = provider_display_names.get(secondary_provider, secondary_provider.title())
            status_parts.append(f"🔄 Paragraph re-translation applied using {secondary_display} for quality refinement.")
        
        status_parts.append("You can translate to more languages!")
        
        status_text = " ".join(status_parts)
        
        self.translation_status_label.config(
            text=status_text,
            foreground="orange" if not used_preferred and fallback_provider else "gray"
        )
        
        # Show translation in translations tab FIRST
        print(f"DEBUG _on_translation_complete: About to show translation, text length: {len(translated_text)}")
        print(f"DEBUG _on_translation_complete: Translated text preview: {translated_text[:100]}")
        print(f"DEBUG _on_translation_complete: Full translation_result: {translation_result}")
        
        # Verify we have the correct translated text
        original_text = translation_result.get('original_text', '')
        
        # Check if translated_text is a coroutine object (async issue)
        if isinstance(translated_text, str) and translated_text.startswith('<coroutine'):
            error_msg = "Translation returned coroutine object - async issue. Please check console."
            print(f"ERROR: {error_msg}")
            print(f"Translated text is: {translated_text}")
            messagebox.showerror("Translation Error", error_msg)
            self._on_translation_error(error_msg)
            return
        
        if translated_text == original_text or not translated_text or translated_text.strip() == original_text.strip():
            print(f"WARNING: Translated text matches original text! Translation may have failed.")
            print(f"Original: {original_text[:50]}")
            print(f"Translated: {translated_text[:50]}")
            # Show error to user
            messagebox.showerror(
                "Translation Failed",
                "Translation returned the same text. This usually means:\n\n"
                "1. Translation service is not working properly\n"
                "2. Network/API issues\n"
                "3. Language code mismatch\n\n"
                "Please check the console for detailed error messages."
            )
            return
        
        # Show translation in both places: translations tab AND original tab
        self._show_translation(target_language, translated_text)
        self._show_translation_in_original_tab(target_language, translated_text, original_text)
        
        # Scroll canvas to show Results section
        if self.canvas:
            try:
                self.canvas.update_idletasks()
                # Scroll to bottom to show Results section
                self.canvas.yview_moveto(1.0)  # Scroll to bottom (1.0 = 100%)
                self.root.update_idletasks()
                print("DEBUG: Scrolled canvas to show Results section")
            except Exception as e:
                print(f"DEBUG: Could not scroll canvas: {e}")
        
        # Switch to translations tab (index 1 is the translations tab)
        print(f"DEBUG _on_translation_complete: Switching to translations tab (index 1)")
        print(f"DEBUG _on_translation_complete: Number of tabs: {self.notebook.index('end')}")
        try:
            # Get the tab index for translations tab
            tab_count = self.notebook.index('end')
            if tab_count >= 2:
                self.notebook.select(1)  # Index 1 is the translations tab
                print(f"DEBUG _on_translation_complete: Tab switched to index 1")
            else:
                print(f"ERROR: Only {tab_count} tabs found, expected at least 2")
        except Exception as e:
            print(f"ERROR: Failed to switch tab: {e}")
            import traceback
            traceback.print_exc()
        
        # Force UI update multiple times to ensure visibility
        self.root.update_idletasks()
        self.root.update()
        
        # Make sure translations frame and text widget are visible and focused
        self.translations_frame.update()
        self.translations_text.update()
        self.translations_text.focus_set()
        
        # Verify the text is actually in the widget
        final_check = self.translations_text.get(1.0, tk.END)
        print(f"DEBUG _on_translation_complete: Final verification - text in widget length: {len(final_check)}")
        print(f"DEBUG _on_translation_complete: Text contains translation: {translated_text[:50] in final_check}")
        print(f"DEBUG _on_translation_complete: Current tab index: {self.notebook.index(self.notebook.select())}")
        
        # Scroll to show the content - first to top to see header, then to end
        self.translations_text.see(1.0)
        self.root.update_idletasks()
        self.translations_text.see(tk.END)
        self.root.update()
        
        # Show success message
        self.root.after(200, lambda: messagebox.showinfo(
            "Translation Complete", 
            f"Translation to {target_language} completed!\n\n"
            f"The translation is shown in the Results section below.\n"
            f"Scroll down if needed to see the '🌍 Translations' tab."
        ))
    
    def _show_translation(self, target_language: str, translated_text: str):
        """Show translation in translations tab"""
        # Validate input
        if not translated_text or not translated_text.strip():
            print(f"Warning: Empty translation for {target_language}")
            return
        
        print(f"DEBUG _show_translation: target_language={target_language}, text_length={len(translated_text)}")
        print(f"DEBUG _show_translation: First 50 chars: {translated_text[:50]}")
        
        lang_name = Languages.get_language_name(target_language)
        
        # Get current text and check if it's the initial placeholder
        current_text = self.translations_text.get(1.0, tk.END)
        print(f"DEBUG _show_translation: Current text length: {len(current_text)}")
        print(f"DEBUG _show_translation: Current text preview: {current_text[:100]}")
        
        is_initial_text = "No translations yet" in current_text or current_text.strip() == "" or len(current_text.strip()) < 50
        
        translation_header = f"TRANSLATION TO {lang_name.upper()} ({target_language})"
        print(f"DEBUG _show_translation: is_initial_text={is_initial_text}, header={translation_header}")
        
        if is_initial_text or translation_header not in current_text:
            # Clear initial text and add new translation
            print("DEBUG _show_translation: Adding new translation (clearing initial text)")
            # Ensure widget is enabled
            self.translations_text.config(state=tk.NORMAL)
            self.translations_text.delete(1.0, tk.END)
            self.translations_text.insert(tk.END, "=" * 70 + "\n")
            self.translations_text.insert(tk.END, f"TRANSLATION TO {lang_name.upper()} ({target_language})\n")
            self.translations_text.insert(tk.END, "=" * 70 + "\n\n")
            self.translations_text.insert(tk.END, translated_text)
            self.translations_text.insert(tk.END, "\n\n")
            # Keep widget enabled so user can see and copy text
            self.translations_text.config(state=tk.NORMAL)
            
            # Verify text was inserted
            inserted_text = self.translations_text.get(1.0, tk.END)
            print(f"DEBUG _show_translation: After insert, text length: {len(inserted_text)}")
            print(f"DEBUG _show_translation: After insert, preview: {inserted_text[:100]}")
        else:
            # Update existing translation
            print("DEBUG _show_translation: Updating existing translation")
            lines = current_text.split('\n')
            new_lines = []
            skip_until_separator = False
            
            for i, line in enumerate(lines):
                if translation_header in line:
                    skip_until_separator = True
                    continue
                elif skip_until_separator and line.startswith("=" * 70):
                    skip_until_separator = False
                    # Add new translation
                    new_lines.append("=" * 70)
                    new_lines.append(translation_header)
                    new_lines.append("=" * 70)
                    new_lines.append("")
                    new_lines.append(translated_text)
                    new_lines.append("")
                    new_lines.append("")
                elif not skip_until_separator:
                    new_lines.append(line)
            
            self.translations_text.delete(1.0, tk.END)
            self.translations_text.insert(1.0, '\n'.join(new_lines))
        
        # Ensure text is visible
        self.translations_text.see(tk.END)
        
        # Force update
        self.root.update_idletasks()
        
        # Final verification
        final_text = self.translations_text.get(1.0, tk.END)
        print(f"DEBUG _show_translation: Final text length: {len(final_text)}")
        print(f"DEBUG _show_translation: Final text contains translation: {translated_text[:30] in final_text}")
    
    def _show_translation_in_original_tab(self, target_language: str, translated_text: str, original_text: str):
        """Show translation in the original transcription tab for easy viewing"""
        lang_name = Languages.get_language_name(target_language)
        
        # Append translation to the original transcription tab
        self.output_text.insert(tk.END, "\n\n" + "=" * 70 + "\n")
        self.output_text.insert(tk.END, f"🌍 TRANSLATION TO {lang_name.upper()} ({target_language})\n")
        self.output_text.insert(tk.END, "=" * 70 + "\n\n")
        self.output_text.insert(tk.END, translated_text)
        self.output_text.insert(tk.END, "\n")
        
        # Scroll to show the translation
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def _on_translation_error(self, error_message: str):
        """Handle translation error"""
        self.progress_bar.stop()
        self.is_translating = False
        self.translate_button.config(state=tk.NORMAL)
        self.progress_label.config(text="❌ Translation failed")
        
        self.translation_status_label.config(
            text=f"❌ Translation failed: {error_message}"
        )
        
        messagebox.showerror("Error", f"Translation failed:\n{error_message}")
    
    def _export_subtitles(self):
        """Export subtitles (SRT/VTT)"""
        if not self.current_transcription:
            messagebox.showwarning("No Transcription", "Please transcribe audio/video first!")
            return
        
        if self.is_exporting:
            messagebox.showwarning("Processing", "Export is already in progress!")
            return
        
        # Ask user which translation to use (if any)
        translated_lang = None
        translated_segments = None
        
        if self.translations:
            # Ask user to select translation language or use original
            selected = messagebox.askyesnocancel(
                "Export Subtitles",
                "Do you want to export translated subtitles?\n\n"
                "Yes: Export translated subtitles\n"
                "No: Export original subtitles\n"
                "Cancel: Abort export"
            )
            
            if selected is None:  # Cancel
                return
            
            if selected:  # Yes - use translation
                # Use first available translation (could be improved with dropdown)
                translated_lang = list(self.translations.keys())[0]
                translation_info = self.translation_data.get(translated_lang, {})
                translation_result = translation_info.get('translation_result', {})
                # Try to get translated segments if available
                translated_segments = translation_result.get('translation', {}).get('segments')
        
        # Start export in thread
        self.is_exporting = True
        self.export_subtitles_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_label.config(text="Generating subtitles...")
        
        thread = threading.Thread(
            target=self._export_subtitles_thread,
            args=(translated_lang, translated_segments),
            daemon=True
        )
        thread.start()
    
    def _export_subtitles_thread(self, translated_lang: Optional[str], translated_segments: Optional[List]):
        """Export subtitles in separate thread"""
        try:
            # Get source file path for naming
            source_file = None
            if self.current_transcription.get('metadata', {}).get('source_file'):
                source_file = Path(self.current_transcription['metadata']['source_file'])
            elif self.selected_file.get():
                source_file = Path(self.selected_file.get())
            
            # Get translated text if available
            translated_text = None
            if translated_lang:
                translated_text = self.translations.get(translated_lang)
            
            # Generate both SRT and VTT
            self.root.after(0, self._update_progress, "Generating SRT and VTT files...")
            
            subtitle_files = SubtitleGenerator.generate_both(
                transcription_data=self.current_transcription,
                source_file=source_file,
                use_paragraphs=False,
                translated_text=translated_text,
                translated_segments=translated_segments
            )
            
            # Update UI
            self.root.after(0, self._on_subtitle_export_complete, subtitle_files, translated_lang)
            
        except Exception as e:
            print(f"ERROR in subtitle export thread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, self._on_export_error, f"Subtitle export failed: {str(e)}")
    
    def _on_subtitle_export_complete(self, subtitle_files: Dict[str, Path], translated_lang: Optional[str]):
        """Handle subtitle export completion"""
        self.progress_bar.stop()
        self.is_exporting = False
        self.export_subtitles_button.config(state=tk.NORMAL)
        self.progress_label.config(text="✅ Subtitle export completed!")
        
        srt_path = subtitle_files.get('srt')
        vtt_path = subtitle_files.get('vtt')
        
        lang_info = f" ({Languages.get_language_name(translated_lang)})" if translated_lang else ""
        
        message = f"✅ Subtitles generated successfully{lang_info}!\n\n"
        if srt_path:
            message += f"SRT: {srt_path}\n"
        if vtt_path:
            message += f"VTT: {vtt_path}\n"
        
        self.export_status_label.config(text=message.strip(), foreground="green")
        messagebox.showinfo("Export Complete", message)
    
    def _export_documents(self):
        """Export documents (MD/TXT/JSON)"""
        if DocumentExporter is None:
            messagebox.showerror(
                "Export Unavailable",
                "Document export is not available.\n\n"
                "Please check that all export modules are properly installed."
            )
            return
        
        if not self.current_transcription:
            messagebox.showwarning("No Transcription", "Please transcribe audio/video first!")
            return
        
        if self.is_exporting:
            messagebox.showwarning("Processing", "Export is already in progress!")
            return
        
        # Ask user which translation to use (if any)
        translated_lang = None
        translated_paragraphs = None
        translated_segments = None
        
        if self.translations:
            selected = messagebox.askyesnocancel(
                "Export Documents",
                "Do you want to export translated documents?\n\n"
                "Yes: Export translated documents\n"
                "No: Export original documents\n"
                "Cancel: Abort export"
            )
            
            if selected is None:
                return
            
            if selected:
                translated_lang = list(self.translations.keys())[0]
                translation_info = self.translation_data.get(translated_lang, {})
                translation_result = translation_info.get('translation_result', {})
                translated_paragraphs = translation_result.get('translation', {}).get('paragraphs')
                translated_segments = translation_result.get('translation', {}).get('segments')
        
        # Start export in thread
        self.is_exporting = True
        self.export_documents_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_label.config(text="Exporting documents...")
        
        thread = threading.Thread(
            target=self._export_documents_thread,
            args=(translated_lang, translated_paragraphs, translated_segments),
            daemon=True
        )
        thread.start()
    
    def _export_documents_thread(self, translated_lang: Optional[str], translated_paragraphs: Optional[List], translated_segments: Optional[List]):
        """Export documents in separate thread"""
        try:
            # Get source file path for naming
            source_file = None
            if self.current_transcription.get('metadata', {}).get('source_file'):
                source_file = Path(self.current_transcription['metadata']['source_file'])
            elif self.selected_file.get():
                source_file = Path(self.selected_file.get())
            
            # Get translated text if available
            translated_text = None
            if translated_lang:
                translated_text = self.translations.get(translated_lang)
            
            # Export all document formats
            self.root.after(0, self._update_progress, "Exporting Markdown, Text, and JSON...")
            
            doc_files = DocumentExporter.export_all(
                transcription_data=self.current_transcription,
                source_file=source_file,
                translated_text=translated_text,
                translated_paragraphs=translated_paragraphs,
                translated_segments=translated_segments,
                include_timestamps=True
            )
            
            # Update UI
            self.root.after(0, self._on_document_export_complete, doc_files, translated_lang)
            
        except Exception as e:
            print(f"ERROR in document export thread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, self._on_export_error, f"Document export failed: {str(e)}")
    
    def _on_document_export_complete(self, doc_files: Dict[str, Path], translated_lang: Optional[str]):
        """Handle document export completion"""
        self.progress_bar.stop()
        self.is_exporting = False
        self.export_documents_button.config(state=tk.NORMAL)
        self.progress_label.config(text="✅ Document export completed!")
        
        lang_info = f" ({Languages.get_language_name(translated_lang)})" if translated_lang else ""
        
        message = f"✅ Documents exported successfully{lang_info}!\n\n"
        if doc_files.get('md'):
            message += f"Markdown: {doc_files['md']}\n"
        if doc_files.get('txt'):
            message += f"Text: {doc_files['txt']}\n"
        if doc_files.get('json'):
            message += f"JSON: {doc_files['json']}\n"
        
        self.export_status_label.config(text=message.strip(), foreground="green")
        messagebox.showinfo("Export Complete", message)
    
    def _export_speech(self):
        """Export speech (TTS)"""
        if TTSSynthesizer is None:
            messagebox.showerror(
                "Export Unavailable",
                "Speech synthesis is not available.\n\n"
                "Please install TTS dependencies:\n"
                "  pip install gtts>=2.4.0\n"
                "  or\n"
                "  pip install pyttsx3>=2.90"
            )
            return
        
        if not self.current_transcription:
            messagebox.showwarning("No Transcription", "Please transcribe audio/video first!")
            return
        
        if self.is_exporting:
            messagebox.showwarning("Processing", "Export is already in progress!")
            return
        
        # Ask user which content to use for TTS
        use_translations = False
        
        if self.translations:
            selected = messagebox.askyesnocancel(
                "Generate Speech",
                f"Do you want to generate speech from translated text?\n\n"
                f"Found {len(self.translations)} translation(s): {', '.join(self.translations.keys())}\n\n"
                f"Yes: Generate speech for ALL translations (one file per language)\n"
                f"No: Generate speech from original text\n"
                f"Cancel: Abort"
            )
            
            if selected is None:
                return
            
            use_translations = selected
        
        # Ask for TTS language if not using translations
        tts_language = None
        if not use_translations:
            # Simple prompt - could be improved with dropdown
            tts_lang_input = messagebox.askstring(
                "TTS Language",
                "Enter language code for TTS (e.g., 'en', 'hi', 'te'):\n\n"
                "Default: 'en' (English)",
                initialvalue="en"
            )
            if tts_lang_input:
                tts_language = tts_lang_input.strip()
            else:
                tts_language = "en"
        
        # Ask for per-paragraph option
        per_paragraph = messagebox.askyesno(
            "TTS Options",
            "Generate one audio file per paragraph?\n\n"
            "Yes: Multiple files (one per paragraph)\n"
            "No: Single file (entire text)"
        )
        
        # Start export in thread
        self.is_exporting = True
        self.export_speech_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_label.config(text="Generating speech...")
        
        thread = threading.Thread(
            target=self._export_speech_thread,
            args=(use_translations, tts_language, per_paragraph),
            daemon=True
        )
        thread.start()
    
    def _export_speech_thread(self, use_translations: bool, tts_language: Optional[str], per_paragraph: bool):
        """Export speech in separate thread - generates audio for ALL translations if use_translations=True"""
        try:
            # Initialize TTS
            self.root.after(0, self._update_progress, "Initializing TTS engine...")
            tts = TTSSynthesizer(tts_engine="gtts")
            
            # Get source file path for naming
            source_file = None
            if self.current_transcription.get('metadata', {}).get('source_file'):
                source_file = Path(self.current_transcription['metadata']['source_file'])
            elif self.selected_file.get():
                source_file = Path(self.selected_file.get())
            
            all_audio_files = []  # Store all generated audio files
            
            if use_translations and self.translations:
                # Generate speech for ALL translations
                total_translations = len(self.translations)
                for idx, (target_lang, translated_text) in enumerate(self.translations.items(), 1):
                    self.root.after(0, self._update_progress, 
                                  f"Generating speech for {target_lang} ({idx}/{total_translations})...")
                    
                    # Get translation data
                    translation_info = self.translation_data.get(target_lang, {})
                    translation_result = translation_info.get('translation_result', {})
                    translated_paragraphs = translation_result.get('translation', {}).get('paragraphs')
                    
                    # Generate base name with language code
                    if source_file:
                        base_name = f"{source_file.stem}_{target_lang}"
                    else:
                        base_name = f"tts_{target_lang}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # Generate speech for this translation
                    if translated_paragraphs and per_paragraph:
                        # Per-paragraph synthesis
                        audio_files = tts.synthesize_paragraphs(
                            paragraphs=translated_paragraphs,
                            language=target_lang,
                            base_name=base_name,
                            output_format="mp3",
                            per_paragraph=True
                        )
                    else:
                        # Full text synthesis
                        output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.mp3"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        audio_file = tts.synthesize(
                            text=translated_text,
                            language=target_lang,
                            output_path=output_path,
                            output_format="mp3"
                        )
                        audio_files = [audio_file]
                    
                    all_audio_files.extend(audio_files)
            else:
                # Generate speech from original text
                original_text = self.current_transcription.get('text', '')
                if not original_text:
                    raise TranscriptionError("No original text found in transcription")
                
                # Use provided language or default to original transcription language
                if not tts_language:
                    tts_language = self.current_transcription.get('language', 'en')
                
                self.root.after(0, self._update_progress, f"Generating speech in {tts_language}...")
                
                # Generate base name
                if source_file:
                    base_name = source_file.stem
                else:
                    base_name = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Generate speech
                if per_paragraph:
                    original_paragraphs = self.current_transcription.get('paragraphs', [])
                    if original_paragraphs:
                        audio_files = tts.synthesize_paragraphs(
                            paragraphs=original_paragraphs,
                            language=tts_language,
                            base_name=base_name,
                            output_format="mp3",
                            per_paragraph=True
                        )
                    else:
                        # No paragraphs, synthesize as single file
                        output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.mp3"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        audio_files = [tts.synthesize(
                            text=original_text,
                            language=tts_language,
                            output_path=output_path,
                            output_format="mp3"
                        )]
                else:
                    output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.mp3"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    audio_files = [tts.synthesize(
                        text=original_text,
                        language=tts_language,
                        output_path=output_path,
                        output_format="mp3"
                    )]
                
                all_audio_files.extend(audio_files)
            
            # Update UI with all generated files
            self.root.after(0, self._on_speech_export_complete, all_audio_files, use_translations)
            
        except Exception as e:
            print(f"ERROR in speech export thread: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, self._on_export_error, f"Speech generation failed: {str(e)}")
    
    def _on_speech_export_complete(self, audio_files: List[Path], use_translations: bool):
        """Handle speech export completion"""
        self.progress_bar.stop()
        self.is_exporting = False
        self.export_speech_button.config(state=tk.NORMAL)
        self.progress_label.config(text="✅ Speech generation completed!")
        
        if use_translations:
            # Multiple languages generated
            message = f"✅ Speech generated successfully for {len(self.translations)} translation(s)!\n\n"
            message += f"Generated {len(audio_files)} audio file(s):\n"
            for audio_file in audio_files:
                # Extract language code from filename if possible
                lang_code = "unknown"
                for lang in self.translations.keys():
                    if lang in str(audio_file):
                        lang_code = lang
                        break
                lang_name = Languages.get_language_name(lang_code)
                message += f"  - {lang_name} ({lang_code}): {audio_file}\n"
        else:
            # Single language (original text)
            message = f"✅ Speech generated successfully!\n\n"
            if len(audio_files) == 1:
                message += f"Audio file: {audio_files[0]}"
            else:
                message += f"Generated {len(audio_files)} audio files:\n"
                for idx, audio_file in enumerate(audio_files, 1):
                    message += f"  {idx}. {audio_file}\n"
        
        self.export_status_label.config(text=message.strip(), foreground="green")
        messagebox.showinfo("Speech Generation Complete", message)
    
    def _on_export_error(self, error_message: str):
        """Handle export error"""
        self.progress_bar.stop()
        self.is_exporting = False
        self.export_subtitles_button.config(state=tk.NORMAL)
        self.export_documents_button.config(state=tk.NORMAL)
        self.export_speech_button.config(state=tk.NORMAL)
        self.progress_label.config(text="❌ Export failed")
        self.export_status_label.config(
            text=f"❌ Export failed: {error_message}",
            foreground="red"
        )
        messagebox.showerror("Export Error", f"Export failed:\n{error_message}")


def main():
    """Run the GUI application"""
    root = tk.Tk()
    app = TranscriptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
