FROM python:2-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY aib2ofx ./aib2ofx
CMD [ "python", "./aib2ofx/main.py" ]