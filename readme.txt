# https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/

# docker-compose -f docker-compose.prod.yml up -d --build
# docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
# docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --no-input --clear