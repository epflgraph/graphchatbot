You can still answer through {% for name in tool_names %}`{{ name }}`{% if not loop.last %} or {% endif %}{% endfor %}, whose output is shown to the user as your reply.
