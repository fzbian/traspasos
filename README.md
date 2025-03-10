# Transfer Management System

A web-based application built with Python and Flet for managing and tracking transfers ("traspasos") efficiently. This application provides a user-friendly interface to manage transfer requests, approvals, and records.

## Features

- User authentication and role-based access
- Create and manage transfer requests
- Dashboard with transfer status overview
- Reporting and export capabilities
- Multi-platform support (works on Windows, Linux, and macOS)

## Requirements

- Python 3.7 or higher
- Dependencies as listed in `requirements.txt`:
  - FastAPI
  - Flet
  - NiceGUI
  - Other web-related dependencies

## Installation

### Windows

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Run the setup script:
   ```
   .\setup.bat
   ```

3. The setup script will:
   - Create a virtual environment
   - Install all required dependencies
   - Show instructions for activating the environment and running the application

4. To run the application after setup:
   ```
   .\venv\Scripts\activate
   python main.py
   ```

### Linux/macOS

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Make the setup script executable and run it:
   ```
   chmod +x setup.sh
   ./setup.sh
   ```

3. The setup script will:
   - Create a virtual environment
   - Install all required dependencies
   - Show instructions for activating the environment and running the application

4. To run the application after setup:
   ```
   source venv/bin/activate
   python main.py
   ```

## Automatic Server Setup

After cloning the repository on your server, you can automate the installation and setup process:

### For Linux servers:
```
git clone <repository-url>
cd <repository-folder>
chmod +x setup.sh
./setup.sh
```

### For Windows servers:
```
git clone <repository-url>
cd <repository-folder>
.\setup.bat
```

## Running in Production

For a production environment, it's recommended to:

1. Set up a proper web server (Nginx, Apache) as a reverse proxy
2. Use a process manager (such as Supervisor, PM2, or systemd)
3. Configure proper security settings

Example systemd service configuration (Linux):

```
[Unit]
Description=Transfer Management System
After=network.target

[Service]
User=<your-user>
WorkingDirectory=/path/to/repository
ExecStart=/path/to/repository/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Development

To start the application in development mode:

```
# With virtual environment activated
python main.py
```

The application will be available at http://localhost:8000 by default.

## Structure

- `main.py` - Main application entry point
- `requirements.txt` - List of Python dependencies
- `setup.bat` - Windows setup script
- `setup.sh` - Linux/macOS setup script

## Troubleshooting

- If you encounter issues with dependencies, try updating pip: 
  ```
  pip install --upgrade pip
  ```
  
- For permission issues on Linux/macOS when running the setup script, make sure it is executable:
  ```
  chmod +x setup.sh
  ```

- If the application fails to start, check that all dependencies were installed correctly:
  ```
  pip list
  ```

## License

[Include license information here]

## Contributors

[Include contributors information here]

