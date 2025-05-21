import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import pandas as pd
import chardet
import os

class CSVEncodingConverter:
    def __init__(self, master):
        self.master = master
        self.master.title("CSV Encoding Converter to UTF-8")
        self.master.geometry("480x280") 

        #menu bar and stuff here
        menubar = tk.Menu(master)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Select CSV", command=self.select_file)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        master.config(menu=menubar)

        #main frame
        main_frame = ttk.Frame(master, padding="10 10 10 10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        #file selection
        self.label = ttk.Label(main_frame, text="1. Select a CSV file to convert to UTF-8:")
        self.label.pack(pady=(0,5), anchor='w')

        self.select_button = ttk.Button(main_frame, text="Select CSV File", command=self.select_file)
        self.select_button.pack(pady=5, fill=tk.X)

        #sample size input -- made it user-defined if csv is super large and some hidden char located somewhere
        sample_size_frame = ttk.Frame(main_frame)
        sample_size_frame.pack(pady=5, fill=tk.X)

        self.sample_size_label = ttk.Label(sample_size_frame, text="2. Detection Sample Size (bytes):")
        self.sample_size_label.pack(side=tk.LEFT, padx=(0, 5))

        self.sample_size_var = tk.StringVar(value="200000") # dfault value -- rather large
        self.sample_size_entry = ttk.Entry(sample_size_frame, textvariable=self.sample_size_var, width=10)
        self.sample_size_entry.pack(side=tk.LEFT)
        
        #status label
        self.status_label_header = ttk.Label(main_frame, text="Status:")
        self.status_label_header.pack(pady=(10,0), anchor='w')
        self.status_label = ttk.Label(main_frame, text="No file selected.", wraplength=440, justify=tk.LEFT)
        self.status_label.pack(pady=(0,10), anchor='w', fill=tk.X, expand=True)
        
        #action buttons
        action_button_frame = ttk.Frame(main_frame)
        action_button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10,0))

        self.about_button = ttk.Button(action_button_frame, text="About", command=self.show_about)
        self.about_button.pack(side=tk.LEFT, padx=(0,5))

        self.quit_button = ttk.Button(action_button_frame, text="Quit", command=self.master.quit)
        self.quit_button.pack(side=tk.RIGHT)


    def show_about(self):
        messagebox.showinfo(
            "About",
            "CSV Encoding Converter\n\n"
            "This tool helps convert CSV files from various encodings to UTF-8.\n"
            "It uses 'chardet' for initial encoding detection and then attempts "
            "a series of common encodings, prioritizing UTF-7 if issues like "
            "'+AF8-' are suspected.\n\n"
            "Developed by ODAT project."
        )

    def get_sample_size(self):
        try:
            size = int(self.sample_size_var.get())
            if size <= 0:
                messagebox.showwarning("Invalid Sample Size", "Sample size must be a positive integer. Using default (200000).")
                return 200000
            return size
        except ValueError:
            messagebox.showwarning("Invalid Sample Size", "Sample size must be a valid integer. Using default (200000).")
            return 200000


    def detect_encoding_info(self, file_path, n_bytes): #n_bytes now passed as argument
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(n_bytes)
            if not raw_data:
                return {'encoding': None, 'confidence': 0.0, 'error': 'File is empty or sample size too small.'}
            
            result = chardet.detect(raw_data)
            #ensure 'encoding' and 'confidence' keys exist
            if 'encoding' not in result:
                result['encoding'] = None
            if 'confidence' not in result:
                result['confidence'] = 0.0
            return result
        except FileNotFoundError:
            return {'encoding': None, 'confidence': 0.0, 'error': 'File not found during detection.'}
        except Exception as e:
            return {'encoding': None, 'confidence': 0.0, 'error': f'Error during detection: {str(e)}'}

    def select_file(self):
        initial_dir_open = os.getcwd() 
        file_path = filedialog.askopenfilename(
            title="Choose CSV file",
            initialdir=initial_dir_open,
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            self.status_label.config(text="No file selected.")
            return

        current_sample_size = self.get_sample_size() #get sample size from GUI

        try:
            self.status_label.config(text=f"Detecting encoding (sample: {current_sample_size} bytes)...")
            self.master.update_idletasks()

            detected_info = self.detect_encoding_info(file_path, current_sample_size)
            chardet_encoding = detected_info.get('encoding')
            chardet_confidence = detected_info.get('confidence', 0.0)
            detection_error = detected_info.get('error')

            if detection_error:
                messagebox.showerror("Encoding Detection Error", detection_error)
                self.status_label.config(text=f"Detection error: {detection_error}")
                return

            base_status_text = f"Chardet: {chardet_encoding} (conf: {chardet_confidence:.2f}). "
            self.status_label.config(text=base_status_text + "Preparing to read...")
            self.master.update_idletasks()

            df = None
            used_encoding = None

            potential_encodings = []
            if chardet_encoding and chardet_encoding.lower() != 'utf-7':
                potential_encodings.append(chardet_encoding)

            if 'utf-7' not in [enc.lower() for enc in potential_encodings if enc]:
                is_ascii_guess = chardet_encoding and 'ascii' in chardet_encoding.lower()
                is_low_confidence = chardet_confidence < 0.85 
                
                if is_ascii_guess or is_low_confidence or chardet_encoding is None:
                    potential_encodings.insert(0, 'utf-7') 
                else:
                    potential_encodings.append('utf-7')

            common_fallbacks = ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252', 'cp1252']
            for enc in common_fallbacks:
                if not any(existing_enc and existing_enc.lower() == enc.lower() for existing_enc in potential_encodings):
                    potential_encodings.append(enc)
            
            final_encodings_to_try = []
            seen_encodings_lower = set()
            for enc in potential_encodings:
                if enc and enc.lower() not in seen_encodings_lower:
                    final_encodings_to_try.append(enc)
                    seen_encodings_lower.add(enc.lower())
            
            self.status_label.config(text=base_status_text + f"Will try: {', '.join(filter(None,final_encodings_to_try))}")
            self.master.update_idletasks()

            for enc_attempt in final_encodings_to_try:
                if not enc_attempt: continue #skip if None somehow got in
                try:
                    self.status_label.config(text=base_status_text + f"Trying: {enc_attempt}...")
                    self.master.update_idletasks()
                    
                    df_attempt = pd.read_csv(file_path, encoding=enc_attempt, on_bad_lines='warn')
                    
                    df = df_attempt
                    used_encoding = enc_attempt
                    self.status_label.config(text=f"Successfully read with: {used_encoding}.")
                    self.master.update_idletasks()
                    break 
                except (UnicodeDecodeError, LookupError) as e_read:
                    print(f"Failed to read with {enc_attempt}: {str(e_read)}")
                    self.status_label.config(text=base_status_text + f"Failed with {enc_attempt}. ")
                    self.master.update_idletasks()
                except pd.errors.ParserError as e_parse:
                    print(f"Pandas parsing error with {enc_attempt}: {str(e_parse)}")
                    self.status_label.config(text=base_status_text + f"Parsing error with {enc_attempt}. ")
                    self.master.update_idletasks()
                except Exception as e_other: 
                    print(f"Other error reading with {enc_attempt}: {str(e_other)}")
                    self.status_label.config(text=base_status_text + f"Error with {enc_attempt}. ")
                    self.master.update_idletasks()

            if df is None:
                messagebox.showerror("Error", f"Could not read the CSV file with any of the attempted encodings: {', '.join(filter(None,final_encodings_to_try))}. Check console for details.")
                self.status_label.config(text="Failed to read CSV. Check console for details.")
                return

            initial_name = os.path.basename(file_path)
            default_name = os.path.splitext(initial_name)[0] + '_utf8.csv'
            initial_dir_save = os.path.dirname(file_path) 
            
            save_path = filedialog.asksaveasfilename(
                title="Save as UTF-8 CSV",
                initialdir=initial_dir_save,
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=default_name
            )
            if not save_path:
                self.status_label.config(text="Save cancelled.")
                return

            df.to_csv(save_path, encoding='utf-8', index=False)

            messagebox.showinfo(
                "Success",
                f"File saved as UTF-8 to:\n{save_path}\nSuccessfully read using encoding: {used_encoding}"
            )
            self.status_label.config(text="Conversion successful. Ready for next file.")

        except FileNotFoundError:
            messagebox.showerror("Error", "The selected file was not found.")
            self.status_label.config(text="Error: File not found.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
            self.status_label.config(text=f"Conversion failed: {str(e)}")
            import traceback
            print(traceback.format_exc())

if __name__ == '__main__':
    root = tk.Tk()
    #theme here
    try:
        style = ttk.Style(root)
        available_themes = style.theme_names()
        if 'clam' in available_themes: # 'clam' is widely available
            style.theme_use('clam')
        elif 'vista' in available_themes: #good for Windows people -- no good to use windows STOP!!!
             style.theme_use('vista')
        elif 'aqua' in available_themes: #good for macOS lads
             style.theme_use('aqua')
    except tk.TclError:
        print("ttk themes not available or failed to apply.")
        
    app = CSVEncodingConverter(root)
    root.mainloop()