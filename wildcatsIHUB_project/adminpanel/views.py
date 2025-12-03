from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q 
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils import timezone
from projects.models import Project
from accounts.models import UserProfile 
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AdminUserForm, AdminProfileForm, UserManagementForm, UserProfileEditForm, ProjectForm
from django.core.mail import send_mail
from django.conf import settings
import json
import csv
from django.http import HttpResponse
from .models import AuditLog

def is_admin(user):
    return user.is_active and user.is_staff

@login_required(login_url='/accounts/login/') 
@user_passes_test(is_admin)                     
def admin_dashboard(request):
    # 1. Existing Counts
    total_users = UserProfile.objects.count()
    approved_projects_count = Project.objects.filter(status='Approved').count()
    ongoing_projects_count = Project.objects.filter(Q(status='Active') | Q(status='Approved')).count()
    
    # 2. Get Data for the Chart (Count by status)
    pending_count = Project.objects.filter(status='Pending').count()
    rejected_count = Project.objects.filter(status='Rejected').count()
    
    # Prepare the list: [Pending, Approved, Rejected]
    # We pass this list to the HTML to draw the chart
    chart_data = [pending_count, approved_projects_count, rejected_count]

    # 3. Recent Projects List
    recent_projects = Project.objects.all().order_by('-created_at')[:5] 
    for project in recent_projects:
        project.badge_class = 'active' if project.status == 'Active' else (
            'completed' if project.status == 'Completed' else 'pending'
        )

    context = {
        'total_users': total_users,
        'approved_projects_count': approved_projects_count,
        'ongoing_projects_count': ongoing_projects_count,
        'projects': recent_projects, 
        'admin_name': request.user.get_full_name() or request.user.username,
        
        # 4. Pass the chart data safely as JSON
        'chart_data_json': json.dumps(chart_data), 
    }
    return render(request, "adminpanel/admin_dashboard.html", context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
@require_POST
def bulk_project_action(request):
    """Handles bulk approval/rejection AND sends emails."""
    project_ids = request.POST.getlist('project_ids')
    action = request.POST.get('action')

    if not project_ids:
        messages.warning(request, "No projects selected.")
        return redirect('approvals')

    projects = Project.objects.filter(id__in=project_ids).select_related('author__user')
    success_count = 0

    for project in projects:
        student_email = project.author.user.email
        student_name = project.author.user.first_name or project.author.user.username
        
        # 1. Update Data
        if action == 'approve':
            project.status = 'Approved'
            project.approved_at = timezone.now()
            project.approved_by = request.user
            # Log the action
            AuditLog.objects.create(
                admin=request.user, 
                action='APPROVE', 
                target_object=f"Project: {project.title}", 
                details="Bulk approval"
            )
            
            subject = f"🎉 Good News! '{project.title}' was Approved"
            message = f"Hi {student_name},\n\nYour project '{project.title}' has been APPROVED.\n\n- Wildcats iHub Team"
            
        elif action == 'reject':
            project.status = 'Rejected'
            project.approved_at = None
            project.approved_by = request.user
            # Log the action
            AuditLog.objects.create(
                admin=request.user, 
                action='REJECT', 
                target_object=f"Project: {project.title}", 
                details="Bulk rejection"
            )
            
            subject = f"Update regarding '{project.title}'"
            message = f"Hi {student_name},\n\nUnfortunately, your project '{project.title}' was NOT approved.\n\n- Wildcats iHub Team"
        
        project.save()
        success_count += 1

        # 2. Send Email - CHANGED fail_silently TO FALSE
        if student_email:
            try:
                print(f"Attempting to send email to {student_email}...") # Debug print
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER, 
                    [student_email],
                    fail_silently=False,  # <--- CRITICAL CHANGE: Now it will crash if settings are wrong
                )
                print("Email sent successfully!")
            except Exception as e:
                print(f"❌ CRITICAL EMAIL ERROR: {e}") # This will show in your terminal
                # We don't stop the loop, but we print the error

    if action == 'approve':
        messages.success(request, f"{success_count} projects approved.")
    else:
        messages.warning(request, f"{success_count} projects rejected.")

    return redirect('approvals')

@login_required(login_url='/accounts/login/') 
@user_passes_test(is_admin)
def approvals(request):
    # 1. Base Query
    projects_list = Project.objects.filter(status='Pending').select_related('author__user').order_by('created_at')
    
    # 2. Search Logic
    query = request.GET.get('q')
    if query:
        projects_list = projects_list.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) | 
            Q(author__user__username__icontains=query)
        )

    # 3. Pagination
    paginator = Paginator(projects_list, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "pending_projects": page_obj,
    }
    return render(request, "adminpanel/approvals.html", context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
@require_POST
def approve_reject_project(request, pk):
    """Handles updating a project's status, date, admin user, sending email, AND logging the action."""
    project = get_object_or_404(Project, pk=pk)
    action = request.POST.get('action') 
    
    # Get student email (Ensure your User model has emails!)
    student_email = project.author.user.email
    student_name = project.author.user.first_name or project.author.user.username
    
    if action == 'Approve':
        project.status = 'Approved'
        project.approved_at = timezone.now()
        project.approved_by = request.user
        
        # --- NEW: Record Audit Log ---
        AuditLog.objects.create(
            admin=request.user,
            action='APPROVE',
            target_object=f"Project: {project.title}",
            details=f"Approved project ID {project.id}"
        )
        # -----------------------------
        
        subject = f"🎉 Good News! '{project.title}' was Approved"
        message = (
            f"Hi {student_name},\n\n"
            f"We are happy to inform you that your project '{project.title}' has been APPROVED by the admin team.\n"
            f"It is now visible in the public gallery.\n\n"
            f"Great work!\n"
            f"- Wildcats iHub Team"
        )
        alert_msg = f'Project "{project.title}" approved and email sent.'
        
    elif action == 'Reject':
        project.status = 'Rejected'
        project.approved_at = None
        project.approved_by = request.user
        
        # --- NEW: Record Audit Log ---
        AuditLog.objects.create(
            admin=request.user,
            action='REJECT',
            target_object=f"Project: {project.title}",
            details=f"Rejected project ID {project.id}"
        )
        # -----------------------------
        
        subject = f"Update regarding your project '{project.title}'"
        message = (
            f"Hi {student_name},\n\n"
            f"Thank you for your submission. Unfortunately, your project '{project.title}' was NOT approved at this time.\n"
            f"Please review the submission guidelines and try again.\n\n"
            f"- Wildcats iHub Team"
        )
        alert_msg = f'Project "{project.title}" rejected and email sent.'
        
    else:
        messages.error(request, "Invalid action requested.")
        return redirect('approvals')

    # Save changes
    project.save()

    # Send the email (Wrapped in try/except so it doesn't crash if email fails)
    if student_email:
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER, 
                [student_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            # We add a warning so the admin knows the email failed, but the approval still happened
            messages.warning(request, f"Project updated, but email failed: {e}")
            return redirect('approvals')

    messages.success(request, alert_msg)
    return redirect('approvals')

@login_required(login_url='/accounts/login/') 
@user_passes_test(is_admin)
def submissions(request):
    all_submissions = Project.objects.all().select_related('author').order_by('-created_at')
    submission_stats = {
        "total": all_submissions.count(),
        "approved": Project.objects.filter(status='Approved').count(),
        "rejected": Project.objects.filter(status='Rejected').count(),
        "pending": Project.objects.filter(status='Pending').count(),
    }
    context = { "submissions": all_submissions, "stats": submission_stats }
    return render(request, "adminpanel/submissions.html", context)

@login_required(login_url='/accounts/login/') 
@user_passes_test(is_admin)
def user_management(request):
    users_list = UserProfile.objects.all().select_related('user').order_by('user__username')
    
    query = request.GET.get('q')
    if query:
        users_list = users_list.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(department__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users_list = users_list.filter(user__is_active=True)
    elif status_filter == 'inactive':
        users_list = users_list.filter(user__is_active=False)

    paginator = Paginator(users_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = { "users": page_obj }
    return render(request, "adminpanel/user_management.html", context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def user_detail(request, pk):
    user_instance = get_object_or_404(User, pk=pk)
    profile_instance = user_instance.userprofile 
    context = { 'user_to_view': user_instance, 'profile': profile_instance }
    return render(request, 'adminpanel/user_detail.html', context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
@transaction.atomic
def user_edit(request, pk):
    user_instance = get_object_or_404(User, pk=pk)
    profile_instance, created = UserProfile.objects.get_or_create(user=user_instance)
    
    if request.method == 'POST':
        user_form = UserManagementForm(request.POST, instance=user_instance)
        profile_form = UserProfileEditForm(request.POST, instance=profile_instance)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f'User {user_instance.username} updated successfully!')
            return redirect('user_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserManagementForm(instance=user_instance)
        profile_form = UserProfileEditForm(instance=profile_instance)
        
    context = { 'user_to_edit': user_instance, 'user_form': user_form, 'profile_form': profile_form }
    return render(request, 'adminpanel/user_edit.html', context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def user_delete(request, pk):
    user_instance = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        if user_instance.is_superuser:
            messages.error(request, "Cannot delete superuser accounts.")
            return redirect('user_management')
            
        # --- NEW LOGGING CODE ---
        AuditLog.objects.create(
            admin=request.user,
            action='DELETE',
            target_object=f"User: {user_instance.username}",
            details=f"Permanently deleted user account ({user_instance.email})"
        )
        # ------------------------

        user_instance.delete()
        messages.success(request, f'User {user_instance.username} successfully deleted.')
        return redirect('user_management')
        
    context = { 'user_to_delete': user_instance }
    return render(request, 'adminpanel/user_delete_confirm.html', context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def project_tracking(request):
    projects_list = Project.objects.all().select_related('author__user').order_by('-created_at')
    
    query = request.GET.get('q')
    if query:
        projects_list = projects_list.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(author__user__username__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter:
        projects_list = projects_list.filter(status=status_filter)

    paginator = Paginator(projects_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = { "projects": page_obj }
    return render(request, "adminpanel/project_tracking.html", context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def project_detail(request, pk):
    project_instance = get_object_or_404(Project.objects.select_related('author__user'), pk=pk)
    project_instance.badge_class = 'active' if project_instance.status == 'Active' else (
        'completed' if project_instance.status == 'Completed' else 'pending'
    )
    context = { 'project': project_instance }
    return render(request, 'adminpanel/project_detail.html', context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def project_edit(request, pk):
    project_instance = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project_instance.title}" updated successfully.')
            return redirect('project_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors.')
    else:
        form = ProjectForm(instance=project_instance)
    context = { 'form': form, 'project': project_instance }
    return render(request, 'adminpanel/project_edit.html', context)

@login_required(login_url='/accounts/login/') 
@user_passes_test(is_admin)
def admin_profile(request):
    profile_instance, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = AdminUserForm(request.POST, instance=request.user)
        profile_form = AdminProfileForm(request.POST, request.FILES, instance=profile_instance)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('admin_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = AdminUserForm(instance=request.user)
        profile_form = AdminProfileForm(instance=profile_instance)
    context = { "user": request.user, "user_form": user_form, "profile_form": profile_form }
    return render(request, "adminpanel/admin_profile.html", context)

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def export_projects_csv(request):
    """Export all projects to a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="projects_export.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['Title', 'Student', 'Email', 'Category', 'Status', 'Date Submitted', 'Views', 'Likes'])

    # Fetch data (optimized query)
    projects = Project.objects.all().select_related('author__user').order_by('-created_at')

    for project in projects:
        # Handle cases where user might not have a first/last name set
        student_name = project.author.user.get_full_name() or project.author.user.username
        
        writer.writerow([
            project.title,
            student_name,
            project.author.user.email,
            project.category,
            project.status,
            project.created_at.strftime("%Y-%m-%d %H:%M"),
            project.views,
            project.likes
        ])

    return response


@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def audit_logs(request):
    logs_list = AuditLog.objects.all().select_related('admin')
    paginator = Paginator(logs_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "adminpanel/audit_logs.html", {"logs": page_obj})

@login_required(login_url='/accounts/login/')
@user_passes_test(is_admin)
def admin_delete_project(request, pk):
    """Allow admins to permanently delete any project."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        # Log the action first
        AuditLog.objects.create(
            admin=request.user,
            action='DELETE',
            target_object=f"Project: {project.title}",
            details=f"Permanently deleted project submitted by {project.author.user.username}"
        )
        
        project_title = project.title
        project.delete()
        messages.success(request, f"Project '{project_title}' has been permanently deleted.")
        return redirect('project_tracking')
    
    context = {'project': project}
    return render(request, 'adminpanel/project_delete_confirm.html', context)