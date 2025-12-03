from django.db import models
from accounts.models import UserProfile  # Import from accounts app
from django.contrib.auth.models import User # Needed for the approved_by field
from django.utils import timezone

# --- NEW: Dynamic Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
# -----------------------------------

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # We keep this as CharField so it can store "Other" or custom text if needed
    category = models.CharField(max_length=100, blank=True, null=True)
    
    github_url = models.URLField(blank=True, null=True)
    live_demo = models.URLField(blank=True, null=True)
    video_demo = models.URLField(blank=True, null=True)
    tech_used = models.CharField(max_length=200, blank=True, null=True)
    screenshot = models.ImageField(upload_to="project_screenshots/", blank=True, null=True)
    
    # Relationship (The student who submitted it)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True) 
    
    # Admin Audit Trail
    approved_at = models.DateTimeField(null=True, blank=True) 
    # Tracks WHO approved/rejected the project
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_projects")

    # Stats
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)

    # Status
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Approved', 'Approved'), 
        ('Rejected', 'Rejected'), 
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending') 
    
    class Meta:
        ordering = ['-created_at']  
    
    def __str__(self):
        return self.title