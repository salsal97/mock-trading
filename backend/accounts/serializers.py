from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'username': {'error_messages': {'required': 'Username is required.'}},
            'email': {'error_messages': {'invalid': 'Please enter a valid email address.'}},
        }

    def validate_username(self, value):
        """Validate username uniqueness"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        """Validate email uniqueness if provided"""
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        """Create user with proper error handling"""
        try:
            # Remove password2 from validated_data as it's not needed for user creation
            validated_data.pop('password2', None)
            
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email', ''),
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', '')
            )
            user.set_password(validated_data['password'])
            user.save()
            return user
        except IntegrityError as e:
            # Handle database-level unique constraint violations
            if 'username' in str(e).lower():
                raise serializers.ValidationError({"username": "A user with this username already exists."})
            elif 'email' in str(e).lower():
                raise serializers.ValidationError({"email": "A user with this email already exists."})
            else:
                raise serializers.ValidationError({"non_field_errors": "A user with this information already exists."})

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, error_messages={'required': 'Username is required.'})
    password = serializers.CharField(required=True, write_only=True, error_messages={'required': 'Password is required.'}) 