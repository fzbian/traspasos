#!/bin/bash

# Display ASCII art banner
echo "╔════════════════════════════════════════════════════╗"
echo "║                                                    ║"
echo "║        SISTEMA DE TRASPASOS Y ENTRADAS             ║"
echo "║                                                    ║"
echo "╚════════════════════════════════════════════════════╝"

echo ""
echo "Activando entorno virtual..."

# Check if the virtual environment directory exists
if [ -d "venv" ]; then
    # Activate the virtual environment
    source venv/bin/activate
elif [ -d ".venv" ]; then
    # Alternative virtual environment directory name
    source .venv/bin/activate
else
    echo "Error: No se encontró el entorno virtual (venv o .venv)"
    echo "Por favor, cree un entorno virtual con 'python -m venv venv' e instale las dependencias"
    exit 1
fi

echo "Entorno virtual activado: $(which python)"
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

# Deactivate the virtual environment when done
deactivate
