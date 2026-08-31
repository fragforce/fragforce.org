# Base Image
FROM python:3.13

# Having an editor is very nice
RUN apt-get update && apt-get install -y \
  vim sqlite3 postgresql \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.7@sha256:9e049ccf355e1c6d11416ba84760b4af443e5d2f0d45867c03b36744beb6ee22 /usr/local/bin/uv /usr/local/bin/uv

WORKDIR /code

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-build --no-binary-package django-memoize --extra dev

VOLUME /code

CMD ["/bin/bash"]