from django.shortcuts import render


# Create your views here.
def News(request):
    return render(request, "news/News.html")

def ForYouPage(request):
    return render(request, "news/ForYouPage.html")

def Links(request):
    return render(request, "news/Links.html")