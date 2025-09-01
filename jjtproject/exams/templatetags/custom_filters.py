# exams/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name="has_group")
def has_group(user, group_name):
    try:
        return user.groups.filter(name=group_name).exists()
    except Exception:
        return False



@register.filter
def safe_fullname(obj):
    """Return full name from auth.User or ExamineeAccount safely."""
    if not obj:
        return ""
    if hasattr(obj, "get_full_name"):
        name = obj.get_full_name()
        if name:
            return name
    # common custom fields
    for attr in ("full_name", "fullname", "name"):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if val:
                return val
    first = getattr(obj, "first_name", "") or getattr(obj, "firstname", "")
    last = getattr(obj, "last_name", "") or getattr(obj, "lastname", "")
    if first or last:
        return f"{first} {last}".strip()
    return getattr(obj, "username", "") or getattr(obj, "email", "")


def exam_name(obj):
    """Return a readable exam title from various possible field names."""
    if not obj:
        return "-"
    for attr in ("name", "title", "exam_title", "label", "code"):
        val = getattr(obj, attr, None)
        if val:
            return val
    return str(obj)

