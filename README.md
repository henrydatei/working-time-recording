# belegarbeit
Belegarbeit an der TU-Dresden am Lehrstuhl für Lehrstuhl für Wirtschaftsinformatik, insb. Intelligente Systeme und Dienste

Code for a working time recording system for student assistants as a Django web application.

## Installation
- Clone the repository
- Install requirements with `pip install -r requirements.txt`
- Run `python manage.py runserver` to start the server

This repo contains a sqlite database with some example data. To reset the database, delete the file `db.sqlite3` and run `python manage.py migrate` to create a new database (start the server with `python manage.py runserver`). After that, you can create a superuser with `python manage.py createsuperuser` and login to the admin interface at `localhost:8000/admin` to create new users.

In the example database, there are multiple users with the following passwords:
```
admin:admin
shkofficer:shkofficer
supervisor1:supervisor1
supervisor2:supervisor2
user1:user1
user2:user2
user4:user4
```
The users `user1`, `user2` and `user4` are student assistants. The users `supervisor1` and `supervisor2` are supervisors, `shkofficer` is a student assistant officer. The user `admin` is a superuser. Each student assistant can have multiple contracts and each contract is assigned to a supervisor. The `shkofficer` has the overview over all student assistants while the supervisors only see the student assistants assigned to them.