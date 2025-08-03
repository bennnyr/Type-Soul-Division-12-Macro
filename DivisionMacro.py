import customtkinter as ctk
import tkinter as tk
from tkinter import font
from ctypes import windll
import cv2
import numpy as np
import mss
import autoit
import time
import threading
import keyboard
import pyautogui

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

hasstyle = False

def set_appwindow(root):
    global hasstyle
    if not hasstyle:
        hwnd = windll.user32.GetParent(root.winfo_id())
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        res = windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        root.withdraw()
        root.after(100, lambda: root.wm_deiconify())
        hasstyle = True

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class AutoClickerGUI:
    def __init__(self):
        # Core variables
        self.selection_active = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selected_area = None
        self.clicking_active = False
        self.detection_thread = None
        
        # Auto-start feature variables
        self.board_location = None
        self.yes_button_location = None
        self.circles_clicked = []
        self.auto_start_enabled = False
        self.last_game_start_time = 0
        self.last_activity_time = 0
        
        # Track repeated clicks on same location (for detecting stuck on player)
        self.recent_click_locations = []
        self.stuck_click_threshold = 20
        
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.01
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Division Macro")
        self.root.geometry("1000x550")
        self.root.configure(fg_color="#1a1a1a")
        self.root.resizable(False, False)
        
        self.root.after(100, self.make_rounded_corners)
        
        self.x = 0
        self.y = 0
        
        self.root.overrideredirect(True)
        
        # Fonts
        self.font_title = ctk.CTkFont(family="Segoe UI", size=32, weight="normal")
        self.font_subtitle = ctk.CTkFont(family="Segoe UI", size=24, weight="normal")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=14, weight="normal")
        self.font_small = ctk.CTkFont(family="Segoe UI", size=12, weight="normal")
        
        # State variables
        self.auto_start_var = tk.BooleanVar()
        self.start_clicking_var = tk.BooleanVar()
        self.stop_exit_var = tk.BooleanVar()
        
        self.create_widgets()
        
        self.center_window()
        
        keyboard.add_hotkey('f1', self.toggle_clicking)
        keyboard.add_hotkey('esc', self.stop_and_exit)
        
        global hasstyle
        hasstyle = False
        self.root.update_idletasks()
        self.root.withdraw()
        set_appwindow(self.root)
        
    def make_rounded_corners(self):
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            region = windll.gdi32.CreateRoundRectRgn(0, 0, 1000, 550, 20, 20)
            windll.user32.SetWindowRgn(hwnd, region, True)
            
        except Exception as e:
            print(f"Could not create rounded corners: {e}")
            pass
        
    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - 1000) // 2
        y = (screen_height - 550) // 2
        
        self.root.geometry(f"1000x550+{x}+{y}")
        
    # Custom title bar with traffic light buttons
    def create_custom_title_bar(self):
        # Custom title bar frame that sits at the top with rounded top corners
        self.title_bar = ctk.CTkFrame(
            self.root,
            height=40,
            fg_color="#2b2b2b",
            corner_radius=15  # Add rounded corners to match window
        )
        self.title_bar.pack(fill="x", side="top", padx=2, pady=(2, 0))
        
        self.traffic_lights = ctk.CTkFrame(
            self.title_bar,
            width=80,
            height=40,
            fg_color="transparent"
        )
        self.traffic_lights.pack(side="left", padx=10)
        
        self.close_btn = ctk.CTkButton(
            self.traffic_lights,
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#ff5f57",
            hover_color="#ff4444",
            text="",
            command=self.close_app
        )
        self.close_btn.place(x=0, y=14)
        
        self.minimize_btn = ctk.CTkButton(
            self.traffic_lights,
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#ffbd2e",
            hover_color="#ffaa00",
            text="",
            command=self.minimize_app
        )
        self.minimize_btn.place(x=20, y=14)
        
        self.maximize_btn = ctk.CTkButton(
            self.traffic_lights,
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#28ca42",
            hover_color="#22aa33",
            text="",
            command=self.maximize_app
        )
        self.maximize_btn.place(x=40, y=14)
        
        self.title_text = ctk.CTkLabel(
            self.title_bar,
            text="made by bennnyr 1353962710240460880",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ffffff"
        )
        self.title_text.place(relx=0.5, rely=0.5, anchor="center")
        
        self.title_bar.bind("<Button-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        self.title_text.bind("<Button-1>", self.start_move)
        self.title_text.bind("<B1-Motion>", self.do_move)
        
        self.title_bar.bind("<Map>", self.frame_map)
        
    def frame_map(self, event=None):
        self.root.overrideredirect(True)
        self.root.update_idletasks()
        set_appwindow(self.root)
        self.root.state("normal")
        
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        
    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        
    def close_app(self):
        self.root.quit()
        self.root.destroy()
        
    def minimize_app(self):
        global hasstyle
        self.root.update_idletasks()
        self.root.overrideredirect(False)
        self.root.state("iconic")
        hasstyle = False
        
    def maximize_app(self):
        # Basic maximize for overrideredirect window
        try:
            if hasattr(self, '_is_maximized') and self._is_maximized:
                # Restore to original size
                self.root.geometry("1000x550")
                self._is_maximized = False
            else:
                # Maximize to screen size
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")
                self._is_maximized = True
        except:
            pass
        
    def create_widgets(self):
        # Create custom title bar first
        self.create_custom_title_bar()
        
        # Main content frame (below title bar) with rounded bottom corners
        self.content_frame = ctk.CTkFrame(
            self.root,
            fg_color="#1a1a1a",
            corner_radius=15  # Add rounded corners
        )
        self.content_frame.pack(fill="both", expand=True, padx=2, pady=(0, 2))  # Small padding for rounded effect
        
        # Main title
        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="console",
            font=self.font_title,
            text_color="white"
        )
        self.title_label.place(x=50, y=20)
        
        # Console area (left side)
        self.console_frame = ctk.CTkFrame(
            self.content_frame,
            width=350,
            height=320,
            fg_color="#2d2d2d",
            corner_radius=10
        )
        self.console_frame.place(x=50, y=100)
        
        # Console text area
        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            width=330,
            height=300,
            fg_color="#2d2d2d",
            text_color="white",
            font=self.font_small,
            corner_radius=8
        )
        self.console_text.place(x=10, y=10)
        
        # Quick start guide title
        self.guide_title = ctk.CTkLabel(
            self.content_frame,
            text="quick start guide",
            font=self.font_subtitle,
            text_color="#8b5fbf"
        )
        self.guide_title.place(x=430, y=60)
        
        # Quick start guide instructions
        instructions = [
            "• click screen area and choose the minigame area",
            "• set division board and yes button locations", 
            "• enable auto start to make it automated",
            "• press f1 to start"
        ]
        
        for i, instruction in enumerate(instructions):
            label = ctk.CTkLabel(
                self.content_frame,
                text=instruction,
                font=self.font_text,
                text_color="#666666"
            )
            label.place(x=430, y=100 + (i * 25))
        
        # Screen area label and box (changed to match original proportions)
        self.screen_area_label = ctk.CTkLabel(
            self.content_frame,
            text="screen area",
            font=self.font_text,
            text_color="#8b5fbf"
        )
        self.screen_area_label.place(x=850, y=60)
        
        self.screen_area_btn = ctk.CTkButton(
            self.content_frame,
            text="Select Screen Area",
            width=120,
            height=25,
            fg_color="#3d3d3d",
            hover_color="#4d4d4d",
            corner_radius=8,
            font=self.font_small,
            command=self.start_area_selection
        )
        self.screen_area_btn.place(x=815, y=90)
        
        # Auto start config label
        self.auto_config_label = ctk.CTkLabel(
            self.content_frame,
            text="auto start config",
            font=self.font_subtitle,
            text_color="#8b5fbf"
        )
        self.auto_config_label.place(x=750, y=170)
        
        # Yes button label and box (changed to match original proportions)
        self.yes_button_label = ctk.CTkLabel(
            self.content_frame,
            text="yes button",
            font=self.font_text,
            text_color="#8b5fbf"
        )
        self.yes_button_label.place(x=850, y=200)
        
        self.yes_button_btn = ctk.CTkButton(
            self.content_frame,
            text="Set Location",
            width=120,
            height=25,
            fg_color="#3d3d3d",
            hover_color="#4d4d4d",
            corner_radius=8,
            font=self.font_small,
            command=self.setup_yes_button
        )
        self.yes_button_btn.place(x=815, y=230)
        
        # Division board label and box (changed to match original proportions)
        self.division_label = ctk.CTkLabel(
            self.content_frame,
            text="division board",
            font=self.font_text,
            text_color="#8b5fbf"
        )
        self.division_label.place(x=850, y=300)
        
        self.division_btn = ctk.CTkButton(
            self.content_frame,
            text="Set Location",
            width=120,
            height=25,
            fg_color="#3d3d3d",
            hover_color="#4d4d4d",
            corner_radius=8,
            font=self.font_small,
            command=self.setup_board_location
        )
        self.division_btn.place(x=815, y=330)
        
        # Checkboxes section
        # Enable auto start checkbox
        self.auto_start_checkbox = ctk.CTkCheckBox(
            self.content_frame,
            text="enable auto start",
            font=self.font_text,
            text_color="white",
            variable=self.auto_start_var,
            onvalue=True,
            offvalue=False,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=4,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.toggle_auto_start
        )
        self.auto_start_checkbox.place(x=430, y=280)
        
        # Start clicking checkbox
        self.start_clicking_checkbox = ctk.CTkCheckBox(
            self.content_frame,
            text="start clicking (F1)",
            font=self.font_text,
            text_color="white",
            variable=self.start_clicking_var,
            onvalue=True,
            offvalue=False,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=4,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.toggle_clicking
        )
        self.start_clicking_checkbox.place(x=430, y=320)
        
        # Stop and exit checkbox
        self.stop_exit_checkbox = ctk.CTkCheckBox(
            self.content_frame,
            text="stop and exit",
            font=self.font_text,
            text_color="white",
            variable=self.stop_exit_var,
            onvalue=True,
            offvalue=False,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=4,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.stop_and_exit
        )
        self.stop_exit_checkbox.place(x=430, y=360)
        
    # Add console logging method
    def add_console_text(self, text):
        """Add text to the console"""
        self.console_text.insert("end", f"{text}\n")
        self.console_text.see("end")
        
    # Screen area selection
    def start_area_selection(self):
        self.root.withdraw()
        self.create_selection_overlay()
        
    def create_selection_overlay(self):
        self.overlay = tk.Toplevel()
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-alpha', 0.3)
        self.overlay.attributes('-topmost', True)
        self.overlay.configure(bg='black')
        
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg='black')
        
        self.canvas.bind('<Button-1>', self.on_mouse_press)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        
        self.canvas.create_text(self.overlay.winfo_screenwidth()//2, 50, 
                               text="🖱️ Click and drag to select the game area. Press ESC to cancel.",
                               fill="#ffffff", font=("Segoe UI", 18, "bold"))
        
        self.canvas.create_text(self.overlay.winfo_screenwidth()//2, 80, 
                               text="Select the area where circles appear during the minigame",
                               fill="#9ca3af", font=("Segoe UI", 14))
        
        self.overlay.bind('<Escape>', lambda e: self.cancel_selection())
        self.overlay.focus_set()
        
    def on_mouse_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.selection_active = True
        
    def on_mouse_drag(self, event):
        if self.selection_active:
            self.canvas.delete("selection_rect")
            self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y,
                                       outline="#6366f1", width=3, tags="selection_rect")
            
    def on_mouse_release(self, event):
        if self.selection_active:
            self.end_x = event.x
            self.end_y = event.y
            self.selection_active = False
            
            x1, x2 = sorted([self.start_x, self.end_x])
            y1, y2 = sorted([self.start_y, self.end_y])
            
            self.selected_area = (x1, y1, x2, y2)
            self.finish_selection()
            
    def cancel_selection(self):
        self.overlay.destroy()
        self.root.deiconify()
        
    def finish_selection(self):
        self.overlay.destroy()
        self.root.deiconify()
        
        if self.selected_area:
            x1, y1, x2, y2 = self.selected_area
            width = x2 - x1
            height = y2 - y1
            self.add_console_text(f"✅ Screen area selected: {width}x{height} at ({x1}, {y1})")
            self.screen_area_btn.configure(text="✅ Area Set", fg_color="#4CAF50")
    
    # Location setup
    def setup_board_location(self):
        self.root.withdraw()
        self.create_click_overlay("division board")
        
    def setup_yes_button(self):
        self.root.withdraw()
        self.create_click_overlay("yes button")
        
    def create_click_overlay(self, location_type):
        self.location_type = location_type
        self.overlay = tk.Toplevel()
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-alpha', 0.3)
        self.overlay.attributes('-topmost', True)
        self.overlay.configure(bg='black')
        
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg='black')
        
        self.canvas.bind('<Button-1>', self.on_location_click)
        
        self.canvas.create_text(self.overlay.winfo_screenwidth()//2, 50, 
                               text=f"Click on the {location_type} location. Press ESC to cancel.",
                               fill="white", font=("Consolas", 16))
        
        self.overlay.bind('<Escape>', lambda e: self.cancel_location_setup())
        self.overlay.focus_set()
        
    def on_location_click(self, event):
        screen_x = self.overlay.winfo_rootx() + event.x
        screen_y = self.overlay.winfo_rooty() + event.y
        
        if self.location_type == "division board":
            self.board_location = (screen_x, screen_y)
            self.division_btn.configure(text="✅ Board Set", fg_color="#4CAF50")
            self.add_console_text(f"Division board location set to: ({screen_x}, {screen_y})")
        elif self.location_type == "yes button":
            self.yes_button_location = (screen_x, screen_y)
            self.yes_button_btn.configure(text="✅ Yes Set", fg_color="#4CAF50")
            self.add_console_text(f"Yes button location set to: ({screen_x}, {screen_y})")
            
        self.finish_location_setup()
        
    def cancel_location_setup(self):
        self.overlay.destroy()
        self.root.deiconify()
        
    def finish_location_setup(self):
        self.overlay.destroy()
        self.root.deiconify()
        
    # Auto-start functionality
    def toggle_auto_start(self):
        self.auto_start_enabled = self.auto_start_var.get()
        if self.auto_start_enabled:
            if self.board_location and self.yes_button_location:
                self.add_console_text("🚀 Auto-start enabled")
            else:
                self.add_console_text("❌ Set board and yes button locations first!")
                self.auto_start_var.set(False)
                self.auto_start_enabled = False
        else:
            self.add_console_text("🛑 Auto-start disabled")
    
    # Circle detection and clicking
    def detect_circles(self, screenshot):
        gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=50
        )
        
        detected_circles = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                detected_circles.append((x, y))
                
        return detected_circles
    
    def capture_area(self):
        if not self.selected_area:
            return None
            
        x1, y1, x2, y2 = self.selected_area
        
        with mss.mss() as sct:
            region = {"top": y1, "left": x1, "width": x2-x1, "height": y2-y1}
            screenshot = sct.grab(region)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            
        return img
    
    def click_detection_mode(self):
        while self.clicking_active:
            try:
                if self.auto_start_enabled:
                    self.check_and_auto_start()
                
                screenshot = self.capture_area()
                if screenshot is not None:
                    circles = self.detect_circles(screenshot)
                    
                    for circle_x, circle_y in circles:
                        if not self.clicking_active:
                            break
                            
                        screen_x = self.selected_area[0] + circle_x
                        screen_y = self.selected_area[1] + circle_y
                        
                        click_offsets = [
                            (0, 0),
                            (-2, -2),
                            (2, 2)
                        ]
                        
                        for offset_x, offset_y in click_offsets:
                            click_x = screen_x + offset_x
                            click_y = screen_y + offset_y
                            autoit.mouse_click("left", click_x, click_y, 1, 0)
                            time.sleep(0.01)
                        
                        self.circles_clicked.append(time.time())
                        self.last_activity_time = time.time()
                        
                        click_location = (screen_x, screen_y)
                        self.recent_click_locations.append((click_location, time.time()))
                        
                        current_time = time.time()
                        self.recent_click_locations = [
                            (loc, t) for loc, t in self.recent_click_locations 
                            if current_time - t <= 10.0
                        ]
                        
                time.sleep(0.1)
                
            except Exception as e:
                self.add_console_text(f"Detection error: {e}")
                time.sleep(0.1)
    
    def check_and_auto_start(self):
        """Check if we should auto-start the game"""
        current_time = time.time()
        
        # Don't try to start a new game if we just started one recently (within 3 seconds)
        if current_time - self.last_game_start_time < 3.0:
            return
        
        # Check if we're stuck clicking the same location (probably a player)
        stuck_on_same_spot = self.is_stuck_on_same_location()
        
        # Check if it's been more than 15 seconds since last activity
        if self.last_activity_time > 0 and current_time - self.last_activity_time > 15.0:
            self.add_console_text("⚠️  WARNING: No circle activity for 15+ seconds!")
            self.add_console_text("⚠️  Check your character status in the game.")
            self.last_activity_time = current_time  # Reset to avoid spam
        
        # Clean old clicks (older than 5 seconds)
        self.circles_clicked = [click_time for click_time in self.circles_clicked 
                               if current_time - click_time <= 5.0]
        
        # Start new game if:
        # 1. Less than 5 clicks in past 5 seconds (no game activity), OR
        # 2. We're stuck clicking the same location repeatedly (probably a player)
        if len(self.circles_clicked) < 5 or stuck_on_same_spot:
            if stuck_on_same_spot:
                self.add_console_text("🔄 Detected stuck on same location (probably a player), starting new game...")
            else:
                self.add_console_text("No recent activity detected, attempting to start game...")
            self.start_minigame()
    
    def is_stuck_on_same_location(self):
        """Check if we're repeatedly clicking the same location (indicating we're stuck on a player)"""
        if len(self.recent_click_locations) < self.stuck_click_threshold:
            return False
        
        # Group clicks by approximate location (within 50 pixels)
        location_groups = {}
        for (x, y), timestamp in self.recent_click_locations:
            # Round to nearest 50 pixels to group nearby clicks
            group_key = (round(x / 50) * 50, round(y / 50) * 50)
            if group_key not in location_groups:
                location_groups[group_key] = 0
            location_groups[group_key] += 1
        
        # If any location has been clicked more than threshold times, we're stuck
        max_clicks_same_area = max(location_groups.values()) if location_groups else 0
        
        if max_clicks_same_area >= self.stuck_click_threshold:
            return True
        
        return False
    
    def start_minigame(self):
        """Start the division minigame"""
        try:
            if self.board_location and self.yes_button_location:
                self.add_console_text("Starting minigame sequence...")
                
                self.add_console_text("Starting minigame sequence...")
                
                # Click the division board
                autoit.mouse_click("left", self.board_location[0], self.board_location[1], 1, 0)
                time.sleep(1.5)  # Wait longer for dialog to fully appear
                
                # Click yes button with multiple attempts and slight mouse movement
                base_x, base_y = self.yes_button_location
                click_offsets = [
                    (0, 0),
                    (-2, -2),
                    (2, 2)
                ]
                
                for i, (offset_x, offset_y) in enumerate(click_offsets):
                    click_x = base_x + offset_x
                    click_y = base_y + offset_y
                    autoit.mouse_click("left", click_x, click_y, 1, 0)
                    time.sleep(0.2)
                
                self.last_game_start_time = time.time()
                self.add_console_text("✅ Started division minigame")
            else:
                self.add_console_text("❌ Board and yes button locations not set!")
                
        except Exception as e:
            self.add_console_text(f"Error starting minigame: {e}")
    
    # Main control methods
    def toggle_clicking(self):
        if not self.selected_area:
            self.add_console_text("❌ Please select a screen area first!")
            self.start_clicking_var.set(False)
            return
            
        if self.clicking_active:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def start_clicking(self):
        self.clicking_active = True
        self.start_clicking_var.set(True)
        self.add_console_text("🎯 Circle detection started!")
        
        self.detection_thread = threading.Thread(target=self.click_detection_mode, daemon=True)
        self.detection_thread.start()
    
    def stop_clicking(self):
        self.clicking_active = False
        self.start_clicking_var.set(False)
        self.add_console_text("⏹️ Circle detection stopped")
    
    def stop_and_exit(self):
        self.clicking_active = False
        if self.stop_exit_var.get():
            self.add_console_text("👋 Exiting application...")
            self.root.after(1000, self.close_app)
        else:
            self.stop_exit_var.set(False)
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AutoClickerGUI()
    app.run()