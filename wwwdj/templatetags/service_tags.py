from django import template

register = template.Library()


@register.simple_tag
def is_project_invoiced(project, session):
    return project.invoices.filter(session=session).exists()
