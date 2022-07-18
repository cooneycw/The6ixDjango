# https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/
# sudo service apache2 stop (interferes with nginx)

# rm -rf T*
# docker-compose down --remove-orphans
# docker-compose -f docker-compose.prod.yml up -d --build
# docker-compose -f docker-compose.prod.yml exec web python manage.py makemigrations --noinput
# docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
# docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --no-input --clear

# to run in dev, change POSTGRES_HOST to localhost

# start the docker network
# docker network create nginx_network

# start celery worker
# celery -A The6ix worker --loglevel=info
