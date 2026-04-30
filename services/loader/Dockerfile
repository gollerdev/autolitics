FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["data_loading_service.lambda_handler"]
