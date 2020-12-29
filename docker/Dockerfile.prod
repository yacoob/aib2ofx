FROM python:3-slim
ARG aib2ofx_version
RUN pip install aib2ofx==${aib2ofx_version} && rm -rf ~/.cache \
    && groupadd aib2ofx && useradd -m -l -g aib2ofx aib2ofx 
USER aib2ofx
WORKDIR /home/aib2ofx
RUN ln -s /.aib2ofx.json && ln -s /out out
CMD [ "python", "-m", "aib2ofx.cli", "-d", "/out" ]