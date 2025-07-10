# Installation Guide

## Google Colab Installation

1. **Get your ngrok auth token**
   - Create an account at https://ngrok.com/
   - Get your auth token from the dashboard
   - In Google Colab, go to `Tools` → `Secrets` → `Add a new secret`
   - Add a secret named `NGROK_TOKEN` with your ngrok token as the value

2. **Open the Colab Notebook**
   - Open [duplicate_finder.ipynb](duplicate_finder.ipynb) in Google Colab

3. **Run the Setup Cells**
   - The notebook will:
     - Install required dependencies
     - Clone the repository
     - Set up ngrok authentication
     - Launch the Streamlit app

4. **Access the Application**
   - After running the notebook, you'll see a public URL in the output
   - Click the URL to access the running application

## Docker Installation (Recommended)

The easiest way to run the application is using Docker Compose:

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Use the provided startup script:
```bash
./start-docker.sh
```

Or manually with Docker Compose:
```bash
docker-compose up --build
```

3. Access the application at `http://localhost:8501`

**Docker Volume Mounts:**
- Your home directory is mounted as `/host_home` (read-only)
- The `test_data` directory is mounted as `/host_test_data` (read-only)
- Additional directories can be added to the `docker-compose.yml` volumes section

## Manual Installation

For development or custom deployments:

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app/main.py
```

## Docker Configuration

The Docker setup includes:

- **Volume Mounts**: Access to host directories for scanning
  - `~/.:/host_home:ro` - Your home directory (read-only)
  - `./test_data:/host_test_data:ro` - Test data directory (read-only)
- **Port Mapping**: `8501:8501` for Streamlit access
- **Environment**: Optimized Python and Streamlit configuration

**Customizing Mounts:**
Edit `docker-compose.yml` to add more directories:
```yaml
volumes:
  - .:/app
  - ~/.:/host_home:ro
  - ./test_data:/host_test_data:ro
  - /path/to/your/data:/host_data:ro  # Add custom paths
```

## Running the Application

### Using Docker (Recommended)

The Docker setup provides an isolated environment with all dependencies:

```bash
# Quick start
./start-docker.sh

# Or manually
docker-compose up --build
```

Access the application at `http://localhost:8501`

### Manual Run

To start the application locally:
```bash
streamlit run app/main.py
```
