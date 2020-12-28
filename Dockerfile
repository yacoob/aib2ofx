FROM python:3-slim
WORKDIR /usr/src/aib2ofx
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY aib2ofx .
WORKDIR /usr/src
CMD [ "python", "-m", "aib2ofx.cli" ]