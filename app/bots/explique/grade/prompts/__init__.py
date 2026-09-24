# The topic menu, in escalation order: a student who keeps not picking one must not
# see the same block forever.
MENU_TEMPLATES = ("menu-standard.md", "menu-retry.md", "menu-firm.md")
# The numbered topic list every menu includes.
TOPIC_LIST_TEMPLATE = "topic-list.md"
# Stands in for the menu when no quiz in the course carries a topic tag.
MENU_UNAVAILABLE_TEMPLATE = "menu-unavailable.md"
# Asks for the explanation, on the turn a topic is locked.
INVITE_TEMPLATE = "invite.md"
# The same invitation, warning that this course has no enrolment to record against.
INVITE_UNRECORDED_TEMPLATE = "invite-unrecorded.md"
# Points a turn that is not about the locked topic back at it.
REDIRECT_TEMPLATE = "redirect.md"
# Answers a turn that tries to jailbreak the bot instead of explaining.
JAILBREAK_TEMPLATE = "jailbreak.md"
# Stands in for an attached file's text in the student's turn, which is never read.
ATTACHMENT_DROPPED_TEMPLATE = "attachment-dropped.md"
# Status lines shown above the reply while it is on its way: at the material fetch,
# at the enrolment check, at the transcription of a photo, at the planning of the next move,
# and at the recap, after the closing message.
STATUS_FETCHING_TEMPLATE = "status-fetching.md"
STATUS_ENROLMENT_TEMPLATE = "status-enrolment.md"
STATUS_TRANSCRIBING_TEMPLATE = "status-transcribing.md"
STATUS_PLANNING_TEMPLATE = "status-planning.md"
STATUS_FINISHING_TEMPLATE = "status-finishing.md"
# Closes the exercise: carries the closing marker, and hands over the practice quiz the coverage opened.
FINISH_TEMPLATE = "finish.md"
# Ends the finish, after the recap: where to go for another topic.
FINISH_NEW_CHAT_TEMPLATE = "finish-new-chat.md"
# Told between tries, while recording the coverage in Moodle is retried.
FINISH_RETRY_TEMPLATE = "finish-retry.md"
# Answers a turn that arrives after the exercise already closed.
FINISH_CLOSED_TEMPLATE = "finish-closed.md"
# The sentence `finish.md` carries, and the only trace a finished exercise leaves.
FINISH_MARKER_TEMPLATE = "finish-marker.md"
