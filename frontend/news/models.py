from django.db import models
from django.contrib.auth.models import AbstractUser

# Benutzer-Modell
class User(AbstractUser):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Angestellter', 'Angestellter'),
    ]
    LOCATION_CHOICES = [
        ('Kaiserlautern', 'Kaiserlautern'),
        ('Landau', 'Landau'),
        ('Beides', 'Beides'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    job_offer = models.BooleanField(default=False)
    uni_info = models.BooleanField(default=False)
    events = models.BooleanField(default=False)
    external_uni = models.BooleanField(default=False)
    surveys = models.BooleanField(default=False)
    interessiert = models.ManyToManyField('Fachschaft',blank=True)

class Fachschaft(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    
class Rundmail(models.Model):
    id = models.IntegerField()
    url = models.URLField()

class ExterneWebsite(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField() 

class InterneWebsite(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

class News(models.Model):
    LOCATION_CHOICES = [
        ('Kaiserlautern', 'Kaiserlautern'),
        ('Landau', 'Landau'),
        ('Beides', 'Beides'),
    ]

    link = models.URLField()
    title = models.CharField(max_length=255)
    created_date = models.DateField()
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    job_offer = models.BooleanField()
    uni_info = models.BooleanField()
    events = models.BooleanField()
    external_uni = models.BooleanField()
    surveys = models.BooleanField()

    Fachschaft = models.ForeignKey(Fachschaft,blank=True)
    ExterneWebsite = models.ForeignKey(ExterneWebsite,blank=True)
    Rundmail = models.ForeignKey(Rundmail,blank=True)
    InterneWebsite = models.ForeignKey(InterneWebsite,blank=True)

    quelle_typ = models.CharField(max_length=20, choices=[('Fachschaft','Fachschaft'),('ExterneWebsite','ExterneWebsite'),('Rundmail','Rundmail'),('InterneWebsite','InterneWebsite')])

class NewsCategory(models.Model):
    CATEGORY_CHOICES = [
        ('Quelle', 'Quelle'),
        ('Jobangebot', 'Jobangebot'),
        ('Allg Infos', 'Allg Infos'),
        ('Veranstaltungen', 'Veranstaltungen'),
        ('Uni Extern', 'Uni Extern'),
        ('Umfragen', 'Umfragen'),
    ]

    news = models.ForeignKey(News, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
