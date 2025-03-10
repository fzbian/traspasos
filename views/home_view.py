import flet as ft

class HomeView(ft.View):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.route = "/"
        self.appbar = ft.AppBar(
            title=ft.Text("Sistema de Traspasos"),
            bgcolor=ft.Colors.BLUE,
            center_title=True,
        )
        
        # Create the main content
        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Bienvenido al Sistema de Traspasos", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text("Seleccione una opción:", size=20),
                        ft.ElevatedButton(
                            "Nuevo Traspaso", 
                            icon=ft.Icons.SWAP_HORIZ,
                            on_click=lambda e: self.page.go("/traspasos"),
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.BLUE,
                                padding=15
                            ),
                            width=300
                        ),
                        ft.ElevatedButton(
                            "Nueva Entrada", 
                            icon=ft.Icons.INPUT,
                            on_click=lambda e: self.page.go("/auth"),  # Go to auth instead of directly to entries
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.ORANGE,
                                padding=15
                            ),
                            width=300
                        ),
                        ft.ElevatedButton(
                            "Historial de Traspasos", 
                            icon=ft.Icons.HISTORY,
                            on_click=lambda e: self.page.go("/history"),
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.GREEN,
                                padding=15
                            ),
                            width=300
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20
                ),
                alignment=ft.alignment.center,
                padding=20,
                expand=True
            )
        ]
