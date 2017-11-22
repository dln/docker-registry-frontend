FROM pstauffer/python3

MAINTAINER confirm IT solutions, pstauffer

RUN addgroup -g 666 flask && \
    adduser -u 666 -G flask -h /home/flask -g "flask User" -s /bin/sh -D flask && \
    mkdir /home/flask/templates

COPY docker_registry_frontend/requirements.txt /home/flask/requirements.txt
COPY docker_registry_frontend/*.py /home/flask/
COPY docker_registry_frontend/templates/* /home/flask/templates/

EXPOSE 5000

RUN pip install --no-cache-dir -r /home/flask/requirements.txt && \
    chown -R flask:flask /home/flask && \
    chmod -R o-rwx /home/flask

USER flask

CMD python /home/flask/run.py
