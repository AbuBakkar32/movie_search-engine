from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Prefetch
from .models import Movie, Person, Principal, Rating

def search_movies(request):
    """
    Handles movie search requests.
    Searches by primary_title.
    """
    query = request.GET.get('q', '')
    movies_found = None

    if query:
        # Search for movies where the primary_title contains the query string (case-insensitive)
        # Prefetch related rating information to avoid N+1 queries in the template
        movies_found = Movie.objects.filter(
            primary_title__icontains=query
        ).prefetch_related(
            Prefetch('rating_info', queryset=Rating.objects.all().only('average_rating', 'num_votes'))
        ).only(
            'tconst', 'primary_title', 'start_year', 'runtime_minutes', 'genres'
        )[:50] # Limit results for performance

    return render(request, 'movies/search_results.html', {
        'query': query,
        'movies': movies_found
    })

def movie_detail(request, tconst):
    """
    Displays detailed information for a specific movie.
    """
    # Get the movie object or return a 404 error if not found
    # Use select_related and prefetch_related to optimize database queries by fetching
    # related objects in a single query.
    movie = get_object_or_404(
        Movie.objects.prefetch_related(
            Prefetch('rating_info', queryset=Rating.objects.all().only('average_rating', 'num_votes')),
            Prefetch('principal_set', queryset=Principal.objects.select_related('person').filter(
                # Fetch only actors and directors for simplicity, can be expanded
                Q(category='actor') | Q(category='director')
            ).order_by('ordering').only('person__primary_name', 'category', 'characters', 'person__nconst'))
        ),
        tconst=tconst
    )

    # Separate principals into actors and directors for easier template rendering
    actors = []
    directors = []
    for principal in movie.principal_set.all(): # Access the prefetched data
        if principal.category == 'actor':
            actors.append(principal)
        elif principal.category == 'director':
            directors.append(principal)
            
    # Get rating information safely
    rating = movie.rating_info if hasattr(movie, 'rating_info') else None

    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'rating': rating,
        'actors': actors,
        'directors': directors
    })
