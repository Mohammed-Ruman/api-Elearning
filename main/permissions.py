from rest_framework.permissions import BasePermission

class HasCoursePermissions(BasePermission):
    def has_permission(self, request, view):
        required_permissions = ['main.add_course', 'main.view_course', 'main.change_course', 'main.delete_course']
        return all(request.user.has_perm(perm) for perm in required_permissions)

class HasCourseContentPermissions(BasePermission):
    def has_permission(self, request, view):
        required_permissions = ['main.view_course','main.view_coursecontent','main.add_subscription']
        return all(request.user.has_perm(perm) for perm in required_permissions)