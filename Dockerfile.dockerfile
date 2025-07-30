FROM python:3.9-alpine

WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn

EXPOSE 8000
CMD ["python", "-c", "from fastapi import FastAPI; import uvicorn; app = FastAPI(); app.add_api_route('/', lambda: {'status': 'ok'}); uvicorn.run(app, host='0.0.0.0', port=8000)"]