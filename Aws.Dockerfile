FROM public.ecr.aws/lambda/python:3.9

WORKDIR /opt

RUN yum install -y wget tar gzip gcc openssl-devel bzip2-devel libffi-devel make zip
RUN wget https://www.python.org/ftp/python/3.9.6/Python-3.9.6.tgz &&\
    tar -xzf Python-3.9.6.tgz
RUN cd Python-3.9.6 && \
    ./configure --enable-optimizations &&\
    make altinstall
RUN python3.9 --version \
    python3.9 -m pip install --upgrade pip && \
    python3.9 -m pip install pipenv
COPY src /var/task
RUN pipenv install -r /var/task/requirements.txt
CMD ["/var/task/aws_handler.invoke"]