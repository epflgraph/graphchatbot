Searches the course material for MICRO-452: Basics of Mobile Robotics at EPFL.

- If `case_study_number` is provided, returns all material from that case study along with relevant lecture slides matching the keywords.
- If `case_study_number` is not provided, returns only the case study questions (used to list all available case studies). In this case `keywords` are ignored. Whatever this call returns IS the complete list: the database only contains questions for one or two lectures. Do not request other lectures to enumerate more.

Use `case_study_number` once the student has chosen a specific case study to discuss.
Omit it to retrieve all available case study questions.
