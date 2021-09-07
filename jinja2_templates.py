import jinja2

jinja2_datasets_template_str = """
    [
        {% for cfg in datasets %}
            {
                data: [ {{ datasets[cfg]["data"] }} ],
                label: "{{ cfg }}" ,
                borderColor: "{{ datasets[cfg]["color"] }}",
                fill: false
            },
        {% endfor %}
    ] """

jinja2_datasets_template: jinja2.Template = \
    jinja2.Template(jinja2_datasets_template_str,
                    trim_blocks=True, lstrip_blocks=True)


def gen_datasets_def(datasets):
    return jinja2_datasets_template.render(datasets=datasets)
