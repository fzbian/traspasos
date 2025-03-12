import flet as ft
from utils import get_employees_with_pins

class AuthView(ft.View):
    def __init__(self, page, target_route):
        """Authentication view for secure access
        
        Args:
            page: The page object
            target_route: The route to navigate to after successful authentication
        """
        super().__init__()
        self.page = page
        self.route = "/auth"
        self.target_route = target_route
        
        # Get authorized employees
        all_employees = get_employees_with_pins()
        self.authorized_employees = [emp for emp in all_employees 
                                    if emp["name"] in ["Fabian Martin", "Nicxy Bermudez"]]
        
        # Setup UI
        self.appbar = ft.AppBar(
            title=ft.Text("Autenticación Requerida"),
            bgcolor=ft.Colors.BLUE,
            center_title=True,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.HOME,
                    tooltip="Volver al inicio",
                    on_click=lambda e: self.page.go("/")
                )
            ],
        )
        
        # Authentication form
        self.employee_dropdown = ft.Dropdown(
            label="Seleccione su nombre",
            options=[
                ft.dropdown.Option(emp["name"]) for emp in self.authorized_employees
            ],
            width=300,
            autofocus=True
        )
        
        self.pin_field = ft.TextField(
            label="Ingrese su PIN",
            password=True,  # Hide the PIN input
            width=300,
        )
        
        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED,
            visible=False
        )
        
        self.login_button = ft.ElevatedButton(
            "Acceder",
            icon=ft.Icons.LOGIN,
            on_click=self.authenticate,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE),
            width=300,
        )
        
        # Create main content
        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Image(
                                src="/assets/logo.png",
                                width=120,
                                height=120,
                                fit=ft.ImageFit.CONTAIN,
                                error_content=ft.Icon(ft.Icons.BUSINESS, size=60, color=ft.Colors.BLUE)  # Fallback icon if logo not found
                            ),
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(bottom=20)
                        ),
                        ft.Text(
                            "Acceso Restringido", 
                            size=20, 
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            "Por favor ingrese sus credenciales para continuar",
                            size=14,
                            color=ft.Colors.GREY_700,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    self.employee_dropdown,
                                    self.pin_field,
                                    self.error_text,
                                    ft.Container(
                                        content=self.login_button,
                                        margin=ft.margin.only(top=10)
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=20
                            ),
                            margin=ft.margin.only(top=20),
                            padding=20,
                            border_radius=10,
                            border=ft.border.all(1, ft.Colors.GREY_400)
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                ),
                alignment=ft.alignment.center,
                padding=20,
                expand=True
            )
        ]
    
    def authenticate(self, e):
        """Verify user credentials"""
        # Show loading state
        self.login_button.disabled = True
        self.login_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        self.page.update()
        
        self.error_text.visible = False
        selected_name = self.employee_dropdown.value
        entered_pin = self.pin_field.value
        
        # Validate inputs
        if not selected_name:
            self.error_text.value = "Por favor seleccione su nombre"
            self.error_text.visible = True
            # Reset button
            self.login_button.disabled = False
            self.login_button.icon = ft.Icons.LOGIN
            self.page.update()
            return
            
        if not entered_pin:
            self.error_text.value = "Por favor ingrese su PIN"
            self.error_text.visible = True
            # Reset button
            self.login_button.disabled = False
            self.login_button.icon = ft.Icons.LOGIN
            self.page.update()
            return
        
        # Add a slight delay to make the loading state visible
        def authenticate_with_delay():
            import time
            time.sleep(0.5)  # Short delay for better UX
            
            # Find the employee and verify PIN
            for employee in self.authorized_employees:
                if employee["name"] == selected_name:
                    if employee["pin"] == entered_pin:
                        # Authentication successful
                        self.show_success_and_redirect()
                        return
                    else:
                        # PIN is incorrect
                        self.show_error("PIN incorrecto. Por favor intente nuevamente.")
                        return
            
            # If we get here, employee not found (shouldn't happen with dropdown)
            self.show_error("Usuario no encontrado")
            
        # Run authentication in a thread to keep UI responsive
        import threading
        threading.Thread(target=authenticate_with_delay).start()
    
    def show_error(self, message):
        """Display an error message"""
        self.error_text.value = message
        self.error_text.visible = True
        # Reset login button
        self.login_button.disabled = False
        self.login_button.icon = ft.Icons.LOGIN
        self.page.update()
    
    def show_success_and_redirect(self):
        """Show success message and redirect to target page"""
        # Display success message
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Autenticación exitosa"),
            bgcolor=ft.Colors.GREEN
        )
        self.page.snack_bar.open = True
        self.page.update()
        
        # Redirect after a short delay
        self.page.splash = ft.ProgressBar()
        self.page.update()
        
        def navigate():
            import time
            time.sleep(1)  # Short delay for better UX
            self.page.go(self.target_route)
        
        import threading
        threading.Thread(target=navigate).start()
