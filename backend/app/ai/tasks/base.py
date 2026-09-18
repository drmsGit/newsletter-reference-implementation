"""What an AI task declares about itself — ADR-140 §4's split, made readable.

A task module is the **dev-owned scaffold**: it says what the task reads, what
shape it returns, and what it costs at worst. The prompt is *not* part of that
— it is manager-owned and versioned in settings, because a developer cannot
meaningfully evaluate marketing copy. `default_prompt` here is only the text a
deployment starts from before anyone has published one.

`settings_fields` is the extension point the settings page renders. It is empty
for every task today, and it exists so that the first task needing an extra
knob declares it here rather than pushing markup back into the template — the
same shape a module manifest uses for its `variables`, which is the idiom this
codebase already follows for decision strategies, email modules, channels and
renderers.
"""

from dataclasses import dataclass, field


@dataclass
class TaskSetting:
    """One extra manager-editable setting beyond the prompt."""
    name: str
    label: str
    help_text: str = ""
    default: str = ""


@dataclass
class TaskMeta:
    #: Stable identifier. It keys the published prompt and every AIRun row, so
    #: it is permanent — renaming it orphans a prompt's version history.
    key: str
    #: What a manager sees as the card heading.
    label: str
    #: One line under the heading, in the manager's terms rather than the
    #: developer's.
    description: str
    #: The text a deployment starts from before anyone publishes.
    default_prompt: str
    #: The worst-case output size, which is what lets the spend cap be a
    #: pre-call gate rather than a mid-run kill (ADR-144 §5).
    max_output_tokens: int
    settings_fields: list[TaskSetting] = field(default_factory=list)
