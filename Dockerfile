FROM python:3.14.3-slim

ENV TZ=Europe/Kiev

# Add a non-root user
RUN useradd -m appuser

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and ensure the appuser owns it
COPY . .
RUN chown -R appuser:appuser /usr/src/app

USER appuser

CMD [ "python", "main.py" ]
