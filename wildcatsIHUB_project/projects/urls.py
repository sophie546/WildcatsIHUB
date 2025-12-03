
from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('submit/', views.submit_project, name='submit_project'),
    path('project/<int:project_id>/', views.view_project, name='view_project'),
    path('edit_project/<int:project_id>/', views.edit_project, name='edit_project'),
    path('delete_project/<int:project_id>/', views.delete_project, name='delete_project'),
    path('gallery/', views.gallery, name='gallery'),
    
    path('user-profile/<int:user_id>/', views.view_user_profile, name='view_user_profile'), 
]