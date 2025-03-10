#!/bin/bash

# Color codes for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====== Python Application Setup ======${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 could not be found. Please install Python 3 and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 is installed${NC}"

# Check if venv module is available
python3 -m venv --help &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Python venv module is not available. Please install it:${NC}"
    echo "  - For Ubuntu/Debian: sudo apt-get install python3-venv"
    echo "  - For Fedora: sudo dnf install python3-venv"
    echo "  - For macOS: Python 3 should already include venv"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}Installing requirements...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Requirements installed${NC}"
else
    echo -e "${YELLOW}Warning: requirements.txt not found${NC}"
fi

# Create a run script if it doesn't exist
if [ ! -f "run.sh" ]; then
    echo -e "${BLUE}Creating run script...${NC}"
    cat > run.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python main.py
EOF
    chmod +x run.sh
    echo -e "${GREEN}✓ Run script created${NC}"
fi

echo -e "\n${GREEN}========== Setup Complete ==========${NC}"
echo -e "${BLUE}To run the application:${NC}"
echo -e "  1. ${YELLOW}source venv/bin/activate${NC} (to activate the virtual environment)"
echo -e "  2. ${YELLOW}python main.py${NC} (to run the application)"
echo -e "  Or simply run: ${YELLOW}./run.sh${NC}"
echo -e "\n${BLUE}To deactivate the virtual environment when done:${NC}"
echo -e "  ${YELLOW}deactivate${NC}"

