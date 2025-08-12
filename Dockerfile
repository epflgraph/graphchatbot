FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

# Install OS dependencies
RUN /usr/bin/apt-get update \
    && /usr/bin/apt-get install -y --no-install-recommends build-essential libsasl2-dev python-dev-is-python3 libldap2-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in container
WORKDIR /chatbot

# Copy project metadata and expected directories before installing the package
COPY pyproject.toml README.md ./
RUN mkdir -p ./app

# Install python dependencies (from pyproject.toml)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy application code
COPY config.ini es.crt ./
COPY data data
COPY ./app ./app

# Document exposed port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
