from django.db import models

class Person(models.Model):
    """
    Represents an actor, director, writer, etc.
    Corresponds to name.basics.tsv
    """
    nconst = models.CharField(max_length=20, primary_key=True, help_text="Alphanumeric unique identifier of the name/person.")
    primary_name = models.CharField(max_length=255, help_text="Primary name of the person.")
    birth_year = models.IntegerField(null=True, blank=True, help_text="Birth year.")
    death_year = models.IntegerField(null=True, blank=True, help_text="Death year.")
    primary_profession = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated list of professions.")
    # known_for_titles is a many-to-many relationship implicitly handled by Movie.principals

    def __str__(self):
        return f"{self.primary_name} ({self.nconst})"

class Movie(models.Model):
    """
    Represents a movie, TV show, etc.
    Corresponds to title.basics.tsv
    """
    tconst = models.CharField(max_length=20, primary_key=True, help_text="Alphanumeric unique identifier of the title.")
    title_type = models.CharField(max_length=50, help_text="Type/format of the title (e.g., movie, short, tvseries).")
    primary_title = models.CharField(max_length=500, help_text="More popular title / the title used for display purposes.")
    original_title = models.CharField(max_length=500, help_text="Original title, in the original language.")
    is_adult = models.BooleanField(default=False, help_text="0: non-adult title; 1: adult title.")
    start_year = models.IntegerField(null=True, blank=True, help_text="Represents the release year of a title.")
    end_year = models.IntegerField(null=True, blank=True, help_text="TV Series end year. Null for non-series.")
    runtime_minutes = models.IntegerField(null=True, blank=True, help_text="Primary runtime of the title, in minutes.")
    genres = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated list of up to three genres.")

    # Relationships
    principals = models.ManyToManyField(
        Person,
        through='Principal',
        related_name='movies_associated',
        help_text="People principally involved with this movie."
    )
    # Directors and writers can also be accessed via Principals or a dedicated Crew model if needed.

    def __str__(self):
        return f"{self.primary_title} ({self.start_year}) ({self.tconst})"

class Rating(models.Model):
    """
    Represents rating information for a movie.
    Corresponds to title.ratings.tsv
    """
    movie = models.OneToOneField(
        Movie,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='rating_info',
        help_text="The movie this rating belongs to."
    )
    average_rating = models.FloatField(null=True, blank=True, help_text="IMDb's weighted average rating.")
    num_votes = models.IntegerField(null=True, blank=True, help_text="Number of votes the movie has received.")

    def __str__(self):
        return f"Rating for {self.movie.primary_title}: {self.average_rating} ({self.num_votes} votes)"

class Principal(models.Model):
    """
    Represents the principal cast/crew for a title.
    Corresponds to title.principals.tsv
    """
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='principal_set', help_text="The movie.")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='principal_set', help_text="The person.")
    ordering = models.IntegerField(help_text="A number to uniquely identify rows for a given titleId.")
    category = models.CharField(max_length=100, help_text="Category of job (e.g., actor, director, writer).")
    job = models.CharField(max_length=255, null=True, blank=True, help_text="Specific job title if applicable (e.g., producer).")
    characters = models.CharField(max_length=500, null=True, blank=True, help_text="Name of the character played, in JSON array format.")

    class Meta:
        unique_together = ('movie', 'person', 'ordering', 'category') # Define a composite key based on typical data structure
        ordering = ['movie', 'ordering'] # Default ordering

    def __str__(self):
        return f"{self.person.primary_name} as {self.category} in {self.movie.primary_title}"

