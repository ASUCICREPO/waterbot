FROM python:3.11-slim as app

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /usr/ib/apt/lists/*

WORKDIR /app
COPY /application/ /app/
RUN pip install --upgrade pip 
RUN pip install -r requirements.txt
RUN pip install -r requirements_full.txt
RUN chown -R root:root application/docs/chroma
RUN chmod -R 777 application/docs/chroma
EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]