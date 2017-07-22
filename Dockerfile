FROM python:3.6-alpine
ENV PORT=80
WORKDIR /app
COPY MANIFEST.in README.rst requirements.txt setup.py ./
COPY readings/ ./readings/
RUN pip install --no-cache-dir .
CMD [ "readings" ]
