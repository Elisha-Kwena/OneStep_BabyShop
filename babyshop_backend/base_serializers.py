# In your main project directory: base_serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class BaseUserSerializer(serializers.ModelSerializer):
    """Base user serializer for all apps to use"""
    
    display_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'display_name', 'initials']
        read_only_fields = fields
    
    def get_display_name(self, obj):
        """Get user-friendly display name"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.username:
            return obj.username
        return obj.email.split('@')[0]
    
    def get_initials(self, obj):
        """Get initials for avatar display"""
        initials = ''
        if obj.first_name:
            initials += obj.first_name[0].upper()
        if obj.last_name:
            initials += obj.last_name[0].upper()
        return initials or obj.email[0].upper()