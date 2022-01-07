FROM python:3.8

RUN apt update && apt install ghostscript xvfb -y

COPY . bushfire-drone-simulation
WORKDIR /bushfire-drone-simulation
RUN ./tools/install-dev-env
ENV DISPLAY :99
RUN Xvfb $DISPLAY -screen 0 640x480x24 & python -m coverage run --source=. -m pytest
#RUN python -m coverage xml
