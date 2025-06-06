import tkinter as tk
from tkinter import scrolledtext
import os
from dotenv import load_dotenv
from openai import OpenAI
import threading
import json
from datetime import datetime
import mss
import mss.tools
from PIL import Image
import base64
from io import BytesIO
from AppKit import NSWorkspace, NSRunningApplication, NSScreen

# Load environment variables
load_dotenv()

# Initialize OpenAI client after loading environment variables
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class AIChatApp:
    def __init__(self):
        print("Booting up AI Chat Assistant...")
        self.root = tk.Tk()
        self.root.withdraw()  # Hide initially
        self.chat_history = []
        self.window_context = ""
        self.setup_openai()
        self.setup_hotkey_binding()
        print("Ready! Press Cmd+Shift+Space to open the chat window.")

    def setup_openai(self):
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("Please set OPENAI_API_KEY in your .env file")
        
        # Set up the event handler for AI responses
        if hasattr(self, 'root'):
            self.root.bind('<<AIResponse>>', self._handle_ai_response)

    def setup_hotkey_binding(self):
        print("Setting up hotkey binding...")
        # Create a transparent window to capture events
        self.root.attributes('-alpha', 0.0)  # Make it transparent
        self.root.attributes('-topmost', True)  # Keep it on top
        self.root.geometry('1x1+0+0')  # Make it tiny
        self.root.deiconify()  # Show it (but it's transparent)

        # Bind the hotkey
        self.root.bind('<Command-Shift-space>', self.toggle_window)
        print("Hotkey bound to Command-Shift-space")

        # Start checking for hotkey
        self.check_hotkey()

    def check_hotkey(self):
        # This keeps the window alive and checking for hotkey
        self.root.after(100, self.check_hotkey)
        # Debug print to show the window is still running
        print(".", end="", flush=True)

    def toggle_window(self, event=None):
        from datetime import datetime
        print(f"\n=== HOTKEY DETECTED at {datetime.now().strftime('%H:%M:%S')} ===")
        if not hasattr(self, 'chat_display'):
            self.create_chat_window()
        else:
            if self.root.winfo_viewable():
                self.hide_window()
            else:
                # Recreate the window components
                self.create_chat_window()

    def get_window_context(self):
        try:
            active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if active_app:
                app_name = active_app.localizedName()
                return f"Current active application: {app_name}"
            return "No active application detected"
        except Exception as e:
            return f"Error getting window context: {str(e)}"

    def capture_window_screenshot(self):
        try:
            screenshots = []
            with mss.mss() as sct:
                # Get all screens (monitors)
                screens = NSScreen.screens()
                print(f"Found {len(screens)} screens")
                
                for i, screen in enumerate(screens, 1):
                    # Get screen dimensions
                    frame = screen.frame()
                    width = int(frame.size.width)
                    height = int(frame.size.height)
                    print(f"Capturing screen {i}: {width}x{height}")
                    
                    # Capture the screen
                    screenshot = sct.grab({
                        "left": int(frame.origin.x),
                        "top": int(frame.origin.y),
                        "width": width,
                        "height": height
                    })
                    
                    # Convert to PIL Image
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    print(f"Screen {i} screenshot size: {img.width}x{img.height}")
                    
                    # Resize if too large (to reduce API costs)
                    max_size = 1024
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        print(f"Screen {i} resized to: {img.width}x{img.height}")
                    
                    # Convert to base64
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=85)
                    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    screenshots.append({
                        "screen": i,
                        "image": img_str,
                        "width": img.width,
                        "height": img.height
                    })
                
                return screenshots
        except Exception as e:
            print(f"Error capturing screenshots: {str(e)}")
            return None

    def create_chat_window(self):
        # Configure the existing root window
        self.root.title("AI Chat")
        self.root.geometry("400x500")
        self.root.attributes('-topmost', True)  # Keep window always on top
        self.root.attributes('-alpha', 0.9)
        self.root.lift()  # Bring window to front
        self.root.focus_force()  # Force focus to this window

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Input field
        self.input_field = tk.Entry(self.root)
        self.input_field.pack(padx=10, pady=10, fill=tk.X)
        self.input_field.bind('<Return>', self.send_message)

        # Send button
        send_button = tk.Button(self.root, text="Send", command=self.send_message)
        send_button.pack(padx=10, pady=5)

        # Close button
        close_button = tk.Button(self.root, text="Close", command=self.hide_window)
        close_button.pack(padx=10, pady=5)

        # Initial message
        self.add_message("AI", "Hello! I'm your AI assistant. I can see your screen and help you with anything you're working on. How can I help you today?")

        # Show the window
        self.root.deiconify()
        self.root.lift()  # Additional lift after showing

    def hide_window(self):
        if self.root:
            self.root.withdraw()

    def add_message(self, sender, message):
        if self.root:
            self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
            self.chat_display.see(tk.END)
            self.chat_history.append({"role": "user" if sender == "You" else "assistant", "content": message})

    def send_message(self, event=None):
        message = self.input_field.get()
        if not message:
            return

        self.input_field.delete(0, tk.END)
        self.add_message("You", message)

        # Get current window context and screenshot
        self.window_context = self.get_window_context()
        screenshots = self.capture_window_screenshot()

        # Send to OpenAI in a separate thread
        threading.Thread(target=self.get_ai_response, args=(message, screenshots)).start()

    def get_ai_response(self, message, screenshots):
        try:
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant that can see the user's screen. Use the visual context to provide relevant and helpful responses."},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Current context: {self.window_context}\n\nUser message: {message}"}
                ]}
            ]

            if screenshots:
                for screenshot in screenshots:
                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot['image']}",
                            "detail": "low"
                        }
                    })
                    messages[1]["content"].append({
                        "type": "text",
                        "text": f"This is screen {screenshot['screen']} ({screenshot['width']}x{screenshot['height']})"
                    })

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content
            
            # Use a thread-safe way to update the UI
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.setvar('ai_response', ai_response)
                self.root.event_generate('<<AIResponse>>', when='tail')
                # Call the handler directly in test environment
                if hasattr(self, '_handle_ai_response'):
                    self._handle_ai_response(None)
            return ai_response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.setvar('ai_response', error_msg)
                self.root.event_generate('<<AIResponse>>', when='tail')
                # Call the handler directly in test environment
                if hasattr(self, '_handle_ai_response'):
                    self._handle_ai_response(None)
            return error_msg

    def _handle_ai_response(self, event):
        """Handle AI responses in a thread-safe way"""
        response = self.root.getvar('ai_response')
        self.add_message("AI", response)

def main():
    app = AIChatApp()
    app.root.mainloop()

if __name__ == "__main__":
    main() 
