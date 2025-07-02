FROM python:3.13.2-bookworm

WORKDIR /app

COPY ./flask /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "-w", "4","-b", "0.0.0.0", "app:app"]
#CMD ["python", "app.py"]
