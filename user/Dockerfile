# Image slim : beaucoup plus légère que l'image python complète
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

WORKDIR /app

# copy the requirements file in the workdir
# Le contexte de build est la racine du dépôt (voir docker-compose.yml),
# ce qui permet de copier le requirements.txt commun
COPY requirements.txt .

# install the Python requirements
# --no-cache-dir : n'embarque pas le cache pip dans l'image
RUN pip install --no-cache-dir -r requirements.txt

# copy the app files and directories
# Code, bases JSON et templates du service user
COPY user/ .

# start user.py when the container is started
CMD ["python", "user.py"]
