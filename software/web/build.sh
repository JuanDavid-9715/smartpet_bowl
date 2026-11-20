#!/usr/bin/env bash
# Lo ejecuta Render en cada despliegue.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Los estaticos los sirve WhiteNoise: hay que juntarlos antes de arrancar.
python manage.py collectstatic --no-input
