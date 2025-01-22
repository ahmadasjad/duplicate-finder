**Explanation:**
*   **`FROM python:3.10-slim`**: Uses the official Python 3.10 slim image as the base.
*   **`WORKDIR /app`**: Sets the working directory inside the container to `/app`.
*   **`COPY app/requirements.txt .`**: Copies the `requirements.txt` file to the working directory.
*   **`RUN pip install --no-cache-dir -r requirements.txt`**: Installs the Python dependencies.
*   **`COPY app .`**: Copies the rest of your application code into the working directory.
*   **`EXPOSE 8501`**: Exposes port 8501 for Streamlit.
*   **`CMD ["streamlit", "run", "duplicate_finder.py", "--server.address=0.0.0.0", "--server.port=8501"]`**: Command to run the Streamlit app when the container starts, with the server accessible on all interfaces (0.0.0.0) and port 8501.