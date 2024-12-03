from django.shortcuts import render

# Create your views here.
def Latest_News(request):
    return render(request, 'LatestNews.html')