FROM python:3.10-slim

WORKDIR /app

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app .

EXPOSE 8501

CMD ["streamlit", "run", "duplicate_finder.py", "--server.address=0.0.0.0", "--server.port=8501"]