from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Project, Category
from accounts.models import UserProfile
from django.utils import timezone
from datetime import timedelta

@login_required
def view_user_profile(request, user_id):
    """View another user's profile (read-only)"""
    viewed_user = get_object_or_404(User, id=user_id)
    user_profile, created = UserProfile.objects.get_or_create(user=viewed_user)
    user_projects = Project.objects.filter(author=user_profile).order_by('-created_at')
    
    is_own_profile = (request.user.id == user_id)
    
    context = {
        'viewed_user': viewed_user,
        'viewed_profile': user_profile,
        'projects': user_projects,
        'is_own_profile': is_own_profile,
        'user': request.user
    }
    return render(request, 'dashboard/view_user_profile.html', context)

def view_project(request, project_id):
    """View individual project details"""
    project = get_object_or_404(Project, id=project_id)
    
    # Increment view count safely
    try:
        project.views += 1
        project.save(update_fields=['views'])
    except Exception:
        pass # Ignore errors if DB is busy to prevent broken pipe
        
    return render(request, 'projects/view_project.html', {'project': project})

@login_required
def delete_project(request, project_id):
    """Delete a project (only by owner)"""
    user_profile = UserProfile.objects.get(user=request.user)
    project = get_object_or_404(Project, id=project_id, author=user_profile)
    project_title = project.title
    project.delete()
    messages.success(request, f"Project '{project_title}' deleted successfully!")
    return redirect('user_profile')              

def home(request):
    """Home page with all projects and feed"""
    # Show only approved projects in main feed
    all_projects = Project.objects.filter(status='Approved').select_related('author__user').order_by('-created_at')
    
    my_recent_projects = Project.objects.none()
    if request.user.is_authenticated:
        try:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            # Show ALL user's own projects (including pending) in their personal feed
            my_recent_projects = Project.objects.filter(author=user_profile).order_by('-created_at')[:6]
        except Exception:
            pass
    
    return render(request, 'projects/home_page.html', {
        'feed_projects': all_projects,
        'my_recent_projects': my_recent_projects
    })

@login_required
def submit_project(request):
    """Submit a new project"""
    # 1. Fetch categories for the dropdown (Crucial for Step 4)
    categories = Category.objects.all().order_by('name')

    if request.method == "POST":
        try:
            # Get form data
            title = request.POST.get("title", "").strip()
            
            # 2. FIXED: Check both possible names for description to prevent "None" error
            description = (request.POST.get("description") or request.POST.get("project-description") or "").strip()
            
            category_input = request.POST.get("category", "").strip()
            other_category = request.POST.get("other_category", "").strip()
            
            github_url = request.POST.get("github_url", "").strip()
            live_demo = request.POST.get("live_demo", "").strip()
            video_demo = request.POST.get("video_demo", "").strip()
            tech_used = request.POST.get("tech_used", "").strip()
            screenshot = request.FILES.get("screenshot")

            # Handle "other" category
            final_category = category_input
            if category_input == "other":
                if not other_category:
                    messages.error(request, "Please specify the category when selecting 'Other'.")
                    return render(request, 'projects/project_form.html', {'categories': categories})
                final_category = other_category

            # Validate required fields
            if not title or not description or not final_category or not github_url or not tech_used:
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'projects/project_form.html', {'categories': categories})

            # Validate GitHub URL format
            if not github_url.startswith(('http://', 'https://')):
                messages.error(request, "Please enter a valid GitHub URL.")
                return render(request, 'projects/project_form.html', {'categories': categories})

            # Get or create UserProfile
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)

            # Create project
            project = Project.objects.create(
                author=user_profile,
                title=title,
                description=description,
                category=final_category,
                github_url=github_url,
                live_demo=live_demo if live_demo else None,
                video_demo=video_demo if video_demo else None,
                tech_used=tech_used,
                screenshot=screenshot
            )

            messages.success(request, f"Project '{title}' submitted successfully!")
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)

        except Exception as e:
            messages.error(request, f"Error submitting project: {str(e)}")
            # Pass categories back so dropdown persists
            return render(request, 'projects/project_form.html', {'categories': categories})

    # Pass categories to template for the dropdown
    return render(request, 'projects/project_form.html', {'categories': categories})

def gallery(request):
    """Project gallery view - publicly accessible (only approved projects)"""
    projects = Project.objects.filter(status='Approved').select_related('author__user').order_by('-created_at')
    return render(request, "projects/gallery.html", {"projects": projects})

@login_required
def user_projects_profile(request):
    """User profile with their projects"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_projects = Project.objects.filter(author=user_profile).order_by('-created_at')
    except UserProfile.DoesNotExist:
        user_profile = None
        user_projects = []
        
    return render(request, 'dashboard/userProfile.html', {  
        'projects': user_projects,
        'user': request.user
    })

@login_required
def edit_project(request, project_id):
    """Edit an existing project"""
    user_profile = UserProfile.objects.get(user=request.user)
    project = get_object_or_404(Project, id=project_id, author=user_profile)
    # Fetch categories for the dropdown
    categories = Category.objects.all().order_by('name')
    
    if request.method == "POST":
        try:
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            
            # Category Logic
            category_input = request.POST.get("category", "").strip()
            other_category = request.POST.get("other_category", "").strip()
            
            final_category = category_input
            if category_input == "other":
                if not other_category:
                    messages.error(request, "Please specify the category.")
                    return render(request, 'projects/project_form.html', {'project': project, 'editing': True, 'categories': categories})
                final_category = other_category

            github_url = request.POST.get("github_url", "").strip()
            live_demo = request.POST.get("live_demo", "").strip()
            video_demo = request.POST.get("video_demo", "").strip()
            tech_used = request.POST.get("tech_used", "").strip()

            if not title or not description or not final_category or not github_url or not tech_used:
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'projects/project_form.html', {'project': project, 'editing': True, 'categories': categories})

            if not github_url.startswith(('http://', 'https://')):
                messages.error(request, "Please enter a valid GitHub URL.")
                return render(request, 'projects/project_form.html', {'project': project, 'editing': True, 'categories': categories})

            project.title = title
            project.description = description
            project.category = final_category
            project.github_url = github_url
            project.live_demo = live_demo if live_demo else None
            project.video_demo = video_demo if video_demo else None
            project.tech_used = tech_used
            
            if 'screenshot' in request.FILES and request.FILES['screenshot']:
                project.screenshot = request.FILES['screenshot']
            
            project.save()
            messages.success(request, f"Project '{project.title}' updated successfully!")
            
            # Redirect back to previous page using next parameter
            next_url = request.POST.get('next') or 'user_profile'
            return redirect(next_url)
            
        except Exception as e:
            messages.error(request, f"Error updating project: {str(e)}")
            return render(request, 'projects/project_form.html', {'project': project, 'editing': True, 'categories': categories})
    
    context = {
        'project': project,
        'editing': True,
        'categories': categories
    }
    return render(request, 'projects/project_form.html', context)