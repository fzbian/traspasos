import flet as ft
from views.home_view import HomeView
from views.traspaso_view import TraspasoView
from views.history_view import HistoryView
from views.entry_view import EntryView
from views.auth_view import AuthView  # Import the new auth view

def main(page: ft.Page):
    # Configure the page
    page.title = "Aplicación de Traspasos"
    page.theme_mode = ft.ThemeMode.LIGHT  # Already set to light theme
    
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
ft.app(target=main, view=ft.WEB_BROWSER)
