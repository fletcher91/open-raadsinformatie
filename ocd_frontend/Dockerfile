FROM python:2.7-alpine
MAINTAINER Jurrian Tromp <jurrian@argu.co>

WORKDIR /opt/ori/ocd_frontend
ENV PYTHONPATH=/opt/ori/
COPY requirements.txt /opt/ori/ocd_frontend/requirements.txt

# Install build base for alpine including gcc for Pillow
RUN apk add --update build-base python-dev py-pip jpeg-dev zlib-dev tzdata \
    && pip install cython \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y cython \
    && cp /usr/share/zoneinfo/Europe/Amsterdam /etc/localtime \
    && echo "Europe/Amsterdam" > /etc/timezone \
    && apk del build-base tzdata

COPY . /opt/ori/ocd_frontend

CMD python wsgi.py
