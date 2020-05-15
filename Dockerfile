FROM python:3.8-slim
RUN pip install pipenv>=2020.4.1b1
WORKDIR /app
COPY Pipfile Pipfile.lock /app/
RUN pipenv lock --requirements > /requirements.txt

FROM python:3.8-slim
WORKDIR /app
COPY --from=0 /requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY keyvault2kube /app/keyvault2kube

CMD ["/bin/bash"]
