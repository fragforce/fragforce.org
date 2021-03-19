# Base Image
FROM python:3.8
RUN pip install pipenv

# Having an editor is very nice
RUN apt-get update && apt-get install -y \
  vim \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install

VOLUME /code

CMD /bin/bash && wait
