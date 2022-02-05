from django.http import JsonResponse, HttpResponse


def not_authenticated_check(func):
    def wrapper(*args, **kwargs):
        user = args[0].user
        if not user.is_authenticated:
            return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

        return_value = func(*args, **kwargs)
        return return_value

    return wrapper

