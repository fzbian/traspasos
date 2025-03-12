#!/bin/bash

# Display ASCII art banner
echo "╔════════════════════════════════════════════════════╗"
echo "║                                                    ║"
echo "║        SISTEMA DE TRASPASOS Y ENTRADAS             ║"
echo "║                                                    ║"
echo "╚════════════════════════════════════════════════════╝"

echo ""
echo "Iniciando servidor en el puerto 5000..."
echo "Una vez iniciado, puede acceder a la aplicación en:"
echo ""
echo "   http://localhost:5000"
echo ""
echo "Presione Ctrl+C para detener el servidor"
echo "════════════════════════════════════════════════════"
echo ""

# Run the Python application with the web view on port 5000
python main.py
