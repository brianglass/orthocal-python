# orthocal-python
Orthocal Rewritten in Python

Install dependencies:

	pip install -r requirements.txt

Load initial data:

	./manage.py collectstatic --noinput
	./manage.py migrate
	./manage.py loaddata calendarium/fixtures/*
	./manage.py loaddata commemorations/fixtures/*
    ./manage.py loaddata calendarium/fixtures/*

Run developement server:

	./manage.py runserver
