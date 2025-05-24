from django.urls import path
from . import views

app_name = 'movies' # Namespace for URLs

urlpatterns = [
    path('search/', views.search_movies, name='search_movies'),
    path('movie/<str:tconst>/', views.movie_detail, name='movie_detail'),
]
