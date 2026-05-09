from django.contrib import admin

from .models import Category, Comment, Location, Post

admin.site.register([Category, Post, Location, Comment])
