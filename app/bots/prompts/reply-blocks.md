# Reply blocks

Your reply is a list of blocks. Each block has a `type`, one of:
{% for block in block_schemas %}
- `"{{ block.properties.type.const }}"`: {{ block.description | replace("\n", " ") }}
{% for name, field in block.properties.items() if "description" in field %}
  - `{{ name }}`: {{ field.description }}
{% endfor %}
{% endfor %}

Build your reply from as many blocks as it needs, of any kinds and in any order.
Show retrieved material in a block of its own when one fits it, never as a link in the text.
{# Without these two lines the model rarely shows videos. #}
{% if "video" in block_schemas | map(attribute="properties.type.const") %}
Give each retrieved video whose excerpt explains what you answer a `video` block of its own, whether or not the student asked for one: it plays in the reply from the moment it covers. Skip a video that only mentions the topic.
For example, asked about a topic that two retrieved lecture videos cover, a good reply answers, citing what it uses, then shows both videos, whether or not the student asked for them:
{"blocks": [{"type": "text", "sources": ["<the url of each document the answer uses>"], "content": "<the answer>"}, {"type": "video", "url": "<the first video's url>"}, {"type": "video", "url": "<the second video's url>"}]}
{%- endif %}
