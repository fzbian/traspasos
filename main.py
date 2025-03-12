import flet as ft
from views.home_view import HomeView
from views.traspaso_view import TraspasoView
from views.history_view import HistoryView
from views.entry_view import EntryView
from views.auth_view import AuthView  # Import the new auth view
import queue
import threading
import time

# Create a helper for running functions in the main thread using a queue-based approach
def add_run_in_main_thread(page):
    """Add a helper method to run functions in the main thread"""
    # Create a queue for functions to be executed on the main thread
    callback_queue = queue.Queue()
    
    def run_in_main_thread(function):
        """Queue a function to be executed on the main UI thread"""
        callback_queue.put(function)
        
        # We need to trigger an update to process the queue
        page.update()
    
    def process_callbacks(e=None):
        """Process any pending callbacks in the queue"""
        try:
            # Process all current callbacks in the queue
            while not callback_queue.empty():
                callback = callback_queue.get_nowait()
                if callback:
                    callback()
                callback_queue.task_done()
        except Exception as ex:
            print(f"Error processing callbacks: {str(ex)}")
    
    # Create a background thread that processes callbacks periodically
    def background_processor():
        while True:
            try:
                # Always check callbacks when page update is called
                page.on_update = process_callbacks
                
                # Sleep to avoid using too much CPU
                time.sleep(0.1)  # 100ms interval
            except Exception as ex:
                print(f"Error in background processor: {str(ex)}")
    
    # Add methods to page object
    page.run_in_main_thread = run_in_main_thread
    
    # Start the background processing thread as daemon so it exits when the main thread exits
    processor_thread = threading.Thread(target=background_processor, daemon=True)
    processor_thread.start()

def main(page: ft.Page):
    # Configure the page
    page.title = "Aplicación de Traspasos"
    page.theme_mode = ft.ThemeMode.LIGHT  # Already set to light theme
    
    # Add the run_in_main_thread helper to the page object
    add_run_in_main_thread(page)
    
    # Create a light theme with a blue primary color
    page.theme = ft.Theme(
        color_scheme_seed="blue",  # Use blue as the base color
        use_material3=True,  # Use Material 3 design
        visual_density=ft.VisualDensity.COMFORTABLE  # Corrected attribute name
    )
    
    # Configure light theme specific styles
    page.dark_theme = None  # Disable dark theme entirely
    page.bgcolor = ft.Colors.WHITE  # Fixed: use Colors (uppercase C) instead of colors
    
    page.padding = 20
    page.window_width = 1000
    page.window_height = 800
    page.window_resizable = True
    
    # Create a splash screen
    def show_loading_screen(route):
        # Display loading splash screen when navigating to history view
        if route == "/history":
            page.splash = ft.ProgressBar()
        else:
            page.splash = None
        page.update()
    
    # Navigation state
    def route_change(e):
        # First show loading indicator
        show_loading_screen(page.route)
        
        # Then change views
        page.views.clear()
        if page.route == "/":
            page.views.append(HomeView(page))
        elif page.route == "/traspasos":
            page.views.append(TraspasoView(page))
        elif page.route == "/history":
            page.views.append(HistoryView(page))
        elif page.route == "/auth":
            # Special case for authentication - 
            # Default authentication route is for accessing entries
            page.views.append(AuthView(page, "/entries"))
        elif page.route == "/entries":
            page.views.append(EntryView(page))
        
        page.update()
    
    # Set up routing
    page.on_route_change = route_change
    
    # Initialize the app with the home view
    page.go('/')

# Run the app
if __name__ == "__main__":
    # Always use web browser with port 5000
    ft.app(target=main, view=ft.WEB_BROWSER, port=5000)
else:
    # For module imports or when running with 'flet run'
    ft.app(target=main, view=ft.WEB_BROWSER, port=5000)
