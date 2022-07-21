FROM python:3-slim-bullseye

# https://stackoverflow.com/questions/59812009/what-is-the-use-of-pythonunbuffered-in-docker-file
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH /code

WORKDIR /code

# Can this become only the folder not the whole repo
COPY . /code/

RUN apt-get update && apt-get install -y \
    # helpful packages.
    jq curl awscli \
    && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Specify path on the left side since we build from the highest level
COPY util/docker/requirements.txt /util/docker/requirements.txt

RUN pip install -r /util/docker/requirements.txt

# CMD ["flask", "run"]
# CMD ["python", "destination_app.py"]
CMD ["/bin/bash"]
