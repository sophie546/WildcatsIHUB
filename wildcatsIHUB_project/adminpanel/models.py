from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]
    
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_object = models.CharField(max_length=200)  # E.g., "Project: AI Chatbot"
    details = models.TextField(blank=True, null=True) # E.g., "Reason for rejection..."
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin} {self.action} - {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

