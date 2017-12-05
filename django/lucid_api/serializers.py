from rest_framework import serializers
from .models import ProjectType, Project, ServiceConnection

class ServiceConnectionSerializer(serializers.ModelSerializer):
    ''' used to create the many to one relation on projects'''
    class Meta:
        model = ServiceConnection
        fields = (
            'service_name', 
            'connection_name',
            'identifier')


class ProjectSerializer(serializers.ModelSerializer):
    
    type_code = serializers.PrimaryKeyRelatedField(
        many=False,
        read_only=False,
        queryset=ProjectType.objects.all()
    )
    services = ServiceConnectionSerializer(
        many=True,
        read_only=False
    )

    class Meta:
        model = Project
        fields = (
            "type_code",
            "title",
            "services"
        )
    
    def create(self, validated_data):
        services_data = validated_data.pop('services')
        project = Project.objects.create(**validated_data)
        for service_data in services_data:
            ServiceConnection.objects.create(project=project, **service_data)
        return project