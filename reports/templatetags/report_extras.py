from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Return the value from a dictionary for the given key."""
    return dictionary.get(key, 0)
