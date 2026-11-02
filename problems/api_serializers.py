from django.db import transaction
from rest_framework import serializers

from .models import Problem, Tag


class ProblemCreateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50, allow_blank=True),
        required=False,
        allow_empty=True,
        max_length=5,
    )

    class Meta:
        model = Problem
        fields = ('id', 'title', 'description', 'difficulty', 'tags', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')

    def validate_tags(self, values):
        # Match the website form: normalize tags and ignore blank entries.
        return list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))

    @transaction.atomic
    def create(self, validated_data):
        tag_names = validated_data.pop('tags', [])
        problem = Problem.objects.create(user=self.context['request'].user, **validated_data)
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            problem.tags.add(tag)
        return problem
