FROM python:3.6

RUN mkdir /bns
COPY requirements.txt /bns
WORKDIR /bns
RUN pip install -r requirements.txt

ADD . /bns

#ENTRYPOINT ["./_run"]
#ENTRYPOINT ["python"]
#CMD ["main.py"]
