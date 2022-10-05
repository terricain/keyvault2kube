FROM python:3.10-slim
RUN pip install poetry poetry-dynamic-versioning
WORKDIR /app
ADD . .
RUN poetry build

FROM python:3.10-slim
COPY --from=0 /app/dist/*.whl /
RUN pip install keyvault2kube-*.*.*-py3-none-any.whl

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "keyvault2kube.server"]
