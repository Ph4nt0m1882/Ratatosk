FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir mcp

COPY server.py /app/server.py

ENTRYPOINT ["python", "-u", "/app/server.py"]
