from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(name='localtime')
@stringfilter
def format_datetime(value, eid=None):
    import random
    import string

    if eid is None:
        eid = ''.join([random.choice(string.ascii_letters) for i in range(0, 15)])
    eid = str(eid)
    return """
<time id="{id}"></time>
<script>
    updateTimeValue("#{id}","{dt}.000Z");
</script>
    """.format(id=eid, dt=value)
