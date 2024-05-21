FROM python:3.11-slim as app
WORKDIR /app
COPY /application/ /app/
RUN pip install --upgrade pip 
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]