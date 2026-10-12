from django.db import models

# Create your models here.
class Students(models.Model):
    no = models.AutoField(primary_key=True) # primary_key는 
    name = models.CharField(max_length=100)
    major = models.CharField(max_length=100)
    age = models.IntegerField(default=0)
    gender = models.CharField(max_length=30)
    hobby = models.CharField(max_length=100)
    sdate = models.DateTimeField(auto_now=True,blank=True)
    grade = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.no},{self.name},{self.major},{self.grade},{self.age},{self.gender},{self.hobby},{self.sdate}"