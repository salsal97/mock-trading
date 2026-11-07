from rest_framework.response import Response
from rest_framework import status


def create_error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    data = {'error': message}
    if errors:
        data['errors'] = errors
    return Response(data, status=status_code)


def create_success_response(message, data=None, status_code=status.HTTP_200_OK):
    return Response({'message': message, **(data or {})}, status=status_code)
