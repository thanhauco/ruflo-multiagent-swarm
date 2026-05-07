FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md /app/
COPY ruflo /app/ruflo
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "ruflo.api:app", "--host", "0.0.0.0", "--port", "8000"]
