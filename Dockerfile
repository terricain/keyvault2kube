FROM python:3.8-slim
RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry export -f requirements.txt > /requirements.txt

FROM python:3.8-slim
WORKDIR /app
COPY --from=0 /requirements.txt /app/requirements.txt
RUN pip install --require-hashes -r /app/requirements.txt
COPY keyvault2kube /app/keyvault2kube

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "keyvault2kube.server"]
