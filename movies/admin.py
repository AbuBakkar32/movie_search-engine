from django.contrib import admin
from .models import Person, Movie, Rating, Principal

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('nconst', 'primary_name', 'birth_year', 'primary_profession')
    search_fields = ('primary_name', 'nconst')

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('tconst', 'primary_title', 'title_type', 'start_year', 'runtime_minutes', 'genres')
    search_fields = ('primary_title', 'tconst', 'original_title')
    list_filter = ('title_type', 'is_adult', 'start_year')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('movie_primary_title', 'average_rating', 'num_votes')
    search_fields = ('movie__primary_title', 'movie__tconst')
    list_select_related = ('movie',) # Optimization for admin

    def movie_primary_title(self, obj):
        return obj.movie.primary_title
    movie_primary_title.short_description = 'Movie Title'
    movie_primary_title.admin_order_field = 'movie__primary_title'


@admin.register(Principal)
class PrincipalAdmin(admin.ModelAdmin):
    list_display = ('movie_title', 'person_name', 'category', 'job', 'ordering')
    search_fields = ('movie__primary_title', 'person__primary_name', 'category')
    list_filter = ('category',)
    autocomplete_fields = ['movie', 'person'] # Makes selection easier

    def movie_title(self, obj):
        return obj.movie.primary_title
    movie_title.short_description = 'Movie'

    def person_name(self, obj):
        return obj.person.primary_name
    person_name.short_description = 'Person'
