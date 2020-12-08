FROM python:2-slim
WORKDIR /usr/src/aib2ofx
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY aib2ofx .
CMD [ "python", "./main.py" ]