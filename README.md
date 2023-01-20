# orthocal-python
Orthocal Rewritten in Python

Install dependencies:

	pip install -r requirements.txt

Load initial data:

	./manage.py collectstatic --noinput
	./manage.py migrate
	./manage.py loaddata calendarium
	./manage.py loaddata commemorations

Run developement server:

	./manage.py runserver

Run tests:

	./manage.py test --keepdb
