from django.urls import path
from . import views
from dashboard.views import user_profile
from django.views.generic import RedirectView  # ADD THIS

urlpatterns = [
    path('', views.landing_page, name='landing_page'), 
    path('dashboard/', views.dashboard, name='dashboard'),
    path('user-profile/', views.user_profile, name='user_profile'),
    path('view-supabase-data/', views.view_all_supabase_data, name='view_supabase_data'),
    path('gallery/', views.gallery, name='gallery'),
    
    # ADD THIS LINE - REDIRECT /submit-project/ to /submit/
    path('submit-project/', RedirectView.as_view(url='/submit/', permanent=False)),
    
    # Project URLs
    path('projects/add/', views.add_project, name='add_project'),
    path('projects/<int:project_id>/', views.view_project, name='view_project'),
    path('projects/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    
    # Supabase integration endpoints
    path('save-profile-to-supabase/', views.save_profile_to_supabase, name='save_profile_to_supabase'),
    path('user-profile/save/', views.save_profile_to_supabase, name='save_profile'),
    path('user-profile/save-project/', views.save_project_to_supabase, name='save_project'),
    path('user-profile/data/', views.get_supabase_profile_data, name='get_profile_data'),
]